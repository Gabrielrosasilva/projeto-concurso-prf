"""O exame de aptidao fisica (TAF) da PRF: os pontos de cada teste. Puro.

Os indices moram no `taf.yml` da pasta de config (na PRF, `PRF/config/taf.yml`),
copiados do Anexo III do edital de 2021. Este arquivo so le e faz a conta:

  * cada teste vira pontos pela tabela do edital (0,00 = reprovado);
  * aprovado = no minimo 2,00 em CADA teste E media 3,00 nos cinco (item 2.3).
    Por isso o minimo em tudo (media 2) reprova - a tela precisa deixar isso
    claro, e a conta mora aqui para nenhuma tela refazer;
  * quanto falta para o proximo degrau (meio ponto) de cada teste;
  * o ritmo de corrida que da uma distancia em 12 minutos.

Nao fala com banco nem com rede.
"""
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from radar import config

#: Duracao do teste de corrida, em minutos (Anexo III, 3.5).
MINUTOS_DA_CORRIDA = 12


def caminho() -> Path:
    return config.diretorio_config() / "taf.yml"


def carregar() -> dict:
    """O taf.yml, ou {} quando nao ha. A tela diz o que falta."""
    arquivo = caminho()
    if not arquivo.exists():
        return {}
    return yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}


def pontos_em_texto(valor: float) -> str:
    """3.5 -> '3,5'; 3.0 -> '3'."""
    texto = f"{valor:.1f}".replace(".", ",")
    return texto[:-2] if texto.endswith(",0") else texto


@dataclass
class Teste:
    """Um teste do edital, ja com a tabela do sexo escolhido."""
    chave: str
    nome: str
    item: str
    tentativas: int
    unidade: str
    sentido: str            # "maior" (mais e melhor) ou "menor" (o tempo)
    faixas: list[tuple[float, float]]
    como_fazer: list[str] = field(default_factory=list)

    def pontos(self, resultado: float) -> float:
        """Os pontos do edital para um resultado. 0,0 e reprovado.

        No "maior", vale a faixa mais alta que o resultado alcancou (>=).
        No "menor" (o shuttle), a mais alta cujo limite ficou ACIMA do tempo:
        o edital diz "de 13,50 a 13,99 = 2" e "inferior a 11 = 5", entao o
        limite de cada faixa e exclusivo.
        """
        ganhou = 0.0
        for limite, pontos in self.faixas:
            if self.sentido == "menor":
                alcancou = resultado < limite
            else:
                alcancou = resultado >= limite
            if alcancou:
                ganhou = pontos
        return ganhou

    def formatar(self, valor: float | None) -> str:
        """O resultado como se le: '2,15 m', '12,49 s', '2.600 m', '7'."""
        if valor is None:
            return "—"
        if self.chave == "corrida":
            return f"{int(valor):,} m".replace(",", ".")
        if self.unidade == "metros":
            return f"{valor:.2f} m".replace(".", ",")
        if self.unidade == "segundos":
            return f"{valor:.2f} s".replace(".", ",")
        if self.unidade.startswith("segundos"):
            return f"{int(valor)} s"
        return str(int(valor))

    def texto_do_degrau(self, resultado: float) -> str:
        """'mais 2 → 3,5', 'baixar 0,11 s → 3,5' ou 'nota máxima'."""
        degrau = self.proximo_degrau(resultado)
        if degrau is None:
            return "nota máxima"
        falta, pontos = degrau
        verbo = "baixar" if self.sentido == "menor" else "mais"
        quanto = self.formatar(falta)
        return f"{verbo} {quanto} → {pontos_em_texto(pontos)}"

    def texto_da_meta(self, resultado: float, meta: float | None) -> str:
        """'faltam 3', 'baixar 0,40 s' ou 'meta batida'."""
        if meta is None:
            return ""
        if self.sentido == "menor":
            if resultado <= meta:
                return "meta batida"
            return f"baixar {self.formatar(round(resultado - meta, 2))}"
        if resultado >= meta:
            return "meta batida"
        return f"faltam {self.formatar(round(meta - resultado, 2))}"

    def minimo_para(self, pontos: float) -> float | None:
        """O resultado que da esses pontos (o limite da faixa), ou None."""
        for limite, valor in self.faixas:
            if valor >= pontos:
                return limite
        return None

    def proximo_degrau(self, resultado: float) -> tuple[float, float] | None:
        """(o que falta, os pontos que vem) para subir meio ponto; None no 5.

        No "maior" falta `limite - resultado`. No "menor" o limite e
        exclusivo: para sair de 12,60 s e ganhar 3,5 e preciso fazer MENOS que
        12,50, e a tela mostra "baixar 0,11 s" (um centesimo abaixo).
        """
        atual = self.pontos(resultado)
        for limite, pontos in self.faixas:
            if pontos > atual:
                if self.sentido == "menor":
                    return round(resultado - limite + 0.01, 2), pontos
                return round(limite - resultado, 2), pontos
        return None


def testes(regras: dict | None = None) -> list[Teste]:
    """Os cinco testes na ordem do edital, com a tabela do `sexo` do yml."""
    regras = carregar() if regras is None else regras
    edital = regras.get("edital") or {}
    sexo = edital.get("sexo", "masculino")
    lista = []
    for bruto in edital.get("testes") or []:
        tabela = bruto[sexo]
        lista.append(Teste(
            chave=bruto["chave"],
            nome=bruto["nome"],
            item=bruto.get("item", ""),
            tentativas=int(bruto.get("tentativas", 1)),
            unidade=tabela["unidade"],
            sentido=tabela.get("sentido", "maior"),
            faixas=[(float(limite), float(pontos)) for limite, pontos in tabela["faixas"]],
            como_fazer=list(bruto.get("como_fazer") or []),
        ))
    return lista


@dataclass
class Avaliacao:
    """O resultado de um TAF (simulado ou de verdade) contra o edital."""
    pontos: dict[str, float]            # chave do teste -> pontos
    faltando: list[str]                 # testes sem resultado
    reprovados: list[str]               # testes abaixo do minimo
    soma: float
    media: float | None                 # None enquanto falta teste
    aprovado: bool | None               # None enquanto falta teste
    falta_para_media: float             # pontos que faltam para a media minima


def avaliar(resultados: dict[str, float], regras: dict | None = None) -> Avaliacao:
    """Os pontos de cada teste, a soma, a media e se passa (item 2.3).

    Teste sem resultado nao vira zero: fica em `faltando`, e a media so sai
    com os cinco. Um zero inventado faria a tela dizer "reprovado" para quem
    so nao fez o teste ainda.
    """
    regras = carregar() if regras is None else regras
    edital = regras.get("edital") or {}
    minimo = float(edital.get("minimo_por_teste", 2.0))
    media_minima = float(edital.get("media_minima", 3.0))

    lista = testes(regras)
    pontos, faltando, reprovados = {}, [], []
    for teste in lista:
        if resultados.get(teste.chave) is None:
            faltando.append(teste.chave)
            continue
        pontos[teste.chave] = teste.pontos(float(resultados[teste.chave]))
        if pontos[teste.chave] < minimo:
            reprovados.append(teste.chave)

    soma = sum(pontos.values())
    completo = not faltando and bool(lista)
    media = round(soma / len(lista), 2) if completo else None
    aprovado = (not reprovados and media >= media_minima) if completo else None
    falta = max(0.0, round(media_minima * len(lista) - soma, 2))
    return Avaliacao(pontos, faltando, reprovados, soma, media, aprovado, falta)


def metas(regras: dict | None = None) -> dict[str, float]:
    """A minha meta de cada teste, em resultado (o `plano.metas` do yml).

    Teste sem meta escrita fica com o resultado que da a `meta_de_pontos`:
    a tela sempre tem uma linha de meta para desenhar.
    """
    regras = carregar() if regras is None else regras
    plano = regras.get("plano") or {}
    escritas = plano.get("metas") or {}
    pontos = float(plano.get("meta_de_pontos", 5))
    saida = {}
    for teste in testes(regras):
        if escritas.get(teste.chave) is not None:
            saida[teste.chave] = float(escritas[teste.chave])
        else:
            saida[teste.chave] = teste.minimo_para(pontos)
    return saida


def ritmo_por_km(distancia_m: float, minutos: float = MINUTOS_DA_CORRIDA) -> str:
    """O ritmo (min:seg por km) que cobre a distancia no tempo. Ex.: '4:37'."""
    segundos_por_km = minutos * 60 / (distancia_m / 1000)
    inteiros = round(segundos_por_km)
    return f"{inteiros // 60}:{inteiros % 60:02d}"


def tempo_por_volta(distancia_m: float, volta_m: float = 400,
                    minutos: float = MINUTOS_DA_CORRIDA) -> str:
    """Quanto cada volta de pista deve levar para chegar na distancia."""
    segundos = round(minutos * 60 * volta_m / distancia_m)
    return f"{segundos // 60}:{segundos % 60:02d}"

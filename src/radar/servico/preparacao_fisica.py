"""A aba Preparacao Fisica: o que eu registro e o que o radar conta disso.

Tres coisas ficam guardadas em `data/preparacao_fisica.json`:

  * a **situacao**: a data da liberacao medica (o plano so comeca nela), o que
    o medico ainda nao liberou e, quando sair o edital, a data do TAF;
  * os **testes**: cada vez que eu medir um ou mais dos cinco testes (o TAF
    simulado completo, ou so a barra num dia de costas);
  * os **treinos**: o que fiz, quantos minutos, o esforco (0 a 10) e a dor
    (0 a 10). Esforco x minutos e a "carga" da semana, que avisa quando eu
    subo rapido demais.

Por que JSON e nao o banco: e pouco dado, so meu, e o arquivo se le e se
corrige a mao. Por que fora do git: o repositorio no GitHub e publico, e
dado de saude nao vai para la (o .gitignore lista o arquivo).

Os pontos sao do `radar.taf`; aqui nao se refaz conta do edital.
"""
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from radar import config, taf

TIPOS_DE_TESTE = ("simulado", "treino")

#: A carga da semana pode subir ate isso sobre a media das anteriores antes do
#: aviso. ~30% e a regra pratica que o plano usa (cuidados do taf.yml).
SUBIDA_MAXIMA_DA_CARGA = 1.30

#: Dor a partir disso (0 a 10) acende o aviso: o "4 ou mais" do plano.
DOR_DE_AVISO = 4

#: Quantas semanas antes da atual entram na media da carga.
SEMANAS_DA_MEDIA = 4


def caminho() -> Path:
    return config.diretorio_dados() / "preparacao_fisica.json"


def ler() -> dict:
    arquivo = caminho()
    dados = {}
    if arquivo.exists():
        dados = json.loads(arquivo.read_text(encoding="utf-8")) or {}
    dados.setdefault("situacao", {})
    dados.setdefault("testes", [])
    dados.setdefault("treinos", [])
    return dados


def _gravar(dados: dict) -> None:
    arquivo = caminho()
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")


def _proximo_id(linhas: list[dict]) -> int:
    return max((linha.get("id", 0) for linha in linhas), default=0) + 1


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


# --- gravar ----------------------------------------------------------------

def definir_situacao(liberado_em: date | None, restricoes: str = "",
                     data_do_taf: date | None = None) -> None:
    dados = ler()
    dados["situacao"] = {
        "liberado_em": liberado_em.isoformat() if liberado_em else None,
        "restricoes": restricoes.strip(),
        "data_do_taf": data_do_taf.isoformat() if data_do_taf else None,
    }
    _gravar(dados)


def registrar_teste(dia: date, resultados: dict[str, float | None],
                    tipo: str = "simulado", observacao: str = "") -> dict:
    """Grava os testes medidos num dia. So os que tem valor entram."""
    if tipo not in TIPOS_DE_TESTE:
        raise ValueError(f"Tipo de teste desconhecido: {tipo}")
    chaves = {teste.chave for teste in taf.testes()}
    medidos = {}
    for chave, valor in resultados.items():
        if valor is None:
            continue
        if chave not in chaves:
            raise ValueError(f"Teste desconhecido: {chave}")
        if valor < 0:
            raise ValueError("Resultado não pode ser negativo.")
        medidos[chave] = float(valor)
    if not medidos:
        raise ValueError("Preencha pelo menos um teste.")
    dados = ler()
    linha = {"id": _proximo_id(dados["testes"]), "data": dia.isoformat(),
             "tipo": tipo, "resultados": medidos,
             "observacao": observacao.strip(), "anotado_em": _agora()}
    dados["testes"].append(linha)
    _gravar(dados)
    return linha


def registrar_treino(dia: date, o_que: str, minutos: int, esforco: int,
                     dor: int = 0, observacao: str = "") -> dict:
    if not o_que.strip():
        raise ValueError("Diga o que foi o treino.")
    if minutos <= 0:
        raise ValueError("Os minutos precisam ser maiores que zero.")
    for nome, valor in (("esforço", esforco), ("dor", dor)):
        if not 0 <= valor <= 10:
            raise ValueError(f"O {nome} vai de 0 a 10.")
    dados = ler()
    linha = {"id": _proximo_id(dados["treinos"]), "data": dia.isoformat(),
             "o_que": o_que.strip(), "minutos": int(minutos),
             "esforco": int(esforco), "dor": int(dor),
             "observacao": observacao.strip(), "anotado_em": _agora()}
    dados["treinos"].append(linha)
    _gravar(dados)
    return linha


def apagar(qual: str, ident: int) -> bool:
    """Apaga um teste ou treino lancado errado. Devolve se achou."""
    if qual not in ("testes", "treinos"):
        raise ValueError(qual)
    dados = ler()
    antes = len(dados[qual])
    dados[qual] = [linha for linha in dados[qual] if linha.get("id") != ident]
    _gravar(dados)
    return len(dados[qual]) < antes


# --- contar ----------------------------------------------------------------

@dataclass
class Medida:
    data: date
    tipo: str
    resultado: float
    pontos: float
    ident: int


def historico(regras: dict | None = None) -> dict[str, list[Medida]]:
    """Cada teste -> as medidas dele, da mais antiga para a mais nova."""
    regras = taf.carregar() if regras is None else regras
    por_chave = {teste.chave: teste for teste in taf.testes(regras)}
    saida = {chave: [] for chave in por_chave}
    for linha in sorted(ler()["testes"], key=lambda l: (l["data"], l.get("id", 0))):
        for chave, valor in linha["resultados"].items():
            if chave in por_chave:
                saida[chave].append(Medida(
                    date.fromisoformat(linha["data"]), linha.get("tipo", "simulado"),
                    valor, por_chave[chave].pontos(valor), linha.get("id", 0)))
    return saida


def ultimos_resultados(regras: dict | None = None) -> dict[str, float]:
    """A medida mais recente de cada teste: o "meu TAF hoje"."""
    return {chave: medidas[-1].resultado
            for chave, medidas in historico(regras).items() if medidas}


@dataclass
class Fase:
    indice: int             # 0 = antes da liberacao; 1 a 4 = as fases do plano
    nome: str
    semana: int | None      # a semana dentro da fase (1, 2, ...)
    detalhe: dict | None    # a fase do taf.yml


def fase_atual(dia: date, regras: dict | None = None) -> Fase:
    """Em que fase do plano estou, contando da liberacao medica.

    Sem liberacao, e a fase 0: so o que o medico mandar. Com a data do TAF
    gravada (saiu o edital), a ultima fase vale das 16 semanas antes dele em
    diante, mesmo que as outras nao tenham acabado: o prazo manda.
    """
    regras = taf.carregar() if regras is None else regras
    fases = (regras.get("plano") or {}).get("fases") or []
    situacao = ler()["situacao"]
    liberado = situacao.get("liberado_em")
    if not liberado or not fases or dia < date.fromisoformat(liberado):
        return Fase(0, "Fase 0 - Recuperação", None, None)

    data_do_taf = situacao.get("data_do_taf")
    semanas_ate_taf = int((regras.get("edital") or {}).get("semanas_do_edital_ao_taf_2021", 16))
    if data_do_taf and dia >= date.fromisoformat(data_do_taf) - timedelta(weeks=semanas_ate_taf):
        inicio_da_ultima = date.fromisoformat(data_do_taf) - timedelta(weeks=semanas_ate_taf)
        semana = (dia - max(inicio_da_ultima, date.fromisoformat(liberado))).days // 7 + 1
        return Fase(len(fases), fases[-1]["nome"], semana, fases[-1])

    # Sem data do TAF, a ultima fase (a especifica, `semanas: 0`) espera o
    # edital: as outras correm uma depois da outra, e a ultima delas continua
    # valendo ate a data do TAF ser gravada.
    semana_total = (dia - date.fromisoformat(liberado)).days // 7      # 0, 1, ...
    com_prazo = fases[:-1] or fases
    inicio = 0
    for indice, fase in enumerate(com_prazo, start=1):
        duracao = int(fase.get("semanas") or 0)
        if semana_total < inicio + duracao or indice == len(com_prazo):
            return Fase(indice, fase["nome"], semana_total - inicio + 1, fase)
        inicio += duracao
    return Fase(0, "Fase 0 - Recuperação", None, None)   # nao chega aqui


@dataclass
class SemanaDeCarga:
    segunda: date
    carga: int              # soma de esforco x minutos
    treinos: int
    dor_maxima: int


def carga_semanal(dia: date, semanas: int = 6) -> list[SemanaDeCarga]:
    """As ultimas `semanas` (a atual por ultimo), de segunda a domingo."""
    segunda_atual = dia - timedelta(days=dia.weekday())
    saida = []
    treinos = ler()["treinos"]
    for atras in range(semanas - 1, -1, -1):
        segunda = segunda_atual - timedelta(weeks=atras)
        domingo = segunda + timedelta(days=6)
        da_semana = [t for t in treinos
                     if segunda <= date.fromisoformat(t["data"]) <= domingo]
        saida.append(SemanaDeCarga(
            segunda,
            sum(t["minutos"] * t["esforco"] for t in da_semana),
            len(da_semana),
            max((t.get("dor", 0) for t in da_semana), default=0)))
    return saida


def avisos(dia: date) -> list[str]:
    """O que a tela deve gritar: carga subindo rapido, dor alta."""
    saida = []
    semanas = carga_semanal(dia, SEMANAS_DA_MEDIA + 1)
    anteriores = [s.carga for s in semanas[:-1] if s.carga > 0]
    atual = semanas[-1]
    if anteriores:
        media = sum(anteriores) / len(anteriores)
        if atual.carga > media * SUBIDA_MAXIMA_DA_CARGA:
            saida.append(
                f"A carga desta semana ({atual.carga}) já passou {round((atual.carga / media - 1) * 100)}% "
                f"da média das anteriores ({round(media)}). Segure o volume até domingo.")
    sete_dias = [t for t in ler()["treinos"]
                 if dia - timedelta(days=6) <= date.fromisoformat(t["data"]) <= dia]
    doloridos = [t for t in sete_dias if t.get("dor", 0) >= DOR_DE_AVISO]
    if doloridos:
        pior = max(doloridos, key=lambda t: t["dor"])
        saida.append(
            f"Dor {pior['dor']}/10 em \"{pior['o_que']}\" ({date.fromisoformat(pior['data']):%d/%m}). "
            "Volte um passo nesse exercício e, se continuar, fale com o médico.")
    return saida


def contagem_do_taf(dia: date, regras: dict | None = None) -> dict | None:
    """Quantos dias faltam para o TAF e a janela do atestado, se ha data."""
    regras = taf.carregar() if regras is None else regras
    data_do_taf = ler()["situacao"].get("data_do_taf")
    if not data_do_taf:
        return None
    alvo = date.fromisoformat(data_do_taf)
    dias_do_atestado = int((regras.get("edital") or {}).get("dias_do_atestado", 15))
    return {"data": alvo, "faltam": (alvo - dia).days,
            "atestado_a_partir_de": alvo - timedelta(days=dias_do_atestado)}

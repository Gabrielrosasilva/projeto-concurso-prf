"""O Certo/Errado do Cebraspe: a regra do chute, o gabarito da banca e os itens
de cada tema.

**A regra do chute (Etapa 4 da PRF, PRF-28).** No Cebraspe a certa vale +1, a
errada -1 e a em branco 0 (edital PRF 2021, item 9.12.2). Chutar um item vale
a pena, em media, so quando a chance de acertar passa de 50%: com chance p, o
chute rende p x (+1) + (1 - p) x (-1) = 2p - 1 ponto. Daqui sai a regra, com
dois numeros contados - nunca de memoria:

  * o GABARITO DA BANCA: quantos itens sao Certo e quantos Errado, nas provas
    da PRF e no acervo do Cebraspe do radar (`gabarito_do_cebraspe`), e nos
    gabaritos inteiros dos cadernos da lista (`gabaritos_inteiros`, so pelo
    terminal: le os PDFs). E ele que diz quanto vale o chute CEGO;
  * os MEUS CHUTES: das respostas marcadas "vou no chute" em item de
    Certo/Errado, quantas acertei (`meus_chutes`). E ele que diz se o chute
    com uma inclinacao (lembro em parte, descartei algo) compensa para mim.

A margem e a de 95% da proporcao (1,96 desvios): enquanto ela cobre os 50%, a
diferenca pode ser sorteio, e a tela diz isso.

**Os itens de cada tema** (`do_tema`) sao a tela "Certo ou Errado" da faixa:
o item com o gabarito escondido ate o clique, sem gravar nada. Na PMSC ela era
o unico lugar do Certo/Errado (decisao PMSC-19); na PRF o item tambem treina e
mede nas rodadas, como complementar (`complementar.cadernos_de_certo_errado`).
"""
import math
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select

from radar import amostra as regua
from radar import cache, leis
from radar import conteudos as arvore
from radar.db import criar_tabelas, sessao
from radar.models import Classificacao, QuestaoDeProva
from radar.origem import AUTOMATICO
from radar.questoes_certo_errado import ALTERNATIVAS, e_certo_errado
from radar.servico import evidencia, metricas
from radar.servico.classificacoes import PENDENTE, chave_de


@dataclass
class Item:
    """Um item de Certo/Errado, pronto para a tela."""

    id: int
    conteudo: str
    numero: int
    banca: str
    ano: int | None
    cargo: str | None
    prova_url: str
    enunciado: str
    texto_base: str | None
    #: "Certo" ou "Errado", do gabarito pos-recursos.
    gabarito: str
    mudancas: list = field(default_factory=list)
    #: O sublinhado do termo que o item cita, da transcricao (o filtro
    #: `destacado` da tela le daqui).
    destaques: list | None = None


def _dentro(conteudo: str, nos: list[str]) -> bool:
    return any(conteudo == no or conteudo.startswith(no + arvore.SEPARADOR) for no in nos)


@cache.por_requisicao
def _todos() -> list[Item]:
    """Todo item de Certo/Errado classificado e com gabarito, na ordem da
    prova. A leitura e uma por abertura de tela: a Hoje pergunta por faixa.
    A classificacao pendente fica de fora, como no treino - e o passo 2 poe ali
    o item cuja lei mudou e deixou o gabarito errado (decisao 171)."""
    criar_tabelas()
    with sessao() as s:
        principais = {c.chave: c.conteudo for c in s.scalars(
            select(Classificacao).where(Classificacao.principal.is_(True))
            .where(Classificacao.status != PENDENTE))}
        questoes = list(s.scalars(
            select(QuestaoDeProva).where(QuestaoDeProva.evidencia == evidencia.COMPLEMENTAR)
            .where(QuestaoDeProva.anulada.is_not(True))
            .order_by(QuestaoDeProva.ano, QuestaoDeProva.prova_url, QuestaoDeProva.numero)))
    saida = []
    for q in questoes:
        if not e_certo_errado(q.alternativas) or q.resposta not in ALTERNATIVAS:
            continue
        conteudo = principais.get(chave_de(q))
        if not conteudo:
            continue
        texto = f"{q.enunciado} {' '.join(ALTERNATIVAS.values())}"
        saida.append(Item(
            id=q.id, conteudo=conteudo, numero=q.numero, banca=q.banca or "sem banca",
            ano=q.ano, cargo=q.cargo, prova_url=q.prova_url, enunciado=q.enunciado,
            texto_base=q.texto_base, gabarito=ALTERNATIVAS[q.resposta],
            mudancas=leis.mudancas_da_questao(q.ano, q.materia, texto, q.prova_url),
            destaques=q.destaques))
    return saida


def do_tema(nos: list[str]) -> list[Item]:
    """Os itens classificados DENTRO dos nos. Sem no, nada."""
    nos = [n for n in nos if n]
    if not nos:
        return []
    return [i for i in _todos() if _dentro(i.conteudo, nos)]


def das_faixas(geradas_das_faixas: dict) -> dict:
    """{(bloco, indice): quantos itens} das faixas de treino do dia, pelos
    nos que a faixa ja diz (os das geradas). So a faixa com algum item entra:
    sem item, a faixa nao ganha o link."""
    saida = {}
    for chave, gf in (geradas_das_faixas or {}).items():
        if gf.sem_no or not gf.nos:
            continue
        quantos = len(do_tema([n.no for n in gf.nos]))
        if quantos:
            saida[chave] = quantos
    return saida


# --- a regra do chute (PRF-28) -------------------------------------------------

#: A pontuacao do Certo/Errado: edital PRF 2021, item 9.12.2.
PONTOS = {"certa": 1, "errada": -1, "em branco": 0}

#: Quantos desvios fazem a margem de 95% da proporcao.
DESVIOS_DE_95 = 1.96


def margem_de_95(lado: int, total: int) -> float | None:
    """A margem de 95% da porcentagem `lado/total`, em pontos: p +- 1,96 x
    raiz(p(1-p)/n). E a conta da aproximacao normal - a de livro, e boa com
    dezenas de itens. None sem item."""
    if not total:
        return None
    p = lado / total
    return 100 * DESVIOS_DE_95 * math.sqrt(p * (1 - p) / total)


@dataclass(frozen=True)
class Gabarito:
    """Quantos Certo e quantos Errado num recorte de provas do Cebraspe."""
    origem = AUTOMATICO

    nome: str
    certo: int = 0
    errado: int = 0
    #: Os anulados (o X do gabarito): nao sao Certo nem Errado.
    anulados: int = 0
    cadernos: int = 0
    #: O minimo de itens para falar de tendencia (`acervo.tendencia_de_gabarito`).
    minimo: int = 0

    @property
    def itens(self) -> int:
        return self.certo + self.errado

    @property
    def porcentagem_errado(self) -> float | None:
        return round(100 * self.errado / self.itens, 1) if self.itens else None

    @property
    def porcentagem_certo(self) -> float | None:
        return round(100 * self.certo / self.itens, 1) if self.itens else None

    @property
    def margem(self) -> float | None:
        valor = margem_de_95(self.errado, self.itens)
        return None if valor is None else round(valor, 1)

    @property
    def veredito(self) -> str:
        """"amostra_pequena", "equilibrado" (a margem cobre os 50%), "errado"
        ou "certo" (o lado que passa dos 50% alem da margem)."""
        if not self.itens or self.itens < self.minimo:
            return "amostra_pequena"
        exato = 100 * self.errado / self.itens
        if abs(exato - 50) <= margem_de_95(self.errado, self.itens):
            return "equilibrado"
        return "errado" if self.errado > self.certo else "certo"

    @property
    def chute_cego(self) -> float | None:
        """O que rende, por item, chutar SEMPRE o lado mais comum: 2p - 1, com
        p a fatia dele. 0,03 quer dizer 3 pontos a cada 100 itens chutados."""
        if not self.itens:
            return None
        return round(2 * max(self.certo, self.errado) / self.itens - 1, 3)

    @property
    def lado_mais_comum(self) -> str:
        return "Errado" if self.errado >= self.certo else "Certo"


def numero(valor: float | None, casas: int = 1, sinal: bool = False) -> str:
    """O numero com virgula, como se escreve em portugues: 51,2 e +0,024."""
    if valor is None:
        return "—"
    texto = f"{valor:+.{casas}f}" if sinal else f"{valor:.{casas}f}"
    return texto.replace(".", ",")


def _da_banca(questao) -> bool:
    return "cebraspe" in (questao.banca or "").lower()


def gabarito_do_cebraspe() -> list[Gabarito]:
    """Certo x Errado nos itens do Cebraspe que o radar tem: uma linha por
    prova da PRF, as provas da PRF juntas, o acervo complementar e tudo.

    Pelo gabarito DEFINITIVO de cada item e uma vez por item (a CHAVE: o
    mesmo item em dois cadernos conta uma vez). Lembrete honesto: o acervo
    complementar so tem os itens das materias do programa da PRF (PRF-16), e
    nao os cadernos inteiros - os inteiros estao em `gabaritos_inteiros`."""
    minimo = regua.carregar().tendencia_de_gabarito
    criar_tabelas()
    with sessao() as s:
        questoes = [q for q in s.scalars(
            select(QuestaoDeProva)
            .where(QuestaoDeProva.evidencia.in_((evidencia.ALVO, evidencia.COMPLEMENTAR)))
            .order_by(QuestaoDeProva.id))
            if e_certo_errado(q.alternativas) and _da_banca(q)]

    por_recorte: dict[str, dict] = {}
    vistas: set[tuple[str, str]] = set()

    def somar(recorte: str, q) -> None:
        chave = (recorte, chave_de(q))
        if chave in vistas:
            return
        vistas.add(chave)
        conta = por_recorte.setdefault(recorte, {"c": 0, "e": 0, "x": 0, "cadernos": set()})
        if q.anulada or q.resposta not in ALTERNATIVAS:
            conta["x"] += 1
        else:
            conta[q.resposta] += 1
        conta["cadernos"].add(q.prova_url)

    anos_do_alvo = sorted({q.ano for q in questoes if q.evidencia == evidencia.ALVO and q.ano})
    for q in questoes:
        if q.evidencia == evidencia.ALVO:
            somar(f"Prova da PRF de {q.ano}", q)
            somar("Provas da PRF juntas", q)
        else:
            somar("Acervo complementar do Cebraspe", q)
        somar("Tudo do Cebraspe no radar", q)

    ordem = ([f"Prova da PRF de {ano}" for ano in anos_do_alvo]
             + ["Provas da PRF juntas", "Acervo complementar do Cebraspe",
                "Tudo do Cebraspe no radar"])
    return [Gabarito(nome=nome, certo=por_recorte[nome]["c"], errado=por_recorte[nome]["e"],
                     anulados=por_recorte[nome]["x"],
                     cadernos=len(por_recorte[nome]["cadernos"]), minimo=minimo)
            for nome in ordem if nome in por_recorte]


def gabaritos_inteiros() -> tuple[list[Gabarito], list[str]]:
    """Certo x Errado nos gabaritos definitivos INTEIROS dos cadernos de
    Certo/Errado da lista: todo item, e nao so os do programa.

    Le os PDFs (`data/provas/`, fora do git), e por isso e so do terminal
    (`radar chute --gabaritos`). Cada arquivo de gabarito conta uma vez.
    Limite dito: cadernos do mesmo concurso (PF 2021 agente e escrivao)
    repetem a parte comum, que aqui conta em cada um. Devolve ([as provas da
    PRF, as outras, tudo], [o que nao deu para ler])."""
    from radar import provas as arquivos_de_prova
    from radar.questoes_certo_errado import _texto_do_pdfminer, ler_gabarito_do_cebraspe
    from radar.servico import provas as acervo_de_provas

    minimo = regua.carregar().tendencia_de_gabarito
    por_url = {r.get("url"): r for r in arquivos_de_prova.carregar_manifesto()}
    # [certo, errado, anulados, cadernos]
    contas = {"prf": [0, 0, 0, 0], "outras": [0, 0, 0, 0]}
    lidos: set[Path] = set()
    falhas = []
    for prova in acervo_de_provas.carregar_provas_de_outras_bancas():
        if (prova.get("formato") != "certo_errado"
                or (prova.get("banca") or "").upper() != "CEBRASPE"):
            continue
        registro = por_url.get(acervo_de_provas.url_do_gabarito(prova))
        caminho = acervo_de_provas._caminho(registro)
        if caminho is None:
            falhas.append(f"{prova['caderno']}: o gabarito não está baixado")
            continue
        if caminho in lidos:
            continue
        try:
            gabarito = ler_gabarito_do_cebraspe(_texto_do_pdfminer(caminho))
        except ValueError as erro:
            falhas.append(f"{caminho.name}: {erro}")
            continue
        lidos.add(caminho)
        do_alvo = evidencia.da_prova(prova.get("cargo"), prova.get("banca"),
                                     prova.get("uf")) == evidencia.ALVO
        conta = contas["prf" if do_alvo else "outras"]
        letras = list(gabarito.values())
        conta[0] += letras.count("C")
        conta[1] += letras.count("E")
        conta[2] += letras.count("X")
        conta[3] += 1

    def linha(nome, certo, errado, anulados, cadernos):
        return Gabarito(nome=nome, certo=certo, errado=errado, anulados=anulados,
                        cadernos=cadernos, minimo=minimo)

    prf, outras = contas["prf"], contas["outras"]
    return ([linha("Gabaritos inteiros das provas da PRF", *prf),
             linha("Gabaritos inteiros dos outros cadernos", *outras),
             linha("Gabaritos inteiros, todos", *[a + b for a, b in zip(prf, outras)])],
            falhas)


@dataclass(frozen=True)
class MeusChutes:
    """As minhas respostas no "vou no chute" em item de Certo/Errado."""
    origem = AUTOMATICO

    certos: int = 0
    errados: int = 0
    #: O minimo do `config/amostra.yml` (`desempenho.chutes`).
    minimo: int = 30

    @property
    def total(self) -> int:
        return self.certos + self.errados

    @property
    def porcentagem(self) -> int | None:
        return round(100 * self.certos / self.total) if self.total else None

    @property
    def margem(self) -> int | None:
        valor = margem_de_95(self.certos, self.total)
        return None if valor is None else round(valor)

    @property
    def saldo(self) -> int:
        """O que os chutes somaram na nota; em branco teriam somado 0."""
        return self.certos - self.errados

    @property
    def veredito(self) -> str:
        """"poucos" (abaixo do minimo), "compensa" (acima dos 50% alem da
        margem), "nao_compensa" (abaixo) ou "empate" (a margem cobre os 50%)."""
        if self.total < self.minimo or not self.total:
            return "poucos"
        exato = 100 * self.certos / self.total
        margem = margem_de_95(self.certos, self.total)
        if exato - margem > 50:
            return "compensa"
        if exato + margem < 50:
            return "nao_compensa"
        return "empate"


def meus_chutes() -> MeusChutes:
    """Os meus chutes em Certo/Errado no radar: cada resposta conta (o
    historico), como a nota liquida acumulada de onde vem."""
    nota = metricas.nota_liquida_acumulada()
    return MeusChutes(certos=nota.chutes_certos, errados=nota.chutes_errados,
                      minimo=regua.carregar().chutes)


def regra_do_chute(gabarito: Gabarito | None, chutes: MeusChutes) -> list[str]:
    """A regra, em tres passos, com os numeros contados. Uma lista so para a
    tela e o terminal escreverem a mesma coisa."""
    passos = ["Sabe a resposta: marque. Cada certa vale +1 e cada errada -1."]
    if chutes.veredito == "compensa":
        passos.append(
            f"Tem uma inclinação (lembra em parte, descartou algo): chute. Seus chutes "
            f"acertam {chutes.porcentagem}% (±{chutes.margem}) em {chutes.total}, acima "
            f"de 50%: saldo {chutes.saldo:+d} na nota.")
    elif chutes.veredito == "nao_compensa":
        passos.append(
            f"Tem uma inclinação: deixe em branco. Seus chutes acertam "
            f"{chutes.porcentagem}% (±{chutes.margem}) em {chutes.total}, abaixo de 50%: "
            f"chutando, você perdeu {-chutes.saldo} pontos.")
    elif chutes.veredito == "empate":
        passos.append(
            f"Tem uma inclinação: tanto faz, em média. Seus chutes acertam "
            f"{chutes.porcentagem}% (±{chutes.margem}) em {chutes.total}: a margem cobre "
            f"os 50%, e chutar rende perto de zero. Na dúvida, em branco.")
    else:
        passos.append(
            f"Tem uma inclinação: nos treinos, marque \"vou no chute\" e responda. Com "
            f"{chutes.minimo} chutes o radar diz se eles acertam mais de 50% (você tem "
            f"{chutes.total}); até lá, na prova, na dúvida, em branco.")
    if gabarito is None or gabarito.veredito == "amostra_pequena":
        passos.append("Não faz ideia: em branco. Não há itens suficientes no acervo para "
                      "dizer se a banca dá mais Certo ou mais Errado.")
    elif gabarito.veredito == "equilibrado":
        passos.append(
            f"Não faz ideia: em branco. No Cebraspe, {numero(gabarito.porcentagem_errado)}% "
            f"dos {gabarito.itens} itens são Errado (±{numero(gabarito.margem)}): a margem "
            f"cobre os 50%, e chutar sempre {gabarito.lado_mais_comum} renderia "
            f"{numero(gabarito.chute_cego, 3, sinal=True)} ponto por item - zero, na prática.")
    else:
        passos.append(
            f"Não faz ideia: chutar sempre {gabarito.lado_mais_comum} rende "
            f"{numero(gabarito.chute_cego, 3, sinal=True)} ponto por item "
            f"({numero(gabarito.porcentagem_errado)}% Errado em {gabarito.itens} itens, "
            f"±{numero(gabarito.margem)}): uns "
            f"{round(100 * gabarito.chute_cego)} pontos a cada 100 itens chutados. É "
            f"pouco, e cada chute errado ainda pode custar o mínimo do bloco.")
    return passos

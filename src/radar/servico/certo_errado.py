"""Os itens de Certo/Errado de cada tema, so para conferir o assunto (decisao PMSC-19).

A prova de Certo/Errado (a Policia Penal DF 2022 da AOCP) esta no banco e
classificada, mas recusada no acervo complementar: nao entra em conta, treino,
rodada nem padrao. Esta e a unica tela que a mostra - cada item com o
gabarito escondido ate o clique, e nada gravado: nenhuma resposta, nenhum
acerto, nenhum erro no caderno (decisao 166, "Certo/Errado so treina").
"""
from dataclasses import dataclass, field

from sqlalchemy import select

from radar import cache, leis
from radar import conteudos as arvore
from radar.db import criar_tabelas, sessao
from radar.models import Classificacao, QuestaoDeProva
from radar.questoes_certo_errado import ALTERNATIVAS, e_certo_errado
from radar.servico import evidencia
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

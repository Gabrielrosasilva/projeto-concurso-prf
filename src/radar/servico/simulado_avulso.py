"""O Simulado da tela Simulado (PRF-53): 60 questoes, como uma prova.

Pedido do Gabriel em 27/11/2026: o simulado comeca com 60 questoes, pega as
questoes reais dando prioridade as que eu errei e, quando as reais acabarem,
entram as geradas pela IA - repetir a real que eu ja acertei mede memoria, e
nao o assunto.

A regra, em ordem, em cada materia:

  1. as reais que eu errei ou chutei da ultima vez (`simulado_da_semana.
     a_rever`): a do Cebraspe antes da de outra banca;
  2. as reais que eu nunca fiz: o Cebraspe (alvo e complementar aceito, fora
     o que a rodada que mede ainda vai usar) antes das outras bancas;
  3. o Certo/Errado da IA que eu nunca fiz;
  4. o Certo/Errado da IA que eu errei ou chutei.

O SIMULADO REAL (PRF-55) e o outro botao da tela: so questao real. Ele
segue os passos 1 e 2 e, quando as reais acabam, em vez da IA repete as que
eu acertei, as de mais tempo primeiro - e o relatorio diz quantas eram
repetidas, porque acertar uma repetida mede em parte a memoria.

No de treino, a real que eu acertei nao volta, nem a gerada que eu acertei. Sem materia
escolhida, as questoes se dividem pelas materias do edital da PRF, na
proporcao dos itens da prova (o bloco `materias` do plano); o que uma materia
nao tiver passa para as outras. As reais e as geradas nunca se somam: o
relatorio mostra os numeros lado a lado (regra 1 do CLAUDE.md), e a correcao
e no fim, como na prova.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select

from radar import conteudos as arvore
from radar.db import criar_tabelas, sessao
from radar.models import QuestaoGerada, RespostaDeSimulado, Simulado
from radar.questoes_certo_errado import e_certo_errado
from radar.servico import (compilado, composicao, cronograma, fepese_no_radar, metricas,
                           outras_bancas, simulado_da_semana)

#: O nome da rodada em `Simulado.filtros`: o de treino (com a IA) e o real.
RODADA = "simulado_avulso"
RODADA_REAL = "simulado_real"

#: Os dois modos da tela (PRF-55).
TREINO, REAL = "treino", "real"

#: Quantas questoes o simulado traz se eu nao mudar (pedido de 27/11/2026).
QUANTIDADE_PADRAO = 60
#: O teto: a prova da PRF tem 120 itens.
QUANTIDADE_MAXIMA = 120

#: De onde veio cada questao escolhida.
CEBRASPE, OUTRA_BANCA, GERADA = "cebraspe", "outra_banca", "gerada"


@dataclass(frozen=True)
class Escolhida:
    questao_id: int
    origem: str              # CEBRASPE, OUTRA_BANCA ou GERADA
    materia: str
    a_rever: bool            # errei ou chutei da ultima vez
    repetida: bool = False   # eu ja tinha acertado (so no Simulado real)


def pesos_do_edital() -> dict[str, int]:
    """{materia: itens na prova}, do bloco `materias` do plano da PRF."""
    from radar import cronograma as plano_de_estudo

    try:
        plano = plano_de_estudo.carregar()
    except (plano_de_estudo.ErroNoCronograma, OSError):
        return {}
    return {m.nome: m.questoes for m in getattr(plano, "materias", None) or [] if m.questoes}


def _da_materia(conteudo: str | None, materia: str) -> bool:
    partes = arvore.partes(conteudo or "")
    return bool(partes) and compilado.mesma_materia(materia, partes[0])


def _geradas_de_certo_errado() -> list[tuple[int, str]]:
    """[(id, no)] das geradas de Certo/Errado valendo."""
    criar_tabelas()
    with sessao() as s:
        linhas = s.execute(select(QuestaoGerada.id, QuestaoGerada.conteudo,
                                  QuestaoGerada.materia, QuestaoGerada.alternativas)
                           .where(QuestaoGerada.rejeitada.is_(False))
                           .where(QuestaoGerada.resposta.is_not(None))).all()
    return [(i, c or m or "") for i, c, m, alternativas in linhas if e_certo_errado(alternativas)]


def fila_da_materia(materia: str, *, estoque: dict, reserva, outras: list, geradas: list,
                    feitas_reais: set[str], feitas_outras: set[str], feitas_geradas: set[int],
                    rever, sorteio: random.Random) -> list[Escolhida]:
    """Todas as candidatas da materia, na ordem da regra (o docstring do
    modulo); cada grupo embaralhado. A que eu acertei fica de fora."""
    cebraspe = [c for c in fepese_no_radar.do_tema([materia], estoque)
                if c.chave not in reserva.chaves]
    if not cebraspe:
        # O no da arvore pode ter outro nome que a materia do plano.
        cebraspe = [c for lista in estoque.values() for c in lista
                    if _da_materia(c.conteudo, materia) and c.chave not in reserva.chaves]
    de_outras = [c for c in outras if _da_materia(c.conteudo, materia)]
    da_ia = [i for i, no in geradas if _da_materia(no, materia)]

    grupos = [
        [Escolhida(c.id, CEBRASPE, materia, True) for c in cebraspe
         if c.impressao in rever.impressoes],
        [Escolhida(c.id, OUTRA_BANCA, materia, True) for c in de_outras
         if c.mesma in rever.mesmas],
        [Escolhida(c.id, CEBRASPE, materia, False) for c in cebraspe
         if c.impressao not in feitas_reais and c.impressao not in rever.impressoes],
        [Escolhida(c.id, OUTRA_BANCA, materia, False) for c in de_outras
         if c.mesma not in feitas_outras and c.mesma not in rever.mesmas],
        [Escolhida(i, GERADA, materia, False) for i in da_ia
         if i not in feitas_geradas and i not in rever.geradas],
        [Escolhida(i, GERADA, materia, True) for i in da_ia if i in rever.geradas],
    ]
    for grupo in grupos:
        sorteio.shuffle(grupo)
    return [e for grupo in grupos for e in grupo]


def fila_da_materia_real(materia: str, *, estoque: dict, reserva, outras: list,
                         feitas_reais: set[str], feitas_outras: set[str], rever,
                         quando: dict[str, object], sorteio: random.Random,
                         **_resto) -> list[Escolhida]:
    """A fila do Simulado real (PRF-55): os erros, as reais novas (Cebraspe
    antes das outras bancas) e, acabando elas, as que eu acertei, a de mais
    tempo primeiro (`quando`: impressao ou `mesma` -> a ultima resposta)."""
    cebraspe = [c for c in fepese_no_radar.do_tema([materia], estoque)
                if c.chave not in reserva.chaves]
    if not cebraspe:
        cebraspe = [c for lista in estoque.values() for c in lista
                    if _da_materia(c.conteudo, materia) and c.chave not in reserva.chaves]
    de_outras = [c for c in outras if _da_materia(c.conteudo, materia)]
    grupos = [
        [Escolhida(c.id, CEBRASPE, materia, True) for c in cebraspe
         if c.impressao in rever.impressoes],
        [Escolhida(c.id, OUTRA_BANCA, materia, True) for c in de_outras
         if c.mesma in rever.mesmas],
        [Escolhida(c.id, CEBRASPE, materia, False) for c in cebraspe
         if c.impressao not in feitas_reais and c.impressao not in rever.impressoes],
        [Escolhida(c.id, OUTRA_BANCA, materia, False) for c in de_outras
         if c.mesma not in feitas_outras and c.mesma not in rever.mesmas],
    ]
    for grupo in grupos:
        sorteio.shuffle(grupo)
    # As que eu acertei: a de mais tempo primeiro (a Cebraspe e as outras
    # juntas, pela data da ultima resposta).
    acertadas = ([(quando.get(c.impressao), Escolhida(c.id, CEBRASPE, materia, False, True))
                  for c in cebraspe
                  if c.impressao in feitas_reais and c.impressao not in rever.impressoes]
                 + [(quando.get(c.mesma), Escolhida(c.id, OUTRA_BANCA, materia, False, True))
                    for c in de_outras
                    if c.mesma in feitas_outras and c.mesma not in rever.mesmas])
    sorteio.shuffle(acertadas)
    acertadas.sort(key=lambda par: (par[0] is None, par[0] or 0))
    return [e for grupo in grupos for e in grupo] + [e for _q, e in acertadas]


def _quando_respondi() -> dict[str, object]:
    """{impressao ou `mesma`: quando dei a ultima resposta a ela} - a chave
    que cada fila usa para dizer "ja fiz"."""
    from radar.models import QuestaoDeProva

    criar_tabelas()
    with sessao() as s:
        ultimas = metricas.ultimas_respostas_reais(s)
        if not ultimas:
            return {}
        quando: dict[str, object] = {}
        for q in s.scalars(select(QuestaoDeProva).where(QuestaoDeProva.id.in_(list(ultimas)))):
            momento = ultimas[q.id].respondida_em
            for chave in (q.impressao, outras_bancas.mesma_questao(q)):
                if chave and (chave not in quando or momento > quando[chave]):
                    quando[chave] = momento
    return quando


def escolher(quantidade: int, filas: dict[str, list[Escolhida]],
             pesos: dict[str, int]) -> tuple[list[Escolhida], dict[str, int]]:
    """As questoes da rodada e quantas cada materia deu. Primeiro a cota de
    cada materia pelo peso; o que faltou numa passa para as outras, na ordem
    do peso. Uma questao uma vez so."""
    cotas = compilado.distribuir(pesos, quantidade) if len(filas) > 1 else {
        m: quantidade for m in filas}
    # O id, e nao o par (origem, id): a rodada guarda a resposta por
    # (simulado, questao_id), e uma real e uma gerada de mesmo id nao cabem
    # juntas - a segunda fica para outra rodada.
    vistas: set[int] = set()
    por_materia: dict[str, list[Escolhida]] = {m: [] for m in filas}

    def tirar(materia: str, quantas: int) -> None:
        fila = filas[materia]
        while fila and quantas > 0:
            e = fila.pop(0)
            if e.questao_id in vistas:
                continue
            vistas.add(e.questao_id)
            por_materia[materia].append(e)
            quantas -= 1

    for materia in filas:
        tirar(materia, cotas.get(materia, 0))
    falta = quantidade - sum(len(v) for v in por_materia.values())
    for materia in sorted(filas, key=lambda m: -pesos.get(m, 0)):
        if falta <= 0:
            break
        antes = len(por_materia[materia])
        tirar(materia, falta)
        falta -= len(por_materia[materia]) - antes
    escolhidas = [e for m in filas for e in por_materia[m]]
    return escolhidas, {m: len(v) for m, v in por_materia.items() if v}


def criar(quantidade: int = QUANTIDADE_PADRAO, materia: str | None = None,
          data: date | None = None, sorteio: random.Random | None = None,
          modo: str = TREINO) -> Simulado | None:
    """A rodada do Simulado. None quando nao ha questao nenhuma que sirva.
    `modo` REAL e o Simulado real (PRF-55): sem a IA, repetindo as reais."""
    real = modo == REAL
    quantidade = max(1, min(quantidade, QUANTIDADE_MAXIMA))
    pesos = pesos_do_edital()
    if materia:
        pesos = {materia: pesos.get(materia, 1)}
    if not pesos:
        return None
    sorteio = sorteio or random.Random()
    data = data or cronograma.hoje_local()
    rever = simulado_da_semana.a_rever()
    contexto = dict(
        estoque=composicao.estoque_real(), reserva=composicao.reserva_das_que_medem(data),
        outras=outras_bancas.estoque([m for m in pesos]),
        feitas_reais=composicao.ja_respondidas(), feitas_outras=outras_bancas.respondidas(),
        rever=rever, sorteio=sorteio)
    if real:
        quando = _quando_respondi()
        filas = {m: fila_da_materia_real(m, quando=quando, **contexto) for m in pesos}
    else:
        contexto.update(geradas=_geradas_de_certo_errado(),
                        feitas_geradas=set(metricas.ultimas_das_geradas()))
        filas = {m: fila_da_materia(m, **contexto) for m in pesos}
    escolhidas, por_materia = escolher(quantidade, filas, pesos)
    if not escolhidas:
        return None

    contar = lambda origem: sum(1 for e in escolhidas if e.origem == origem)  # noqa: E731
    filtros = {
        "rodada": RODADA_REAL if real else RODADA,
        # As que eu ja tinha acertado (so no real): o acerto nelas mede em
        # parte a memoria, e o relatorio diz isso.
        **({"repetidas": sum(1 for e in escolhidas if e.repetida)} if real else {}),
        "quantidade": len(escolhidas),
        "pedidas": quantidade,
        "materia": materia,
        "por_materia": por_materia,
        "cebraspe": contar(CEBRASPE),
        "outras": contar(OUTRA_BANCA),
        # A mesma chave do Simulado da semana: e ela que faz o relatorio
        # mostrar as reais e as geradas lado a lado, nunca somadas.
        "geradas_na_rodada": contar(GERADA),
        "a_rever": sum(1 for e in escolhidas if e.a_rever),
        **({"faltaram": quantidade - len(escolhidas)} if len(escolhidas) < quantidade else {}),
    }
    criar_tabelas()
    with sessao() as s:
        simulado = Simulado(filtros=filtros)
        s.add(simulado)
        s.flush()
        for ordem, e in enumerate(escolhidas, start=1):
            s.add(RespostaDeSimulado(simulado_id=simulado.id, questao_id=e.questao_id,
                                     ordem=ordem, gerada=e.origem == GERADA))
    return simulado

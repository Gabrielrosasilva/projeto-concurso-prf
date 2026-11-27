"""O treino com questoes reais da FEPESE do tema, em toda materia (decisao 167).

A faixa de Portugues ja comecava pelas questoes da FEPESE que o radar tem do
tema (decisao 107). As outras materias nao tinham isso: o "Gerar questao real"
da faixa leva as questoes reais da FEPESE classificadas nos nos do tema - do
alvo e do complementar aceito, uma por chave, sem anulada, com gabarito - para
eu responder aqui dentro, e o acerto mede, como qualquer questao real.

Duas regras:

- **o fechamento de 07/11 vem primeiro.** O estoque e o mesmo das rodadas que
  medem, e a composicao nao repete questao. O treino nunca usa o que uma rodada
  que mede ainda vai usar (`composicao.reserva_das_que_medem`): a tela diz
  quantas ficaram guardadas, e para quando;
- **as nunca feitas primeiro, e depois as ja feitas** (PRF-66, pedido do
  Gabriel em 27/11; antes, na PRF-48, so as nunca feitas): feitas todas, o
  botao nao zera - ele traz de novo as que eu ja fiz. A questao nunca vista
  continua na frente, entao repetir so acontece quando o tema acabou.

O botao "Certo ou Errado" da faixa (PRF-48) e esta mesma rodada, so com os
itens de Certo/Errado (`so_certo_errado`): antes era uma lista com o gabarito
no clique, que nao deixava responder.

A faixa de Portugues no Qconcursos continua com o bloco dela (decisao 107): la
o botao ja existe, e dois botoes para as mesmas questoes seriam um a mais.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date

from radar import conteudos as arvore
from radar.db import criar_tabelas, sessao
from radar.models import RespostaDeSimulado, Simulado
from radar.servico import composicao, evidencia

#: O nome da rodada em `Simulado.filtros`.
RODADA = "fepese_no_radar"

#: O teto de uma rodada, o mesmo do treino de geradas.
MAXIMO_DA_RODADA = 30


def _dentro(conteudo: str, nos: list[str]) -> bool:
    return any(conteudo == no or conteudo.startswith(no + arvore.SEPARADOR) for no in nos)


def do_tema(nos: list[str], estoque: dict | None = None) -> list[composicao.Candidata]:
    """As questoes reais da FEPESE dentro dos nos, uma por chave, na ordem do id."""
    nos = [n for n in nos if n]
    if not nos:
        return []
    estoque = composicao.estoque_real() if estoque is None else estoque
    vistas, saida = set(), []
    for lista in estoque.values():
        for c in lista:
            if c.chave in vistas or not _dentro(c.conteudo, nos):
                continue
            vistas.add(c.chave)
            saida.append(c)
    return sorted(saida, key=lambda c: c.id)


def escolher(candidatas: list, respondidas: set[str], quantidade: int,
             sorteio: random.Random | None = None) -> list:
    """As nunca feitas primeiro e, se faltar, as que eu ja fiz (PRF-66); cada
    grupo embaralhado; no maximo `quantidade`."""
    sorteio = sorteio or random.Random()
    novas = [c for c in candidatas if c.impressao not in respondidas]
    feitas = [c for c in candidatas if c.impressao in respondidas]
    sorteio.shuffle(novas)
    sorteio.shuffle(feitas)
    return (novas + feitas)[:max(quantidade, 0)]


def ids_de_certo_errado(candidatas: list) -> set[int]:
    """Das candidatas, os ids dos itens de Certo/Errado (uma consulta so)."""
    from radar.servico import metricas

    if not candidatas:
        return set()
    criar_tabelas()
    with sessao() as s:
        return metricas.ids_de_certo_errado(s, {c.id for c in candidatas})


@dataclass
class FepeseDaFaixa:
    """O que a tela Hoje mostra numa faixa: quantas reais da FEPESE o tema tem,
    quantas ficam guardadas para a rodada que mede e quantas eu ja fiz."""

    nos: list[str]
    no_acervo: int
    reservadas: int
    feitas: int
    do_alvo: int
    dias_da_reserva: list[date] = field(default_factory=list)
    questoes_da_faixa: int | None = None
    #: Os itens de Certo/Errado livres (fora da reserva) e, deles, os que eu
    #: nunca fiz: o botao "Certo ou Errado" (PRF-48).
    certo_errado: int = 0
    certo_errado_novos: int = 0

    @property
    def disponiveis(self) -> int:
        return max(self.no_acervo - self.reservadas, 0)

    @property
    def novas(self) -> int:
        return max(self.disponiveis - self.feitas, 0)

    @property
    def sugeridas(self) -> int:
        """O que o botao traz: o numero da faixa, sem passar das do tema fora
        da reserva nem do teto. As ja feitas contam (PRF-66): zero so quando o
        tema nao tem questao livre."""
        quantas = self.questoes_da_faixa or 10
        return min(quantas, self.disponiveis, MAXIMO_DA_RODADA)

    @property
    def certo_errado_sugeridos(self) -> int:
        quantas = self.questoes_da_faixa or 10
        return min(quantas, self.certo_errado, MAXIMO_DA_RODADA)


def da_faixa(nos: list[str], reserva: composicao.Reserva, *,
             questoes_da_faixa: int | None = None, estoque: dict | None = None,
             respondidas: set[str] | None = None,
             de_certo_errado: set[int] | None = None) -> FepeseDaFaixa:
    """O resumo de uma faixa. Sempre devolve: a faixa sem questao da FEPESE no
    tema tambem diz isso. `de_certo_errado` sao os ids de Certo/Errado do
    estoque (a tela pergunta uma vez para todas as faixas)."""
    candidatas = do_tema(nos, estoque)
    respondidas = composicao.ja_respondidas() if respondidas is None else respondidas
    livres = [c for c in candidatas if c.chave not in reserva.chaves]
    guardadas = [c.chave for c in candidatas if c.chave in reserva.chaves]
    if de_certo_errado is None:
        de_certo_errado = ids_de_certo_errado(livres)
    livres_ce = [c for c in livres if c.id in de_certo_errado]
    return FepeseDaFaixa(
        nos=list(nos), no_acervo=len(candidatas),
        reservadas=len(guardadas),
        feitas=sum(1 for c in livres if c.impressao in respondidas),
        do_alvo=sum(1 for c in livres if c.evidencia == evidencia.ALVO),
        # O dia de cada questao guardada DESTE tema (sem o dia, o da reserva toda).
        dias_da_reserva=reserva.dias_das(guardadas) or (list(reserva.dias) if guardadas else []),
        questoes_da_faixa=questoes_da_faixa,
        certo_errado=len(livres_ce),
        certo_errado_novos=sum(1 for c in livres_ce if c.impressao not in respondidas))


def das_faixas(geradas_das_faixas: dict, data: date, reserva: composicao.Reserva | None = None,
               fora: set | None = None, pedidas: dict | None = None) -> dict:
    """{(bloco, indice): FepeseDaFaixa} das faixas de treino do dia, pelos nos
    que a faixa ja diz. `fora` sao as chaves (bloco, indice) que ja tem o bloco
    da decisao 107 (a de Portugues no Qconcursos). `pedidas` e o
    `cronograma.pedidas_das_faixas`: a rodada traz o que falta da faixa
    (decisao 185); sem ele, o numero dela."""
    com_nos = {chave: gf for chave, gf in (geradas_das_faixas or {}).items()
               if not gf.sem_no and gf.nos and chave not in (fora or set())}
    if not com_nos:
        return {}
    reserva = reserva if reserva is not None else composicao.reserva_das_que_medem(data)
    estoque = composicao.estoque_real()
    respondidas = composicao.ja_respondidas()
    de_certo_errado = ids_de_certo_errado([c for lista in estoque.values() for c in lista])
    pedidas = pedidas or {}
    return {chave: da_faixa([n.no for n in gf.nos], reserva,
                            questoes_da_faixa=(pedidas[chave].quantas if chave in pedidas
                                               else gf.questoes),
                            estoque=estoque, respondidas=respondidas,
                            de_certo_errado=de_certo_errado)
            for chave, gf in com_nos.items()}


def criar_rodada(nos: list[str], quantidade: int, data: date,
                 da_faixa_do_dia: dict | None = None,
                 sorteio: random.Random | None = None,
                 so_certo_errado: bool = False) -> Simulado | None:
    """A rodada de treino com as reais da FEPESE dos nos, sem as reservadas;
    as nunca feitas primeiro (PRF-66). None sem questao livre. `so_certo_errado`
    e o botao "Certo ou Errado": so os itens de Certo/Errado."""
    nos = [n for n in nos if n]
    reserva = composicao.reserva_das_que_medem(data)
    livres = [c for c in do_tema(nos) if c.chave not in reserva.chaves]
    if so_certo_errado:
        de_certo_errado = ids_de_certo_errado(livres)
        livres = [c for c in livres if c.id in de_certo_errado]
    quantidade = max(1, min(quantidade, MAXIMO_DA_RODADA))
    escolhidas = escolher(livres, composicao.ja_respondidas(), quantidade, sorteio)
    if not escolhidas:
        return None
    filtros = {
        "quantidade": len(escolhidas),
        "rodada": RODADA,
        "nos": nos,
        "proprias": sum(1 for c in escolhidas if c.evidencia == evidencia.ALVO),
        "da_banca": sum(1 for c in escolhidas if c.evidencia == evidencia.COMPLEMENTAR),
        **({"so_certo_errado": True} if so_certo_errado else {}),
    }
    if da_faixa_do_dia:
        filtros["da_faixa"] = da_faixa_do_dia
    criar_tabelas()
    with sessao() as s:
        simulado = Simulado(filtros=filtros)
        s.add(simulado)
        s.flush()
        for ordem, candidata in enumerate(escolhidas, start=1):
            s.add(RespostaDeSimulado(simulado_id=simulado.id,
                                     questao_id=candidata.id, ordem=ordem))
    return simulado

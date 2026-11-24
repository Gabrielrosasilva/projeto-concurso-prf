"""O Simulado PMSC dos sabados de 14/11 a 05/12 (Etapa 5 da PMSC, decisao PMSC-9).

Como no dia 13/12: 60 questoes na proporcao do edital e a redacao, em 5 horas.

- **a composicao e a do bloco `materias`** do cronograma (a do edital: 8 de
  Constitucional, 10 de Institucional...), e nao a regra dos temas da semana
  do Simulado da semana (decisao 170). A faixa diz isso com
  `proporcao_do_edital`;
- **cada materia sai primeiro do radar, na ordem do pedido da PMSC**: as
  reais da banca do alvo (a AOCP, o complementar aceito; sem as reservadas de
  uma rodada que mede), depois as reais de outras bancas, e so entao as
  geradas, onde faltar questao real - a Institucional, que nao tem nenhuma.
  As nunca feitas primeiro em todas;
- **e TREINO, e nao rodada que mede**: entra gerada, e rodada com gerada nunca
  mede (regra do projeto). A faixa tem `treino`, o `composicao.mede` a recusa,
  e a rodada daqui nao esta nas `RODADAS_QUE_MEDEM`. Corrige no fim, como a
  prova (`simulado.RODADAS_CORRIGIDAS_NO_FIM`);
- **o resultado por materia, contra a `meta`**: a rodada guarda de que materia
  saiu cada questao (a de outra banca muitas vezes nao tem `materia` no
  banco), e a conta e do `metricas.placar_por_grupo`. As reais e as geradas
  NUNCA se somam: cada uma e comparada com a porcentagem da meta, separada;
- **5 horas com a redacao dentro**: a rodada guarda o fim da prova
  (`fim_da_prova`), e a tela da questao diz quanto falta - a redacao, a mao,
  vai nessas mesmas 5 horas. Sem JavaScript: o tempo e o da hora em que a
  pagina abriu.

A escolha das reais e deterministica (a semente e a faixa), e a rodada criada
guarda o que escolheu: criada, ela nao e recriada.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from radar.db import criar_tabelas, sessao
from radar.models import RespostaDeSimulado, Simulado, agora
from radar.servico import composicao, fepese_no_radar, geradas, metricas, outras_bancas

#: O nome da rodada em `Simulado.filtros`.
RODADA = "simulado_pmsc"

#: O tempo da prova, com a redacao dentro (edital, item 8: 5 horas).
MINUTOS_DA_PROVA = 300


def aceita(faixa) -> bool:
    """O Simulado PMSC: simulado de treino com as questoes na proporcao do edital."""
    return (faixa is not None and faixa.tipo == "simulado"
            and bool(getattr(faixa, "treino", False))
            and bool(getattr(faixa, "proporcao_do_edital", False)))


@dataclass
class MateriaDoSimulado:
    """Uma materia do simulado: quantas o edital pede, a meta e de onde saem."""

    materia: str
    pedidas: int
    meta: int
    da_banca: list[int] = field(default_factory=list)   # ids de questoes reais da AOCP
    outras: list[int] = field(default_factory=list)     # ids de reais de outras bancas
    geradas: list[int] = field(default_factory=list)    # ids de geradas

    @property
    def reais(self) -> int:
        return len(self.da_banca) + len(self.outras)

    @property
    def faltam(self) -> int:
        return max(self.pedidas - self.reais - len(self.geradas), 0)


@dataclass
class SimuladoPMSC:
    materias: list[MateriaDoSimulado]
    rodada_id: int | None = None

    @property
    def pedidas(self) -> int:
        return sum(m.pedidas for m in self.materias)

    @property
    def da_banca(self) -> int:
        return sum(len(m.da_banca) for m in self.materias)

    @property
    def outras(self) -> int:
        return sum(len(m.outras) for m in self.materias)

    @property
    def geradas(self) -> int:
        return sum(len(m.geradas) for m in self.materias)

    @property
    def faltam(self) -> int:
        return sum(m.faltam for m in self.materias)


def _semente(data: date, bloco: str, indice: int) -> str:
    return f"{RODADA}:{data.isoformat()}:{bloco}:{indice}"


def planejar(data: date, bloco: str, indice: int, faixa, plano) -> SimuladoPMSC:
    """A composicao do simulado, materia por materia, sem gravar nada."""
    sorteio = random.Random(_semente(data, bloco, indice))
    reserva = composicao.reserva_das_que_medem(data)
    estoque = composicao.estoque_real()
    respondidas = composicao.ja_respondidas()
    feitas_de_outras = outras_bancas.respondidas()
    geradas_feitas = set(metricas.ultimas_das_geradas())
    materias = []
    for item in plano.materias:
        da_materia = MateriaDoSimulado(materia=item.nome, pedidas=item.questoes, meta=item.meta)
        da_banca = [c for c in fepese_no_radar.do_tema([item.nome], estoque)
                    if c.chave not in reserva.chaves]
        de_outras = outras_bancas.estoque([item.nome])
        # As reais primeiro, em duas passadas: as que eu nunca fiz (a AOCP,
        # depois outras bancas) e so entao as que ja fiz. Sem isso, o 3o
        # sabado repetiria a AOCP do 1o antes de usar a de outra banca que eu
        # nunca vi.
        for nunca_feita in (True, False):
            for fonte, lista, feita in (
                    (da_materia.da_banca, da_banca, lambda c: c.impressao in respondidas),
                    (da_materia.outras, de_outras, lambda c: c.mesma in feitas_de_outras)):
                falta = item.questoes - da_materia.reais
                if falta <= 0:
                    break
                grupo = [c for c in lista if feita(c) != nunca_feita and c.id not in fonte]
                sorteio.shuffle(grupo)
                fonte += [c.id for c in grupo[:falta]]
        materias.append(da_materia)
    # As geradas so onde falta questao real (o pedido da PMSC), as nunca
    # feitas primeiro. Nenhuma com o mesmo id de uma real da rodada: a
    # resposta e achada pelo `questao_id`, e as duas tabelas tem ids proprios.
    ids_reais = {i for m in materias for i in m.da_banca + m.outras}
    for da_materia in materias:
        falta = da_materia.pedidas - da_materia.reais
        if falta <= 0:
            continue
        de_ia = [i for i in geradas._sortear(falta * 4 + len(ids_reais), conteudo=da_materia.materia)
                 if i not in ids_reais]
        nunca = [i for i in de_ia if i not in geradas_feitas]
        feitas = [i for i in de_ia if i in geradas_feitas]
        da_materia.geradas = (nunca + feitas)[:falta]
    existente = composicao.rodada_da_faixa(data, bloco, indice, faixa)
    return SimuladoPMSC(materias=materias, rodada_id=existente.id if existente else None)


def criar_rodada(data: date, bloco: str, indice: int, faixa, plano) -> Simulado | None:
    """A rodada do simulado, ou a que ja existe. None sem questao nenhuma."""
    if not aceita(faixa):
        return None
    existente = composicao.rodada_da_faixa(data, bloco, indice, faixa)
    if existente is not None:
        return existente
    planejado = planejar(data, bloco, indice, faixa, plano)
    sorteio = random.Random(_semente(data, bloco, indice))
    ordem_das_questoes: list[tuple[bool, int, str]] = []
    for m in planejado.materias:
        da_materia = ([(False, i, m.materia) for i in m.da_banca + m.outras]
                      + [(True, i, m.materia) for i in m.geradas])
        sorteio.shuffle(da_materia)
        ordem_das_questoes += da_materia
    if not ordem_das_questoes:
        return None
    comeco = agora()
    criar_tabelas()
    with sessao() as s:
        simulado = Simulado(filtros={
            "quantidade": len(ordem_das_questoes),
            "rodada": RODADA,
            # A mesma identidade das rodadas da faixa: e por ela que a faixa
            # acha a rodada, e que o "Fiz hoje" conta o que eu respondi.
            "faixa": composicao.identidade_da_faixa(data, bloco, indice, faixa),
            "treino": True,
            "fim_da_prova": (comeco + timedelta(minutes=MINUTOS_DA_PROVA)).isoformat(),
            RODADA: {
                "materias": [{"materia": m.materia, "pedidas": m.pedidas, "meta": m.meta,
                              "da_banca": len(m.da_banca), "outras": len(m.outras),
                              "geradas": len(m.geradas)} for m in planejado.materias],
                # De que materia saiu cada questao: "r:<id>" ou "g:<id>".
                "grupo_de": {f"{'g' if gerada else 'r'}:{i}": materia
                             for gerada, i, materia in ordem_das_questoes},
            },
        })
        s.add(simulado)
        s.flush()
        for ordem, (gerada, questao_id, _materia) in enumerate(ordem_das_questoes, start=1):
            s.add(RespostaDeSimulado(simulado_id=simulado.id, questao_id=questao_id,
                                     ordem=ordem, gerada=gerada))
    return simulado


def das_faixas(blocos, data: date, plano) -> dict:
    """{(bloco, indice): SimuladoPMSC} do dia. Dia sem ele nao conta nada."""
    if plano is None:
        return {}
    return {(bloco.chave, indice): planejar(data, bloco.chave, indice, faixa, plano)
            for bloco in blocos for indice, faixa in enumerate(bloco.faixas) if aceita(faixa)}


def e_desta(simulado: Simulado | None) -> bool:
    return simulado is not None and (simulado.filtros or {}).get("rodada") == RODADA


def minutos_que_faltam(simulado: Simulado | None, quando: datetime | None = None) -> int | None:
    """Quantos minutos faltam para acabar as 5 horas (0 quando ja acabaram),
    ou None quando a rodada nao e o Simulado PMSC."""
    if not e_desta(simulado):
        return None
    fim = (simulado.filtros or {}).get("fim_da_prova")
    if not fim:
        return None
    fim = datetime.fromisoformat(fim)
    quando = quando or agora()
    if fim.tzinfo is not None and quando.tzinfo is None:
        quando = quando.replace(tzinfo=fim.tzinfo)
    return max(int((fim - quando).total_seconds() // 60), 0)


def tempo_que_falta(simulado: Simulado | None, quando: datetime | None = None) -> str | None:
    """O tempo que falta das 5 horas, escrito ("3h12"; "0h00" quando
    acabou), ou None quando a rodada nao e o Simulado PMSC."""
    minutos = minutos_que_faltam(simulado, quando)
    if minutos is None:
        return None
    return f"{minutos // 60}h{minutos % 60:02d}"


@dataclass
class LinhaDoResultado:
    """Uma materia no resultado: as reais e as geradas, nunca somadas, cada
    uma contra a porcentagem da meta."""

    materia: str
    pedidas: int
    meta: int
    reais: metricas.DesempenhoDaMateria
    geradas: metricas.DesempenhoDaMateria

    @property
    def porcentagem_da_meta(self) -> float:
        return self.meta / self.pedidas * 100 if self.pedidas else 0.0

    @staticmethod
    def _bateu(parte: metricas.DesempenhoDaMateria, alvo: float) -> bool | None:
        return None if not parte.respondidas else parte.porcentagem >= alvo

    @property
    def reais_bateram(self) -> bool | None:
        return self._bateu(self.reais, self.porcentagem_da_meta)

    @property
    def geradas_bateram(self) -> bool | None:
        return self._bateu(self.geradas, self.porcentagem_da_meta)


@dataclass
class ResultadoDoSimulado:
    """O resultado inteiro: as reais e as geradas da rodada, separadas, e uma
    linha por materia."""

    reais: metricas.DesempenhoDaMateria
    geradas: metricas.DesempenhoDaMateria
    linhas: list[LinhaDoResultado]


def resultado(simulado: Simulado) -> ResultadoDoSimulado | None:
    """O resultado por materia, na ordem do bloco `materias`. None quando a
    rodada nao e o Simulado PMSC."""
    if not e_desta(simulado):
        return None
    dado = (simulado.filtros or {}).get(RODADA) or {}
    placares = metricas.placar_por_grupo(simulado.id, dado.get("grupo_de") or {})
    linhas = []
    for m in dado.get("materias") or []:
        reais, de_ia = placares.get(m["materia"], (
            metricas.DesempenhoDaMateria(m["materia"]),
            metricas.DesempenhoDaMateria(m["materia"], origem=metricas.IA)))
        linhas.append(LinhaDoResultado(materia=m["materia"], pedidas=m["pedidas"],
                                       meta=m["meta"], reais=reais, geradas=de_ia))
    reais, de_ia = metricas.placar_separado(simulado.id)
    return ResultadoDoSimulado(reais=reais, geradas=de_ia, linhas=linhas)

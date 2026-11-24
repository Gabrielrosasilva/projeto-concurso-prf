"""O Simulado da semana dos sabados leves: treina, nao mede (decisao 170).

De 24/10 em diante o sabado tem umas 2 horas, num bloco so, e o simulado e
feito AQUI, no radar - na PMSC, sem nada no Qconcursos (decisao PMSC-25):

- **a composicao e a da decisao 69, em duas partes**: `questoes - anteriores`
  entre os temas da semana (de segunda a sexta: a semana do plano) e
  `anteriores` entre os temas de semanas anteriores. Cada parte e o
  `composicao.compor_por_tema` de sempre - com a janela da semana, ou antes
  dela;
- **cada tema sai primeiro do radar, questao real**: as da banca do alvo fora
  da reserva das rodadas que medem (decisao 167), depois as de outras bancas
  (decisao 166), as nunca feitas primeiro em todas. Onde nao ha real (a
  Institucional da PMSC), completa com as geradas do no, como o Simulado
  PMSC (pedido de 30/10, decisao PMSC-25); o que nem assim houver fica
  faltando, e a tela diz. As reais e as geradas nunca se somam no resultado;
- **o que eu errei ou chutei vem primeiro** (pedido de 30/10): em cada tema,
  a questao cuja ultima resposta minha foi errada, ou marcada no chute, entra
  antes da nunca feita - o simulado diz se eu corrigi o erro. Vale para a
  real e para a gerada;
- **dois botoes, e cada clique gera um simulado novo**: o GERAR SIMULADO
  (`criar_rodada`) e o GERAR SIMULADO IA (`criar_rodada_de_ia`, a mesma
  composicao so com geradas). O que esta pela metade reabre; terminado, o
  proximo clique sorteia outro, e o que eu errei no anterior vem primeiro.
  As rodadas guardam a faixa em `da_faixa` (o "Fiz hoje" e o fechamento da
  faixa contam por ela), e nao em `faixa`: a faixa tem varias;
- **liberado a partir da sexta da semana**: os temas sao os de segunda a
  sexta, e gerar antes disso pegaria tema que eu ainda nao estudei;
- **e TREINO, e nao rodada que mede**: a faixa tem `treino`, o
  `composicao.mede` a recusa, e a rodada daqui (`simulado_da_semana`) nao
  esta nas `RODADAS_QUE_MEDEM`. Ela nao reserva questao, nao tira questao do
  fechamento de 07/11 e nao entra na comparacao. A resposta conta no acumulado
  do ciclo como qualquer questao real respondida no radar, com a origem ao
  lado; a parte feita no Qconcursos continua fora (decisao 146);
- **corrige no fim**, como simulado (`simulado.corrige_na_hora`).

A escolha e deterministica (a semente e a faixa - data, bloco e posicao - e
a vez do clique), e a rodada criada guarda o que escolheu.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select

from radar import conteudos as arvore
from radar import niveis
from radar.db import criar_tabelas, sessao
from radar.models import QuestaoDeProva, QuestaoGerada, RespostaDeSimulado, Simulado
from radar.origem import AUTOMATICO
from radar.servico import (compilado, composicao, evidencia, fepese_no_radar, metricas,
                           outras_bancas)

#: O nome da rodada em `Simulado.filtros`.
RODADA = "simulado_da_semana"

#: A rodada so de geradas da mesma faixa (decisao PMSC-25).
RODADA_DE_IA = "simulado_da_semana_ia"

#: As duas partes da composicao.
SEMANA, ANTERIORES = "semana", "anteriores"

#: De onde veio a questao escolhida.
FEPESE, OUTRA_BANCA, GERADA = "fepese", "outra_banca", "gerada"

REGRA = ("decisão 170: a regra da 69 em duas partes (os temas da semana e os de "
         "antes), cada tema primeiro do radar com questão real, e as geradas "
         "onde falta real (PMSC-25)")


def aceita(faixa) -> bool:
    """O Simulado da semana: simulado com `treino` e as materias escritas."""
    # O Simulado PMSC (decisao PMSC-9) tambem e simulado de treino com as
    # materias escritas, mas a composicao dele e a do edital: nao e daqui.
    return (faixa is not None and faixa.tipo == "simulado"
            and bool(getattr(faixa, "treino", False)) and bool(faixa.questoes)
            and bool(getattr(faixa, "materias_da_rodada", ()))
            and not getattr(faixa, "proporcao_do_edital", False))


@dataclass
class TemaDoSimulado:
    """Um tema da composicao: quantas o plano pede e de onde elas saem."""

    parte: str                    # SEMANA ou ANTERIORES
    materia: str
    tema: str
    estudado_em: date | None
    pedidas: int
    fepese: int = 0               # reais da FEPESE do radar
    outras: int = 0               # reais de outras bancas do radar
    filtro: str | None = None     # o filtro escrito no plano, sem link do site
    sem_no: bool = False          # sem no, o radar nao acha questao do tema
    geradas: int = 0              # geradas que completam a falta de real
    a_rever: int = 0              # das escolhidas, as que eu errei ou chutei
    #: As geradas do tema para o "Simulado so com IA", ate `pedidas`, na
    #: ordem de treino, e os nos dele. Nao sao gravados: a rodada de IA
    #: guarda as dela.
    de_ia: list[int] = field(default_factory=list)
    nos: list[str] = field(default_factory=list)

    @property
    def do_radar(self) -> int:
        """As reais do radar (as geradas ficam a parte, nunca somadas)."""
        return self.fepese + self.outras

    @property
    def faltam(self) -> int:
        """O que nem real nem gerada cobre: a tela diz, e nao manda a site."""
        return max(self.pedidas - self.do_radar - self.geradas, 0)


@dataclass
class Escolhida:
    questao_id: int
    origem: str                   # FEPESE, OUTRA_BANCA ou GERADA
    evidencia: str | None         # alvo | complementar | fora; None na gerada
    banca: str | None = None

    @property
    def gerada(self) -> bool:
        return self.origem == GERADA


@dataclass
class ARever:
    """O que eu errei ou chutei da ultima vez que respondi: a real pela
    impressao (a da banca do alvo) e pela `mesma` (a de outra banca), como o
    "ja feita" de cada uma; a gerada pelo id."""

    impressoes: set[str] = field(default_factory=set)
    mesmas: set[str] = field(default_factory=set)
    geradas: set[int] = field(default_factory=set)


def a_rever() -> ARever:
    """A ultima resposta de cada questao, errada ou no chute (pedido de 30/10:
    o simulado refaz o que eu errei e o que eu chutei na semana)."""
    def rever(r) -> bool:
        return not r.acertou or bool(r.chutou)

    criar_tabelas()
    with sessao() as s:
        ids = [i for i, r in metricas.ultimas_respostas_reais(s).items() if rever(r)]
        questoes = (list(s.scalars(select(QuestaoDeProva).where(QuestaoDeProva.id.in_(ids))))
                    if ids else [])
        saida = ARever(impressoes={q.impressao for q in questoes},
                       mesmas={outras_bancas.mesma_questao(q) for q in questoes})
    saida.geradas = {i for i, r in metricas.ultimas_das_geradas().items() if rever(r)}
    return saida


@dataclass(frozen=True)
class GeradaNoEstoque:
    """Uma gerada aceita, com o no e a materia: o que a escolha precisa."""

    id: int
    conteudo: str
    materia: str | None


@dataclass
class SimuladoDaSemana:
    """O que a tela Hoje e o `radar hoje` mostram no Simulado da semana."""

    tipo = "simulado_da_semana"
    origem = AUTOMATICO

    inicio_da_semana: date
    total: int
    anteriores: int
    temas: list[TemaDoSimulado]
    escolhidas: list[Escolhida] = field(default_factory=list)
    regra: str = REGRA
    #: Os simulados ja gerados nesta faixa, na ordem em que foram gerados.
    rodadas: list["RodadaGerada"] = field(default_factory=list)
    #: Os botoes so geram depois da sexta da semana (os temas ja estudados).
    liberado: bool = False

    @property
    def da_parte_da_semana(self) -> int:
        """Quantas o plano pede dos temas da semana: o total menos as de antes."""
        return self.total - self.anteriores

    @property
    def da_semana(self) -> list[TemaDoSimulado]:
        return [t for t in self.temas if t.parte == SEMANA]

    @property
    def de_antes(self) -> list[TemaDoSimulado]:
        return [t for t in self.temas if t.parte == ANTERIORES]

    @property
    def do_radar(self) -> int:
        return sum(t.do_radar for t in self.temas)

    @property
    def faltam(self) -> int:
        return sum(t.faltam for t in self.temas)

    @property
    def em_andamento(self) -> "RodadaGerada | None":
        """O GERAR SIMULADO pela metade: o botao reabre ele."""
        return next((r for r in self.rodadas if not r.de_ia and not r.terminada), None)

    @property
    def em_andamento_ia(self) -> "RodadaGerada | None":
        return next((r for r in self.rodadas if r.de_ia and not r.terminada), None)

    @property
    def terminadas(self) -> list["RodadaGerada"]:
        return [r for r in self.rodadas if r.terminada]

    @property
    def geradas(self) -> int:
        return sum(t.geradas for t in self.temas)

    @property
    def a_rever(self) -> int:
        return sum(t.a_rever for t in self.temas)

    @property
    def de_ia(self) -> int:
        """Quantas geradas o "Simulado so com IA" teria."""
        return sum(len(t.de_ia) for t in self.temas)

    @property
    def fim_da_semana(self) -> date:
        """A sexta da semana: os temas da semana vao de segunda ate ela."""
        return self.inicio_da_semana + timedelta(days=4)

    def como_dicionario(self) -> dict:
        """O que a rodada grava: a regra e, por tema, quanto e de onde."""
        return {
            "regra": self.regra,
            "inicio_da_semana": self.inicio_da_semana.isoformat(),
            "total": self.total,
            "anteriores": self.anteriores,
            "temas": [{
                "parte": t.parte, "materia": t.materia, "tema": t.tema,
                "estudado_em": t.estudado_em.isoformat() if t.estudado_em else None,
                "pedidas": t.pedidas, "fepese": t.fepese, "outras": t.outras,
                "geradas": t.geradas, "a_rever": t.a_rever,
                "filtro": t.filtro, "sem_no": t.sem_no,
            } for t in self.temas],
        }


# --- a composicao ----------------------------------------------------------------

def inicio_da_semana(data: date, plano) -> date:
    """O primeiro dia da semana do plano de `data` - a segunda. E a semana do
    plano, e nao a do calendario, como na revisao do sabado (decisao 70)."""
    dia = plano.dia(data)
    if dia is not None:
        da_semana = [d.data for d in plano.dias if d.semana == dia.semana]
        if da_semana:
            return min(da_semana)
    return data - timedelta(days=data.weekday())


def _partes(data: date, faixa, plano, contexto) -> tuple[date, list]:
    """[(parte, Composicao)]: a da semana e a de antes, pela regra da 69."""
    inicio = inicio_da_semana(data, plano)
    anteriores = faixa.anteriores or 0
    materias = list(faixa.materias_da_rodada)
    partes = [(SEMANA, composicao.compor_por_tema(
        data, materias, faixa.questoes - anteriores, plano, contexto=contexto, desde=inicio))]
    if anteriores:
        partes.append((ANTERIORES, composicao.compor_por_tema(
            inicio, materias, anteriores, plano, contexto=contexto)))
    return inicio, partes


def _dentro(conteudo: str, nos: list[str]) -> bool:
    return any(conteudo == no or conteudo.startswith(no + arvore.SEPARADOR) for no in nos)


def _geradas_do_tema(estoque: list[GeradaNoEstoque], nos: list[str], materia: str,
                     feitas: set[int], sorteio: random.Random,
                     rever: set[int] | None = None) -> list[int]:
    """As geradas do tema: as que eu errei ou chutei, as nunca feitas, e so
    entao as que acertei. Tema sem no usa as da materia: e melhor treinar a
    materia do que deixar o buraco."""
    if nos:
        ids = [g.id for g in estoque if _dentro(g.conteudo, nos)]
    else:
        ids = [g.id for g in estoque
               if g.materia and compilado.mesma_materia(g.materia, materia)]
    rever = rever or set()
    primeiro = sorted(i for i in ids if i in rever)
    nunca = sorted(i for i in ids if i not in feitas and i not in rever)
    ja = sorted(i for i in ids if i in feitas and i not in rever)
    for grupo in (primeiro, nunca, ja):
        sorteio.shuffle(grupo)
    return primeiro + nunca + ja


def escolher(partes: list, reserva: composicao.Reserva, estoque_fepese: dict,
             outras: list, feitas_reais: set[str], feitas_outras: set[str],
             semente: str, geradas: list[GeradaNoEstoque] | None = None,
             feitas_geradas: set[int] | None = None, rever: ARever | None = None
             ) -> tuple[list[TemaDoSimulado], list[Escolhida]]:
    """Os temas com o que sai do radar, e as questoes escolhidas, em ordem.

    Em cada tema: as da FEPESE nunca feitas, as de outras bancas nunca feitas,
    e so entao as ja feitas (FEPESE antes) - refazer mede memoria. A FEPESE
    reservada para a rodada que mede nao entra. Uma questao uma vez so no
    simulado inteiro: dois temas podem ter o mesmo no.

    Com `geradas`, cada tema separa ate `pedidas` geradas (o `de_ia`, para o
    "Simulado so com IA"), e as primeiras completam o que faltou de real.

    Com `rever`, o que eu errei ou chutei vem antes de tudo, em cada tema."""
    rever = rever or ARever()
    geradas = geradas or []
    feitas_geradas = feitas_geradas or set()
    usadas_geradas: set[int] = set()
    sorteio = random.Random(semente)
    usadas_chave: set[str] = set()
    usadas_enunciado: set[str] = set()
    usadas_mesma: set[str] = set()
    temas: list[TemaDoSimulado] = []
    escolhidas: list[Escolhida] = []
    for parte, comp in partes:
        for materia in comp.materias:
            for a in materia.assuntos:
                if not a.pedidas:
                    continue
                tema = TemaDoSimulado(parte=parte, materia=materia.materia, tema=a.nome,
                                      estudado_em=a.estudado_em, pedidas=a.pedidas,
                                      filtro=a.filtro, sem_no=not a.nos)
                temas.append(tema)
                tema.nos = list(a.nos)
                # As geradas do tema, separadas antes: o "so com IA" pede o
                # tema inteiro, e um no repetido em dois temas nao repete.
                tema.de_ia = [i for i in _geradas_do_tema(
                    geradas, a.nos, materia.materia, feitas_geradas, sorteio,
                    rever.geradas)
                    if i not in usadas_geradas][:a.pedidas]
                usadas_geradas.update(tema.de_ia)
                if not a.nos:
                    _completar_com_geradas(tema, escolhidas, rever.geradas)
                    continue
                fep = [c for c in fepese_no_radar.do_tema(a.nos, estoque_fepese)
                       if c.chave not in reserva.chaves]
                ob = [c for c in outras if _dentro(c.conteudo, a.nos)]
                pares = [(FEPESE, c) for c in fep] + [(OUTRA_BANCA, c) for c in ob]
                grupos = (
                    [(o, c) for o, c in pares if _de_rever(o, c, rever)],
                    [(FEPESE, c) for c in fep if c.impressao not in feitas_reais
                     and not _de_rever(FEPESE, c, rever)],
                    [(OUTRA_BANCA, c) for c in ob if c.mesma not in feitas_outras
                     and not _de_rever(OUTRA_BANCA, c, rever)],
                    [(FEPESE, c) for c in fep if c.impressao in feitas_reais
                     and not _de_rever(FEPESE, c, rever)],
                    [(OUTRA_BANCA, c) for c in ob if c.mesma in feitas_outras
                     and not _de_rever(OUTRA_BANCA, c, rever)],
                )
                for grupo in grupos:
                    sorteio.shuffle(grupo)
                for origem, c in (par for grupo in grupos for par in grupo):
                    if tema.do_radar >= a.pedidas:
                        break
                    if c.chave in usadas_chave:
                        continue
                    if origem == FEPESE:
                        if c.impressao in usadas_enunciado:
                            continue
                        usadas_enunciado.add(c.impressao)
                        tema.fepese += 1
                        escolhidas.append(Escolhida(c.id, FEPESE, c.evidencia))
                    else:
                        if c.mesma in usadas_mesma:
                            continue
                        usadas_mesma.add(c.mesma)
                        tema.outras += 1
                        escolhidas.append(Escolhida(c.id, OUTRA_BANCA, evidencia.FORA, c.banca))
                    usadas_chave.add(c.chave)
                    if _de_rever(origem, c, rever):
                        tema.a_rever += 1
                _completar_com_geradas(tema, escolhidas, rever.geradas)
    return temas, escolhidas


def _de_rever(origem: str, c, rever: ARever) -> bool:
    if origem == FEPESE:
        return c.impressao in rever.impressoes
    return c.mesma in rever.mesmas


def _completar_com_geradas(tema: TemaDoSimulado, escolhidas: list[Escolhida],
                           rever: set[int]) -> None:
    """O que faltou de real no tema, com as geradas dele (PMSC-25)."""
    falta = tema.pedidas - tema.do_radar
    for questao_id in tema.de_ia[:max(falta, 0)]:
        tema.geradas += 1
        if questao_id in rever:
            tema.a_rever += 1
        escolhidas.append(Escolhida(questao_id, GERADA, None))


def estoque_de_geradas() -> list[GeradaNoEstoque]:
    """As geradas que valem para treino: nao rejeitadas e com gabarito."""
    criar_tabelas()
    with sessao() as s:
        linhas = s.execute(select(QuestaoGerada.id, QuestaoGerada.conteudo,
                                  QuestaoGerada.materia)
                           .where(QuestaoGerada.rejeitada.is_(False))
                           .where(QuestaoGerada.resposta.is_not(None)))
        return [GeradaNoEstoque(i, c or "", m) for i, c, m in linhas]


def _semente(data: date, bloco: str, indice: int, vez: int = 1) -> str:
    base = f"{data.isoformat()}|{bloco}|{indice}|{RODADA}"
    # A 1a vez fica com a semente de sempre; cada GERAR de novo sorteia outra.
    return base if vez == 1 else f"{base}|{vez}"


@dataclass
class RodadaGerada:
    """Um simulado ja gerado na faixa: o link, o andamento e o placar, com as
    reais e as geradas separadas (nunca somadas)."""

    id: int
    de_ia: bool
    vez: int
    total: int
    terminada: bool
    reais: metricas.DesempenhoDaMateria
    geradas: metricas.DesempenhoDaMateria

    @property
    def respondidas(self) -> int:
        return self.reais.respondidas + self.geradas.respondidas


def rodadas_da_faixa(data: date, bloco: str, indice: int, faixa) -> list[RodadaGerada]:
    """Os simulados gerados nesta faixa, os dois tipos, em ordem."""
    identidade = composicao.identidade_da_faixa(data, bloco, indice, faixa)
    criar_tabelas()
    with sessao() as s:
        achadas = [(r.id, (r.filtros or {}).get("rodada") == RODADA_DE_IA,
                    (r.filtros or {}).get("quantidade", 0), r.finalizado_em is not None)
                   for r in s.scalars(select(Simulado).order_by(Simulado.id))
                   if (r.filtros or {}).get("rodada") in (RODADA, RODADA_DE_IA)
                   and (r.filtros or {}).get("da_faixa") == identidade]
    saida, vezes = [], {False: 0, True: 0}
    for simulado_id, de_ia, total, terminada in achadas:
        vezes[de_ia] += 1
        reais, geradas = metricas.placar_separado(simulado_id)
        saida.append(RodadaGerada(simulado_id, de_ia, vezes[de_ia], total, terminada,
                                  reais, geradas))
    return saida


def liberado(planejado: SimuladoDaSemana, hoje: date | None = None) -> bool:
    """Da sexta da semana em diante: os temas de segunda a sexta ja passaram."""
    from radar.servico import cronograma as servico_cronograma

    return (hoje or servico_cronograma.hoje_local()) >= planejado.fim_da_semana


def planejar(data: date, bloco: str, indice: int, faixa, plano,
             contexto: composicao.Contexto | None = None,
             hoje: date | None = None) -> SimuladoDaSemana:
    """A composicao de agora - o que o proximo GERAR SIMULADO traria -, com os
    simulados ja gerados na faixa. NAO cria nada."""
    rodadas = rodadas_da_faixa(data, bloco, indice, faixa)
    vez = 1 + sum(1 for r in rodadas if not r.de_ia)
    planejado = _planejar_novo(data, bloco, indice, faixa, plano, contexto, vez)
    planejado.rodadas = rodadas
    planejado.liberado = liberado(planejado, hoje)
    return planejado


def _planejar_novo(data: date, bloco: str, indice: int, faixa, plano,
                   contexto: composicao.Contexto | None = None,
                   vez: int = 1) -> SimuladoDaSemana:
    """A composicao de agora, com as questoes que a vez `vez` escolheria."""
    contexto = contexto or composicao.Contexto.ler(com_estoque=False)
    inicio, partes = _partes(data, faixa, plano, contexto)
    nos = sorted({no for _parte, comp in partes for m in comp.materias
                  for a in m.assuntos if a.pedidas for no in a.nos})
    temas, escolhidas = escolher(
        partes, composicao.reserva_das_que_medem(data, plano), composicao.estoque_real(),
        outras_bancas.estoque(nos), composicao.ja_respondidas(), outras_bancas.respondidas(),
        _semente(data, bloco, indice, vez), estoque_de_geradas(),
        set(metricas.ultimas_das_geradas()), a_rever())
    return SimuladoDaSemana(inicio_da_semana=inicio, total=faixa.questoes,
                            anteriores=faixa.anteriores or 0, temas=temas,
                            escolhidas=escolhidas)


def _rodada(simulado_id: int) -> Simulado:
    with sessao() as s:
        return s.get(Simulado, simulado_id)


def criar_rodada(data: date, bloco: str, indice: int, faixa, plano,
                 hoje: date | None = None) -> Simulado | None:
    """O GERAR SIMULADO: reabre o que esta pela metade, ou gera um novo com a
    composicao de agora. None antes da sexta da semana, ou sem questao."""
    if not aceita(faixa):
        return None
    rodadas = rodadas_da_faixa(data, bloco, indice, faixa)
    andamento = next((r for r in rodadas if not r.de_ia and not r.terminada), None)
    if andamento is not None:
        return _rodada(andamento.id)
    vez = 1 + sum(1 for r in rodadas if not r.de_ia)
    planejado = _planejar_novo(data, bloco, indice, faixa, plano, vez=vez)
    if not liberado(planejado, hoje) or not planejado.escolhidas:
        return None
    escolhidas = planejado.escolhidas
    criar_tabelas()
    with sessao() as s:
        simulado = Simulado(filtros={
            "quantidade": len(escolhidas),
            "rodada": RODADA,
            "vez": vez,
            # Rodada que mistura real e gerada: o resultado sai separado
            # (`metricas.placar_separado`), como no Simulado PMSC.
            "geradas_na_rodada": sum(1 for e in escolhidas if e.gerada),
            # A faixa tem varias rodadas: `da_faixa`, e nao `faixa` (o
            # `composicao.rodada_da_faixa` pega so a primeira). O "Fiz hoje"
            # e o fechamento da faixa contam pelas duas chaves.
            "da_faixa": composicao.identidade_da_faixa(data, bloco, indice, faixa),
            RODADA: planejado.como_dicionario(),
            "proprias": sum(1 for e in escolhidas if e.evidencia == evidencia.ALVO),
            "da_banca": sum(1 for e in escolhidas if e.evidencia == evidencia.COMPLEMENTAR),
            "outras": sum(1 for e in escolhidas if e.origem == OUTRA_BANCA),
            "bancas": sorted({e.banca for e in escolhidas if e.banca}),
        })
        s.add(simulado)
        s.flush()
        # As geradas embaralhadas entre as reais, e nao todas no fim: no fim
        # elas diriam "esta e de IA" antes de eu ler.
        ordem_das_questoes = list(escolhidas)
        random.Random(_semente(data, bloco, indice, vez)).shuffle(ordem_das_questoes)
        for ordem, escolhida in enumerate(ordem_das_questoes, start=1):
            s.add(RespostaDeSimulado(simulado_id=simulado.id,
                                     questao_id=escolhida.questao_id, ordem=ordem,
                                     gerada=escolhida.gerada))
    return simulado


def criar_rodada_de_ia(data: date, bloco: str, indice: int, faixa, plano,
                       hoje: date | None = None) -> Simulado | None:
    """O GERAR SIMULADO IA (decisao PMSC-25): a mesma composicao da faixa, tema
    por tema, so com geradas, as que eu errei ou chutei primeiro. Reabre o que
    esta pela metade, ou gera um novo. None antes da sexta, ou sem gerada.

    E rodada so de geradas (`geradas`): o resultado e o numero da IA, nunca
    somado ao das reais; corrige no fim, como simulado."""
    if not aceita(faixa):
        return None
    rodadas = rodadas_da_faixa(data, bloco, indice, faixa)
    andamento = next((r for r in rodadas if r.de_ia and not r.terminada), None)
    if andamento is not None:
        return _rodada(andamento.id)
    vez = 1 + sum(1 for r in rodadas if r.de_ia)
    planejado = _planejar_novo(data, bloco, indice, faixa, plano, vez=vez)
    ids = [i for t in planejado.temas for i in t.de_ia]
    pedidas = sum(t.pedidas for t in planejado.temas)
    if not liberado(planejado, hoje) or not ids:
        return None
    random.Random(_semente(data, bloco, indice, vez) + "|ia").shuffle(ids)
    criar_tabelas()
    with sessao() as s:
        simulado = Simulado(filtros={
            "quantidade": len(ids),
            "rodada": RODADA_DE_IA,
            "vez": vez,
            # A marca que a tela le para o selo e o resultado so de IA.
            "geradas": True,
            "nivel": niveis.MISTURADA,
            "da_faixa": composicao.identidade_da_faixa(data, bloco, indice, faixa),
            "conteudos": sorted({no for t in planejado.temas if t.de_ia for no in t.nos}),
            **({"faltou": {"pedidas": pedidas, "havia": len(ids)}}
               if len(ids) < pedidas else {}),
        })
        s.add(simulado)
        s.flush()
        for ordem, questao_id in enumerate(ids, start=1):
            s.add(RespostaDeSimulado(simulado_id=simulado.id, questao_id=questao_id,
                                     ordem=ordem, gerada=True))
    return simulado


def das_faixas(blocos, data: date, plano) -> dict:
    """{(bloco, indice): SimuladoDaSemana} do dia. Dia sem ele nao conta nada."""
    if plano is None:
        return {}
    achadas = [(bloco.chave, indice, faixa) for bloco in blocos
               for indice, faixa in enumerate(bloco.faixas) if aceita(faixa)]
    if not achadas:
        return {}
    contexto = composicao.Contexto.ler(com_estoque=False)
    return {(chave, indice): planejar(data, chave, indice, faixa, plano, contexto)
            for chave, indice, faixa in achadas}


def criar_rodada_de_ia_do_dia(data: date, bloco: str, indice: int) -> Simulado | None:
    """O "Simulado so com IA" da faixa `indice` do `bloco`, lida como a tela
    Hoje a mostra (a mesma montagem do `composicao.criar_rodada_do_dia`)."""
    from radar.servico import cronograma as servico_cronograma

    tela = servico_cronograma.tela_do_dia(data)
    for bloco_na_tela in tela.blocos:
        if bloco_na_tela.chave == bloco and 0 <= indice < len(bloco_na_tela.faixas):
            return criar_rodada_de_ia(data, bloco, indice, bloco_na_tela.faixas[indice],
                                      tela.plano)
    return None

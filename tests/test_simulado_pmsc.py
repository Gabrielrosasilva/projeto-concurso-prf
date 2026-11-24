"""O Simulado PMSC dos sabados de 14/11 a 05/12 (decisao PMSC-9).

As fontes de questao (a AOCP, outras bancas, as geradas) sao trocadas por
listas fixas: o que se testa aqui e a regra - a proporcao do edital, a real
antes da gerada, a nunca feita antes da feita, nenhum id repetido entre as
duas tabelas - e o resultado, com as reais e as geradas nunca somadas.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import pytest

from radar import cronograma
from radar.db import sessao
from radar.models import RespostaDeSimulado, Simulado
from radar.servico import (composicao, fepese_no_radar, geradas, metricas, outras_bancas,
                           simulado_da_semana, simulado_pmsc)

SABADO = date(2026, 11, 14)


@dataclass
class _Faixa:
    tipo: str = "simulado"
    titulo: str = "Simulado PMSC completo: 60 questões"
    questoes: int = 60
    treino: bool = True
    proporcao_do_edital: bool = True
    materias_da_rodada: tuple = ("Língua Portuguesa", "Legislação Institucional")


@dataclass
class _Materia:
    nome: str
    questoes: int
    meta: int


@dataclass
class _Plano:
    materias: list = field(default_factory=lambda: [
        _Materia("Língua Portuguesa", 3, 2), _Materia("Legislação Institucional", 2, 1)])


@dataclass
class _DaBanca:          # o que o fepese_no_radar devolve
    id: int
    chave: str
    impressao: str


@dataclass
class _DeOutra:          # o que o outras_bancas devolve
    id: int
    mesma: str


@dataclass
class _Reserva:
    chaves: set = field(default_factory=set)


@pytest.fixture
def fontes(monkeypatch):
    """Portugues: 2 da AOCP (uma ja feita) e 2 de outras bancas (uma ja
    feita). Institucional: nenhuma real, 3 geradas - a de id 11 tem o mesmo
    numero de uma real de Portugues."""
    banca = {"Língua Portuguesa": [_DaBanca(10, "k10", "i10"), _DaBanca(11, "k11", "i11")]}
    outras = {"Língua Portuguesa": [_DeOutra(20, "m20"), _DeOutra(21, "m21")]}
    de_ia = {"Língua Portuguesa": [90], "Legislação Institucional": [11, 30, 31]}
    monkeypatch.setattr(composicao, "reserva_das_que_medem", lambda data: _Reserva())
    monkeypatch.setattr(composicao, "estoque_real", lambda: {})
    monkeypatch.setattr(composicao, "ja_respondidas", lambda: {"i11"})
    monkeypatch.setattr(composicao, "rodada_da_faixa", lambda *a: None)
    monkeypatch.setattr(fepese_no_radar, "do_tema", lambda nos, estoque=None: banca.get(nos[0], []))
    monkeypatch.setattr(outras_bancas, "estoque", lambda nos: outras.get(nos[0], []))
    monkeypatch.setattr(outras_bancas, "respondidas", lambda: {"m21"})
    monkeypatch.setattr(geradas, "_sortear", lambda q, conteudo=None, **_: de_ia.get(conteudo, [])[:q])
    monkeypatch.setattr(metricas, "ultimas_das_geradas", lambda: {30: object()})


def test_so_a_faixa_com_a_proporcao_do_edital_e_o_simulado_pmsc():
    assert simulado_pmsc.aceita(_Faixa())
    assert not simulado_pmsc.aceita(_Faixa(proporcao_do_edital=False))
    assert not simulado_pmsc.aceita(_Faixa(treino=False))
    # E o Simulado da semana nao pega a faixa dele.
    assert not simulado_da_semana.aceita(_Faixa())
    assert simulado_da_semana.aceita(_Faixa(proporcao_do_edital=False))


def test_a_proporcao_do_edital_so_vale_em_simulado_de_treino():
    bruta = {"tipo": "simulado", "titulo": "Simulado", "questoes": 60, "proporcao_do_edital": True}
    with pytest.raises(cronograma.ErroNoCronograma, match="proporcao_do_edital"):
        cronograma._faixa(bruta, "manha", SABADO, set())
    faixa = cronograma._faixa({**bruta, "treino": True}, "manha", SABADO, set())
    assert faixa.proporcao_do_edital


def test_a_real_vem_antes_da_gerada_e_a_nunca_feita_antes_da_feita(fontes):
    plano = simulado_pmsc.planejar(SABADO, "manha", 0, _Faixa(), _Plano())
    portugues, institucional = plano.materias
    # 3 de Portugues: as duas nunca feitas (AOCP 10, outra banca 20) e so
    # depois uma ja feita, ainda REAL (a AOCP 11) - a gerada 90 nao entra.
    assert portugues.da_banca == [10, 11] and portugues.outras == [20]
    assert portugues.geradas == []
    # Institucional nao tem real: 2 geradas, a nunca feita (31) antes da feita
    # (30), e nunca a 11, que tem o numero de uma real da rodada.
    assert institucional.geradas == [31, 30]
    assert (plano.pedidas, plano.da_banca, plano.outras, plano.geradas, plano.faltam) == (5, 2, 1, 2, 0)


def test_o_que_falta_fica_dito(fontes, monkeypatch):
    monkeypatch.setattr(geradas, "_sortear", lambda q, conteudo=None, **_: [])
    plano = simulado_pmsc.planejar(SABADO, "manha", 0, _Faixa(), _Plano())
    assert plano.materias[1].faltam == 2 and plano.faltam == 2


def test_a_rodada_guarda_a_materia_de_cada_questao_e_o_fim_da_prova(fontes, banco_temporario):
    rodada = simulado_pmsc.criar_rodada(SABADO, "manha", 0, _Faixa(), _Plano())
    filtros = rodada.filtros
    assert filtros["rodada"] == simulado_pmsc.RODADA and filtros["treino"] is True
    assert filtros["simulado_pmsc"]["grupo_de"] == {
        "r:10": "Língua Portuguesa", "r:11": "Língua Portuguesa", "r:20": "Língua Portuguesa",
        "g:31": "Legislação Institucional", "g:30": "Legislação Institucional"}
    with sessao() as s:
        respostas = list(s.query(RespostaDeSimulado).filter_by(simulado_id=rodada.id))
    assert sorted((r.gerada, r.questao_id) for r in respostas) == [
        (False, 10), (False, 11), (False, 20), (True, 30), (True, 31)]
    inicio = datetime.fromisoformat(filtros["fim_da_prova"]) - timedelta(minutes=300)
    assert simulado_pmsc.tempo_que_falta(rodada, inicio + timedelta(minutes=48)) == "4h12"
    assert simulado_pmsc.tempo_que_falta(rodada, inicio + timedelta(hours=6)) == "0h00"


def _rodada_respondida(materias, grupo_de, respostas):
    with sessao() as s:
        rodada = Simulado(filtros={"rodada": simulado_pmsc.RODADA, simulado_pmsc.RODADA: {
            "materias": materias, "grupo_de": grupo_de}})
        s.add(rodada)
        s.flush()
        for ordem, (gerada, questao_id, acertou) in enumerate(respostas, start=1):
            s.add(RespostaDeSimulado(simulado_id=rodada.id, questao_id=questao_id, ordem=ordem,
                                     gerada=gerada, escolhida="a", acertou=acertou))
        s.flush()
        s.expunge(rodada)
    return rodada


def test_o_resultado_separa_as_reais_das_geradas_contra_a_meta(banco_temporario):
    materias = [{"materia": "Língua Portuguesa", "pedidas": 4, "meta": 3},
                {"materia": "Legislação Institucional", "pedidas": 2, "meta": 1}]
    # Os ids da gerada sao outros: o banco nao aceita o mesmo `questao_id`
    # duas vezes na rodada (e por isso a composicao evita a colisao).
    grupo_de = {"r:1": "Língua Portuguesa", "r:2": "Língua Portuguesa", "r:3": "Língua Portuguesa",
                "g:101": "Língua Portuguesa", "g:102": "Legislação Institucional",
                "g:103": "Legislação Institucional"}
    rodada = _rodada_respondida(materias, grupo_de, [
        (False, 1, True), (False, 2, True), (False, 3, False),
        (True, 101, False), (True, 102, True), (True, 103, False)])
    resultado = simulado_pmsc.resultado(rodada)
    assert (resultado.reais.acertos, resultado.reais.respondidas) == (2, 3)
    assert (resultado.geradas.acertos, resultado.geradas.respondidas) == (1, 3)
    portugues, institucional = resultado.linhas
    # Portugues: meta 3 de 4 (75%); reais 2/3 (67%) nao bateram; a gerada 0/1.
    assert (portugues.reais.acertos, portugues.reais.respondidas) == (2, 3)
    assert (portugues.geradas.acertos, portugues.geradas.respondidas) == (0, 1)
    assert portugues.reais_bateram is False and portugues.geradas_bateram is False
    # Institucional: so geradas, 1/2 (50%) contra a meta de 1 de 2 (50%).
    assert institucional.reais.respondidas == 0 and institucional.reais_bateram is None
    assert institucional.geradas_bateram is True


def test_rodada_que_nao_e_o_simulado_pmsc_nao_tem_resultado_nem_tempo(banco_temporario):
    with sessao() as s:
        outra = Simulado(filtros={"rodada": "simulado_da_semana"})
        s.add(outra)
        s.flush()
        s.expunge(outra)
    assert simulado_pmsc.resultado(outra) is None
    assert simulado_pmsc.tempo_que_falta(outra) is None

"""A distancia dos aprovados (PRF-34): a minha nota liquida por bloco ao lado da dos
aprovados da PRF 2021.

Os numeros dos aprovados aqui sao de teste, num dicionario fixo; a minha nota sai de
respostas gravadas no banco temporario. Nada de internet nem do dia de hoje.
"""
import pytest
from fastapi.testclient import TestClient

from radar.servico import aprovados
from radar.servico import simulado as rodadas
from radar.web.app import app
from tests.test_certo_errado_prf import _item
from tests.test_correcao_na_hora import _ids, _rodada


def _bloco(itens: int, mediana_geral: float, mediana_1500: float) -> tuple[dict, dict]:
    return ({"itens": itens, "min": 0, "q1": 0, "mediana": mediana_geral, "q3": 0},
            {"itens": itens, "min": 0, "q1": 0, "mediana": mediana_1500, "q3": 0})


def _dados() -> dict:
    blocos = {"I": _bloco(55, 28, 31), "II": _bloco(30, 26, 27), "III": _bloco(35, 25, 26)}
    return {
        "blocos": {"I": ["Língua Portuguesa"], "II": ["Legislação de Trânsito"],
                   "III": ["Direito Penal"]},
        "2021": {
            "corrigidas": 5886, "cairam_na_discursiva": 488, "corte_da_ampla": 73.0,
            "lista_geral": {**{f"bloco_{b}": g for b, (g, _) in blocos.items()}, "n": 5096},
            "as_1500": {**{f"bloco_{b}": m for b, (_, m) in blocos.items()},
                        "objetiva": {"mediana": 83.0}, "discursiva": {"mediana": 17.09}},
        },
    }


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


def test_a_minha_nota_vai_para_o_bloco_da_materia(banco_temporario):
    rodada = _rodada(*(_item(n, "c", materia="Legislação de Trânsito") for n in (1, 2, 3)))
    um, dois, tres = _ids(rodada)
    rodadas.responder(rodada, um, "c")
    rodadas.responder(rodada, dois, "c")
    rodadas.responder(rodada, tres, "e")

    linhas = {l.bloco: l for l in aprovados.distancia(_dados()).linhas}

    transito = linhas["II"]
    assert (transito.minha.certos, transito.minha.errados) == (2, 1)
    assert transito.minha.porcentagem == 33 and transito.mediana_das_1500 == 90
    assert transito.falta == 57 and transito.pouca_amostra
    # Sem resposta no bloco: sem porcentagem e sem "falta".
    assert linhas["I"].minha.porcentagem is None and linhas["I"].falta is None


def test_sem_o_arquivo_nao_ha_cartao(cliente, tmp_path, monkeypatch):
    monkeypatch.setattr(aprovados, "_caminho", lambda: tmp_path / "nao_existe.json")

    assert aprovados.distancia() is None
    assert "A distância dos aprovados" not in cliente.get("/analises/certo-errado").text


def test_a_tela_do_certo_errado_mostra_a_distancia(cliente, monkeypatch):
    monkeypatch.setattr(aprovados, "carregar", lambda caminho=None: _dados())

    tela = cliente.get("/analises/certo-errado").text

    assert "A distância dos aprovados (PRF 2021)" in tela
    assert "Bloco II" in tela and "90%" in tela
    assert "o corte da ampla para ter a discursiva corrigida foi 73 de 120" in tela
    assert "discursiva com mediana 17,09 de 20" in tela
    assert "a mediana dos 5.096 da ampla concorrência, entre 5.886 discursivas corrigidas" in tela

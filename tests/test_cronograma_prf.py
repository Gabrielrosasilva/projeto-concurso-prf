"""O cronograma da PRF, Ciclo 1 (Etapa 5, PRF-35): as regras do metodo no arquivo.

O PRF/config/cronograma.yml foi gerado por script e pode ser editado a mao; este
teste diz se uma edicao quebrou o que o docs/metodo.md promete. Le o arquivo
versionado e a arvore versionada (data/conteudos.json, a do edital da PRF): nada
de internet nem do dia de hoje.
"""
import shutil
from datetime import timedelta

import pytest

from radar import config
from radar import cronograma as plano_de_estudo

ARQUIVO = config.RAIZ / "PRF" / "config" / "cronograma.yml"
SABADO = 5


@pytest.fixture
def plano(tmp_path, monkeypatch):
    # O conftest troca a arvore pela antiga (PRF-9); este plano aponta para a da PRF.
    shutil.copy2(config.RAIZ / "data" / "conteudos.json", tmp_path / "conteudos.json")
    monkeypatch.setenv("RADAR_DATA_DIR", str(tmp_path))
    return plano_de_estudo.carregar(ARQUIVO)


def _uteis(plano):
    return [d for d in plano.dias if d.data.weekday() < SABADO]


def _sabados(plano):
    return [d for d in plano.dias if d.data.weekday() == SABADO]


def test_seis_semanas_de_segunda_a_sabado_a_partir_de_4_de_janeiro(plano):
    assert plano.inicio.isoformat() == "2027-01-04" and len(plano.dias) == 36
    assert len(_uteis(plano)) == 30 and len(_sabados(plano)) == 6


def test_a_prova_de_2021_e_as_metas(plano):
    # Os 120 itens da prova de 2021, e a meta e a soma das metas das materias.
    assert sum(m.questoes for m in plano.materias) == 120
    assert plano.meta_da_prova["acertos"] == sum(m.meta for m in plano.materias) == 96


def test_toda_manha_util_tem_duas_teorias_de_materias_diferentes_com_fixacao(plano):
    for dia in _uteis(plano):
        teorias = [f for f in dia.manha if f.tipo == "teoria"]
        assert len(teorias) == 2, dia.data
        assert teorias[0].materia != teorias[1].materia, dia.data
        fixacoes = [f for f in dia.manha if f.tipo == "questoes" and f.consulta]
        assert [f.materia for f in fixacoes] == [t.materia for t in teorias], dia.data


def test_a_aprendizagem_da_noite_e_sem_consulta_e_do_tema_da_manha(plano):
    for dia in _uteis(plano):
        temas = {f.titulo for f in dia.manha if f.tipo == "teoria"}
        aprendizagem = [f for f in dia.noite if f.titulo.startswith("Aprendizagem: ")]
        assert len(aprendizagem) == 2 and not any(f.consulta for f in aprendizagem), dia.data
        assert {f.titulo.removeprefix("Aprendizagem: ") for f in aprendizagem} == temas


def test_as_revisoes_voltam_ao_tema_daquele_dia(plano):
    # A origem e o compara_com sao texto AAAA-MM-DD, como no cronograma da PMSC.
    por_data = {d.data.isoformat(): d for d in plano.dias}
    revisoes = [(dia, f) for dia in _uteis(plano) for f in dia.noite if f.tipo == "revisao"]
    assert revisoes
    for dia, faixa in revisoes:
        semanas = {"R+7": 1, "R+30": 4}[faixa.rotulo]
        origem = por_data[faixa.origem]
        assert faixa.origem == (dia.data - timedelta(weeks=semanas)).isoformat()
        temas = {f.titulo for f in origem.manha if f.tipo == "teoria"}
        assert faixa.titulo.removeprefix(f"{faixa.rotulo}: ") in temas


def test_o_sabado_mede_na_semana_1_e_na_6_e_treina_no_meio(plano):
    sabados = _sabados(plano)
    rodadas = [next(f for f in s.manha if f.questoes) for s in sabados]
    assert rodadas[0].tipo == "diagnostico" and rodadas[0].questoes == 120
    assert rodadas[-1].tipo == "simulado" and not rodadas[-1].treino
    assert rodadas[-1].compara_com == sabados[0].data.isoformat()
    assert all(r.treino for r in rodadas[1:-1])
    # Toda semana tem redacao no sabado.
    assert all(any(f.materia == "Redação" for f in s.manha) for s in sabados)


def test_transito_e_a_materia_com_mais_teoria(plano):
    contagem = {}
    for dia in _uteis(plano):
        for f in dia.manha:
            if f.tipo == "teoria":
                contagem[f.materia] = contagem.get(f.materia, 0) + 1
    assert sum(contagem.values()) == 60
    assert max(contagem, key=contagem.get) == "Legislação de Trânsito"
    assert len(contagem) == 14

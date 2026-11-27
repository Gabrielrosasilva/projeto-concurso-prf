"""A aba Preparacao Fisica: os pontos do TAF (edital PRF 2021) e os registros.

O taf.yml e uma copia fixa em tests/fixtures/preparacao_fisica/: o teste nao
depende do arquivo de verdade em PRF/config/. Nenhuma data e a de hoje.
"""
import shutil
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from radar import taf
from radar.servico import preparacao_fisica as pf
from radar.web.app import app

FIXTURES = Path(__file__).parent / "fixtures" / "preparacao_fisica"
SEGUNDA = date(2027, 1, 4)


@pytest.fixture
def pasta(banco_temporario, tmp_path, monkeypatch):
    """Config com o taf.yml de teste; os dados (o JSON) no tmp_path."""
    pasta_config = tmp_path / "config"
    pasta_config.mkdir()
    shutil.copy(FIXTURES / "taf.yml", pasta_config / "taf.yml")
    monkeypatch.setenv("RADAR_CONFIG_DIR", str(pasta_config))
    return tmp_path


@pytest.fixture
def regras():
    import yaml
    return yaml.safe_load((FIXTURES / "taf.yml").read_text(encoding="utf-8"))


def _teste(regras, chave):
    return next(t for t in taf.testes(regras) if t.chave == chave)


# --- os pontos, nos limites da tabela do edital ------------------------------

@pytest.mark.parametrize("chave, resultado, pontos", [
    ("barra", 2, 0.0), ("barra", 3, 2.0), ("barra", 5, 3.0), ("barra", 9, 5.0), ("barra", 15, 5.0),
    # O shuttle e "menos e melhor", e o limite e exclusivo: 13,50 a 13,99 = 2.
    ("shuttle", 14.0, 0.0), ("shuttle", 13.99, 2.0), ("shuttle", 13.5, 2.0),
    ("shuttle", 13.49, 2.5), ("shuttle", 11.0, 4.5), ("shuttle", 10.99, 5.0),
    ("impulsao", 2.0, 0.0), ("impulsao", 2.01, 2.0), ("impulsao", 2.15, 3.0), ("impulsao", 2.31, 5.0),
    ("abdominal", 34, 0.0), ("abdominal", 35, 2.0), ("abdominal", 43, 3.0), ("abdominal", 59, 5.0),
    ("corrida", 2300, 0.0), ("corrida", 2301, 2.0), ("corrida", 2601, 3.5), ("corrida", 2901, 5.0),
])
def test_pontos_do_edital_masculino(regras, chave, resultado, pontos):
    assert _teste(regras, chave).pontos(resultado) == pontos


def test_tabela_feminina_quando_o_yml_pede(regras):
    regras["edital"]["sexo"] = "feminino"
    assert _teste(regras, "barra").unidade == "segundos em suspensão"
    assert _teste(regras, "barra").pontos(16) == 3.0
    assert _teste(regras, "corrida").pontos(2001) == 2.0


def test_os_cinco_testes_na_ordem_do_edital(regras):
    assert [t.chave for t in taf.testes(regras)] == [
        "barra", "shuttle", "impulsao", "abdominal", "corrida"]


# --- a regra do item 2.3: minimo 2 em cada E media 3 -------------------------

def test_o_minimo_em_tudo_reprova(regras):
    a = taf.avaliar({"barra": 3, "shuttle": 13.9, "impulsao": 2.01,
                     "abdominal": 35, "corrida": 2301}, regras)
    assert a.media == 2.0
    assert a.aprovado is False
    assert a.reprovados == []
    assert a.falta_para_media == 5.0


def test_media_tres_aprova(regras):
    a = taf.avaliar({"barra": 5, "shuttle": 12.9, "impulsao": 2.11,
                     "abdominal": 43, "corrida": 2501}, regras)
    assert a.media == 3.0
    assert a.aprovado is True


def test_um_zero_reprova_mesmo_com_media_alta(regras):
    a = taf.avaliar({"barra": 15, "shuttle": 10.5, "impulsao": 2.5,
                     "abdominal": 60, "corrida": 2200}, regras)
    assert a.media == 4.0
    assert a.reprovados == ["corrida"]
    assert a.aprovado is False


def test_teste_que_falta_nao_vira_zero(regras):
    a = taf.avaliar({"barra": 10, "abdominal": 50}, regras)
    assert a.media is None and a.aprovado is None
    assert a.faltando == ["shuttle", "impulsao", "corrida"]
    assert a.soma == 8.5


# --- o proximo degrau e o ritmo ----------------------------------------------

def test_proximo_degrau(regras):
    assert _teste(regras, "barra").texto_do_degrau(5) == "mais 1 → 3,5"
    # 12,60 s vale 3; para 3,5 e preciso fazer MENOS que 12,50: 12,49.
    assert _teste(regras, "shuttle").texto_do_degrau(12.6) == "baixar 0,11 s → 3,5"
    assert _teste(regras, "corrida").texto_do_degrau(2550) == "mais 51 m → 3,5"
    assert _teste(regras, "impulsao").texto_do_degrau(2.4) == "nota máxima"


def test_meta_em_resultado(regras):
    assert _teste(regras, "barra").minimo_para(3.5) == 6
    assert _teste(regras, "corrida").minimo_para(3.5) == 2601


def test_ritmo_da_corrida():
    assert taf.ritmo_por_km(2600) == "4:37"
    assert taf.tempo_por_volta(2600) == "1:51"
    assert taf.ritmo_por_km(2400) == "5:00"


# --- os registros ------------------------------------------------------------

def test_registra_e_le_o_ultimo_de_cada_teste(pasta):
    pf.registrar_teste(SEGUNDA, {"barra": 8, "abdominal": 40})
    pf.registrar_teste(SEGUNDA + timedelta(days=14), {"barra": 9, "corrida": None},
                       tipo="treino")
    assert pf.ultimos_resultados() == {"barra": 9.0, "abdominal": 40.0}
    barra = pf.historico()["barra"]
    assert [m.pontos for m in barra] == [4.5, 5.0]
    assert barra[-1].tipo == "treino"


def test_teste_vazio_ou_torto_nao_grava(pasta):
    with pytest.raises(ValueError):
        pf.registrar_teste(SEGUNDA, {"barra": None})
    with pytest.raises(ValueError):
        pf.registrar_teste(SEGUNDA, {"supino": 10})
    with pytest.raises(ValueError):
        pf.registrar_treino(SEGUNDA, "corrida", 30, esforco=11)
    assert pf.ler()["testes"] == [] and pf.ler()["treinos"] == []


def test_apagar(pasta):
    linha = pf.registrar_treino(SEGUNDA, "costas", 60, 7)
    assert pf.apagar("treinos", linha["id"]) is True
    assert pf.ler()["treinos"] == []


# --- a fase do plano ---------------------------------------------------------

def test_sem_liberacao_e_a_fase_zero(pasta):
    assert pf.fase_atual(SEGUNDA).indice == 0


def test_fases_contam_da_liberacao(pasta):
    pf.definir_situacao(SEGUNDA, "salto e tiro")
    assert pf.fase_atual(SEGUNDA - timedelta(days=1)).indice == 0
    primeira = pf.fase_atual(SEGUNDA + timedelta(days=6))
    assert (primeira.indice, primeira.semana) == (1, 1)
    base = pf.fase_atual(SEGUNDA + timedelta(weeks=4))
    assert (base.indice, base.semana) == (2, 1)
    # Sem data do TAF, a Construcao (fase 3) continua ate sair o edital.
    longe = pf.fase_atual(SEGUNDA + timedelta(weeks=40))
    assert (longe.indice, longe.semana) == (3, 31)


def test_com_data_do_taf_a_especifica_comeca_16_semanas_antes(pasta):
    taf_em = date(2027, 9, 6)
    pf.definir_situacao(SEGUNDA, "", taf_em)
    assert pf.fase_atual(taf_em - timedelta(weeks=17)).indice == 3
    especifica = pf.fase_atual(taf_em - timedelta(weeks=16))
    assert (especifica.indice, especifica.semana) == (4, 1)
    contagem = pf.contagem_do_taf(taf_em - timedelta(days=30))
    assert contagem["faltam"] == 30
    assert contagem["atestado_a_partir_de"] == date(2027, 8, 22)


# --- a carga e os avisos -----------------------------------------------------

def test_carga_subindo_rapido_avisa(pasta):
    for semana in range(4):
        pf.registrar_treino(SEGUNDA + timedelta(weeks=semana), "corrida", 30, 5)   # 150
    esta = SEGUNDA + timedelta(weeks=4)
    pf.registrar_treino(esta, "corrida", 40, 6)                                     # 240
    carga = pf.carga_semanal(esta + timedelta(days=2))
    assert carga[-1].carga == 240 and carga[-2].carga == 150
    avisos = pf.avisos(esta + timedelta(days=2))
    assert len(avisos) == 1 and "60%" in avisos[0]


def test_dor_alta_avisa(pasta):
    pf.registrar_treino(SEGUNDA, "pernas", 50, 7, dor=5)
    assert any("Dor 5/10" in a for a in pf.avisos(SEGUNDA + timedelta(days=3)))
    assert pf.avisos(SEGUNDA + timedelta(days=10)) == []


# --- a tela ------------------------------------------------------------------

@pytest.fixture
def cliente(pasta):
    return TestClient(app)


def test_a_aba_abre_e_esta_no_menu(cliente):
    pagina = cliente.get("/preparacao-fisica")
    assert pagina.status_code == 200
    assert "Preparação Física" in pagina.text
    assert "Fase 0 - Recuperação" in pagina.text
    assert "Rascunho da IA" in pagina.text          # o plano nao e do edital
    assert 'href="/preparacao-fisica"' in cliente.get("/redacao").text


def test_calculadora_nao_grava(cliente):
    pagina = cliente.get("/preparacao-fisica", params={
        "barra": "5", "shuttle": "12,9", "impulsao": "2,11", "abdominal": "43", "corrida": "2501"})
    assert pagina.status_code == 200
    assert "aprovado" in pagina.text
    assert pf.ler()["testes"] == []


def test_gravar_teste_e_treino_pela_tela(cliente):
    r = cliente.post("/preparacao-fisica/teste", data={
        "data": "2027-02-01", "tipo": "simulado", "barra": "8", "abdominal": "40"},
        follow_redirects=False)
    assert r.status_code == 303
    r = cliente.post("/preparacao-fisica/treino", data={
        "data": "2027-02-01", "o_que": "costas", "minutos": "60", "esforco": "7"},
        follow_redirects=False)
    assert r.status_code == 303
    pagina = cliente.get("/preparacao-fisica").text
    assert "Teste gravado" not in pagina           # recado so com ?recado=
    assert "4,5" in pagina                           # 8 barras = 4,5 pontos


def test_treino_torto_volta_400(cliente):
    r = cliente.post("/preparacao-fisica/treino", data={
        "data": "2027-02-01", "o_que": "corrida", "minutos": "30", "esforco": "15"})
    assert r.status_code == 400
    assert "Treino não gravado" in r.text

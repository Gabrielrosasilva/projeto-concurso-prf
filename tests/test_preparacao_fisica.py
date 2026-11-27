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


# --- o treino de hoje --------------------------------------------------------

def test_treino_de_hoje_na_fase_zero_e_so_o_recado(pasta):
    treino = pf.treino_do_dia(SEGUNDA)
    assert treino.dia_da_semana == "Segunda"
    assert treino.itens == []
    assert "médico" in treino.recado


def test_treino_de_hoje_segue_a_semana_e_a_fase(pasta):
    pf.definir_situacao(SEGUNDA)
    terca = pf.treino_do_dia(SEGUNDA + timedelta(days=1))
    assert [i.chave for i in terca.itens] == ["musculacao", "barra", "abdominal"]
    assert terca.itens[0].prescricao.startswith("Costas.")
    assert "metade do seu máximo" in terca.itens[1].prescricao      # fase 1
    # Quarta: a potencia so entra na fase 3.
    quarta_fase_1 = pf.treino_do_dia(SEGUNDA + timedelta(days=2))
    assert [i.chave for i in quarta_fase_1.itens] == ["musculacao"]
    quarta_fase_3 = pf.treino_do_dia(SEGUNDA + timedelta(weeks=10, days=2))
    assert [i.chave for i in quarta_fase_3.itens] == ["potencia", "musculacao"]
    assert pf.treino_do_dia(SEGUNDA + timedelta(days=6)).descanso is True


def test_ler_series():
    assert pf.ler_series("4 4 4 3") == [4, 4, 4, 3]
    assert pf.ler_series("4,4-3") == [4, 4, 3]
    assert pf.ler_series("") == []
    with pytest.raises(ValueError):
        pf.ler_series("4 x")


# --- a evolucao --------------------------------------------------------------

def test_evolucao_junta_teste_e_treino(pasta):
    pf.registrar_teste(SEGUNDA, {"barra": 6, "corrida": 2400})
    pf.registrar_treino(SEGUNDA, "", 60, 7, itens={"barra": {"series": [7, 6, 5]}})
    pf.registrar_treino(SEGUNDA + timedelta(days=3), "", 20, 5,
                        itens={"corrida": {"distancia_m": 4000, "minutos": 20}})
    # Corrida de 10 min nao entra: o ritmo de um tiro curto engana.
    pf.registrar_treino(SEGUNDA + timedelta(days=4), "", 10, 8,
                        itens={"corrida": {"distancia_m": 2500, "minutos": 10}})
    evolucao = pf.evolucao()
    barra = evolucao["barra"]
    assert len(barra) == 1 and barra[0].valor == 7 and barra[0].origem == "treino"
    corrida = evolucao["corrida"]
    assert [p.valor for p in corrida] == [2400, 2400]       # 4 km em 20 min = 2.400 m em 12
    assert "ritmo de 5:00/km" in corrida[1].rotulo


def test_grafico_poe_a_meta_e_inverte_o_shuttle(pasta, regras):
    shuttle = _teste(regras, "shuttle")
    pontos = [pf.Ponto(SEGUNDA, 13.2, "teste", ""),
              pf.Ponto(SEGUNDA + timedelta(weeks=4), 12.4, "teste", "")]
    g = pf.grafico(pontos, shuttle, 3.5)
    # Tempo menor (melhor) fica mais ALTO no grafico (y menor no SVG).
    assert g["marcas"][1]["y"] < g["marcas"][0]["y"]
    assert [r["nome"] for r in g["referencias"]] == ["mínimo (2)", "meta (3,5)"]
    assert pf.grafico([], shuttle, 3.5) is None


# --- a tela ------------------------------------------------------------------

@pytest.fixture
def cliente(pasta):
    return TestClient(app)


def test_a_aba_abre_e_esta_no_menu(cliente):
    pagina = cliente.get("/taf")
    assert pagina.status_code == 200
    assert "Treino de hoje" in pagina.text
    assert "Fase 0 - Recuperação" in pagina.text
    assert "Rascunho da IA" in pagina.text          # o plano nao e do edital
    assert 'href="/taf">🏃 TAF' in cliente.get("/redacao").text


def test_o_endereco_antigo_leva_para_taf(cliente):
    r = cliente.get("/preparacao-fisica?barra=5", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "/taf?barra=5"


def test_calculadora_nao_grava(cliente):
    pagina = cliente.get("/taf", params={
        "barra": "5", "shuttle": "12,9", "impulsao": "2,11", "abdominal": "43", "corrida": "2501"})
    assert pagina.status_code == 200
    assert "aprovado" in pagina.text
    assert pf.ler()["testes"] == []


def test_gravar_teste_e_treino_pela_tela(cliente):
    r = cliente.post("/taf/teste", data={
        "data": "2027-02-01", "tipo": "simulado", "barra": "8", "abdominal": "40"},
        follow_redirects=False)
    assert r.status_code == 303
    r = cliente.post("/taf/treino", data={
        "data": "2027-02-01", "o_que": "costas", "minutos": "60", "esforco": "7"},
        follow_redirects=False)
    assert r.status_code == 303
    pagina = cliente.get("/taf").text
    assert "Teste gravado" not in pagina           # recado so com ?recado=
    assert "4,5" in pagina                           # 8 barras = 4,5 pontos


def test_como_foi_com_os_numeros_de_cada_exercicio(cliente):
    r = cliente.post("/taf/treino", data={
        "data": "2027-02-02", "esforco": "6", "musculacao": "1", "grupo": "Costas",
        "barra_series": "5 5 4 4", "corrida_km": "2,6", "corrida_tempo": "15:00",
        "corrida_fc": "158", "abdominal_1min": "41"}, follow_redirects=False)
    assert r.status_code == 303
    treino = pf.ler()["treinos"][0]
    assert treino["minutos"] == 15                      # sem total, vale o da corrida
    assert treino["itens"]["barra"] == {"series": [5, 5, 4, 4]}
    assert treino["itens"]["corrida"] == {"distancia_m": 2600, "minutos": 15.0, "fc_media": 158}
    assert treino["o_que"].startswith("Costas; corrida 2,60 km em 15 min; barra 5 5 4 4")
    pagina = cliente.get("/taf").text
    assert "<svg" in pagina and "02/02 · 5 (treino)" in pagina


def test_series_tortas_voltam_400(cliente):
    r = cliente.post("/taf/treino", data={"esforco": "5", "minutos": "30",
                                          "barra_series": "cinco"})
    assert r.status_code == 400
    assert "Séries inválidas" in r.text


def test_treino_torto_volta_400(cliente):
    r = cliente.post("/taf/treino", data={
        "data": "2027-02-01", "o_que": "corrida", "minutos": "30", "esforco": "15"})
    assert r.status_code == 400
    assert "Treino não gravado" in r.text

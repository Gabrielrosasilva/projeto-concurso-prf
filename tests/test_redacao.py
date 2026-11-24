"""A aba Redacao da copia PMSC (decisao PMSC-5).

A nota e do radar, pela formula do edital (item 11.5): a conta da IA nao vale.
Nenhum teste vai a API: a resposta da IA e um arquivo fixo em
tests/fixtures/redacao/, e a "API" e uma sessao falsa.
"""
import json
import shutil
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from radar import cli, config
from radar import redacao as regras
from radar.servico import manual
from radar.servico import redacao as servico_redacao
from radar.web.app import app

FIXTURES = Path(__file__).parent / "fixtures" / "redacao"
REGRAS = {"linhas_minimo": 20, "linhas_maximo": 30, "nota_maxima": 20, "nota_minima": 10}
QUARTA = date(2026, 10, 28)


@pytest.fixture
def pasta(banco_temporario, tmp_path, monkeypatch):
    """Config com o redacao.yml de teste, e os dados no tmp_path."""
    pasta_config = tmp_path / "config"
    pasta_config.mkdir()
    shutil.copy(FIXTURES / "redacao.yml", pasta_config / "redacao.yml")
    monkeypatch.setenv("RADAR_CONFIG_DIR", str(pasta_config))
    monkeypatch.delenv("RADAR_ANTHROPIC_KEY", raising=False)
    return tmp_path


@pytest.fixture
def cliente(pasta):
    return TestClient(app)


def _responder(fixture: str) -> Path:
    """A resposta fixa, com o lote do pedido que acabou de ser gravado."""
    lote = json.loads(manual.caminho_do_pedido().read_text(encoding="utf-8"))
    corpo = json.loads((FIXTURES / fixture).read_text(encoding="utf-8"))
    corpo["lote"] = lote["lote"]
    resposta = manual.caminho_do_pedido().with_name("resposta_ia.json")
    resposta.write_text(json.dumps(corpo, ensure_ascii=False), encoding="utf-8")
    return resposta


# --- a conta do edital ------------------------------------------------------

def test_a_nota_e_nc_menos_ne_sobre_tl():
    n = regras.nota(14, 6, 25, REGRAS)
    assert (n.bruta, n.desconto, n.final) == (13.76, 0.0, 13.76)
    assert n.aprovada


def test_cada_linha_abaixo_de_20_tira_0_20():
    n = regras.nota(14, 6, 18, REGRAS)
    assert n.linhas_faltando == 2
    assert n.desconto == 0.40
    assert n.final == 13.27            # 14 - 6/18 = 13,67, menos 0,40


def test_negativa_vira_zero():
    assert regras.nota(1, 30, 20, REGRAS).final == 0.0


def test_o_que_passa_de_30_linhas_nao_conta():
    n = regras.nota(14, 6, 33, REGRAS)
    assert n.tl == 30 and n.acima_do_maximo
    assert n.final == 13.8


def test_motivo_de_zero_zera_e_a_conta_fica():
    n = regras.nota(14, 6, 25, REGRAS, motivo_zero="fuga ao tema")
    assert n.final == 0.0 and n.bruta == 13.76 and n.zerada == "fuga ao tema"


def test_abaixo_de_10_nao_aprova():
    assert not regras.nota(9, 0, 25, REGRAS).aprovada


# --- o tema da vez ----------------------------------------------------------

TEMAS = [{"data": "2026-10-28", "tema": "Tema da quarta"},
         {"data": "2026-10-31", "tema": "Tema do sabado"},
         {"data": "2026-11-04", "tema": "Tema da outra quarta"}]


def test_a_faixa_do_dia_manda():
    vez = regras.tema_da_vez(QUARTA, ["Redação da semana: Tema da faixa"], TEMAS)
    assert (vez.tema, vez.origem) == ("Tema da faixa", "a faixa de Redação do dia")


def test_a_aula_de_redacao_nao_e_tema():
    vez = regras.tema_da_vez(QUARTA, ["Redação 1: o que a AOCP cobra"], TEMAS)
    assert vez.tema == "Tema da quarta"


def test_sem_faixa_vale_o_da_semana_e_depois_o_proximo():
    feitos = {"Tema da quarta", "Tema do sabado"}
    assert regras.tema_da_vez(date(2026, 10, 26), [], TEMAS).tema == "Tema da quarta"
    # quinta, com a de quarta corrigida: o proximo da semana e o de sabado
    assert regras.tema_da_vez(date(2026, 10, 29), [], TEMAS, feitos).tema == "Tema do sabado"
    # domingo, tudo corrigido: nada depois na semana, vale o ultimo dela
    assert regras.tema_da_vez(date(2026, 11, 1), [], TEMAS, feitos).tema == "Tema do sabado"
    assert regras.tema_da_vez(date(2026, 10, 1), [], TEMAS).tema == "Tema da quarta"
    assert regras.tema_da_vez(date(2026, 12, 1), [], TEMAS) is None


def test_o_tema_que_ficou_sem_correcao_vem_antes_do_proximo():
    # A terca de 03/11 mostrava o tema de quarta, e o de segunda ficou para tras.
    vez = regras.tema_da_vez(date(2026, 10, 29), [], TEMAS, set())
    assert vez.tema == "Tema da quarta"
    assert vez.origem == "o tema da semana que ficou sem correção (28/10)"
    # dois para tras: o mais recente primeiro
    assert regras.tema_da_vez(date(2026, 11, 1), [], TEMAS).tema == "Tema do sabado"
    assert regras.tema_da_vez(date(2026, 11, 1), [], TEMAS, {"Tema do sabado"}).tema \
        == "Tema da quarta"
    # o tema do dia continua mandando, mesmo ja corrigido
    assert regras.tema_da_vez(date(2026, 11, 4), [], TEMAS,
                              {"Tema da outra quarta"}).tema == "Tema da outra quarta"


def test_a_aba_mostra_o_tema_que_ficou_para_tras(pasta):
    # Fixture: 28/10 e 04/11 tem tema; a quinta 05/11 nao tem.
    vez = servico_redacao.tema_da_vez(date(2026, 11, 5))
    assert vez.origem == "o tema da semana que ficou sem correção (04/11)"
    servico_redacao.gravar({"redacoes": [{
        "id": "x", "data": "2026-11-04",
        "tema": "Segurança pública: dever do Estado, direito e responsabilidade de todos"}]})
    # corrigida, a quinta segue no ultimo da semana, como antes
    assert servico_redacao.tema_da_vez(date(2026, 11, 5)).origem == "o tema da semana (04/11)"


# --- a forma do que a IA devolve --------------------------------------------

def _correcao_da_fixture() -> dict:
    corpo = json.loads((FIXTURES / "resposta_correcao.json").read_text(encoding="utf-8"))
    return corpo["respostas"][0]["correcao"]


def test_a_correcao_sem_nota_de_conteudo_e_recusada():
    item = _correcao_da_fixture()
    del item["nota_conteudo"]
    with pytest.raises(regras.RespostaInvalida):
        regras.conferir_correcao(item, REGRAS)


def test_nota_de_conteudo_fora_de_0_a_20_e_recusada():
    item = _correcao_da_fixture()
    item["nota_conteudo"] = 25
    with pytest.raises(regras.RespostaInvalida):
        regras.conferir_correcao(item, REGRAS)


def test_erro_sem_trecho_e_descartado_e_contado():
    correcao = regras.conferir_correcao(_correcao_da_fixture(), REGRAS)
    assert len(correcao.erros) == 6
    assert len(correcao.descartados) == 1
    assert len(correcao.tres_pontos) == 3


def test_ideias_sem_tese_sao_recusadas():
    with pytest.raises(regras.RespostaInvalida):
        regras.conferir_ideias({"teses": [{"tese": ""}]})


# --- o caminho sem API ------------------------------------------------------

def test_correcao_sem_api_grava_a_nota_do_radar(pasta):
    servico_redacao.escrever_pedido(servico_redacao.TIPO_CORRECAO, "Tema X", QUARTA,
                                    "Um texto qualquer.", 25)
    lote = json.loads(manual.caminho_do_pedido().read_text(encoding="utf-8"))
    assert lote["tipo"] == "redacao_correcao"
    assert lote["pedidos"][0]["texto"] == "Um texto qualquer."
    assert "REPERTÓRIO" in lote["como_responder"]

    resultado = manual.importar(_responder("resposta_correcao.json"))
    assert resultado["gravadas"] == 1
    assert resultado["modelo"].startswith("Claude Code (claude-opus-5-5)")

    salvo = servico_redacao.historico()[0]
    # A IA disse 19,5; a conta do edital da 14 - 6/25 = 13,76.
    assert salvo["nota"]["final"] == 13.76
    assert salvo["nota_final_da_ia"] == 19.5
    assert salvo["nota"]["ne"] == 6
    assert salvo["procedencia"] == resultado["modelo"]
    dados = json.loads((pasta / "redacoes.json").read_text(encoding="utf-8"))
    assert len(dados["redacoes"]) == 1


def test_ideias_sem_api(pasta):
    servico_redacao.escrever_pedido(servico_redacao.TIPO_IDEIAS, "Tema X", QUARTA)
    resultado = manual.importar(_responder("resposta_ideias.json"))
    assert resultado["gravadas"] == 1
    ideias = servico_redacao.ultimas_ideias("Tema X")
    assert len(ideias["teses"]) == 1                    # a tese vazia saiu
    assert len(ideias["teses"][0]["argumentos"]) == 1   # e o argumento vazio
    assert ideias["proposta"]["agente"] == "o Estado"


def test_pedido_sem_linhas_nao_e_gravado(pasta):
    with pytest.raises(ValueError):
        servico_redacao.escrever_pedido(servico_redacao.TIPO_CORRECAO, "Tema", QUARTA, "texto", None)
    assert not manual.caminho_do_pedido().exists()


# --- com API, com resposta fixa ---------------------------------------------

class _SessaoFalsa:
    """A API de mentira: devolve a correcao da fixture, sem rede."""

    def __init__(self, item):
        self.item = item
        self.enviado = None

    def post(self, url, headers=None, json=None, timeout=None):  # noqa: A002
        self.enviado = json
        texto = __import__("json").dumps(self.item, ensure_ascii=False)

        class _Resposta:
            def raise_for_status(self):
                return None

            def json(self):
                return {"content": [{"type": "text", "text": texto}],
                        "usage": {"input_tokens": 1000, "output_tokens": 2000}}
        return _Resposta()


def test_correcao_pela_api_com_resposta_fixa(pasta, monkeypatch):
    monkeypatch.setattr(config, "chave_da_anthropic", lambda: "chave-de-teste")
    sessao = _SessaoFalsa(_correcao_da_fixture())
    registro = servico_redacao.corrigir_pela_api("Um texto.", 25, "Tema X", QUARTA, sessao=sessao)
    assert registro["nota"]["final"] == 13.76
    assert "pela API" in registro["procedencia"]
    assert "LINHAS ESCRITAS NA FOLHA: 25" in sessao.enviado["messages"][0]["content"]


def test_sem_chave_a_api_nao_e_chamada(pasta):
    with pytest.raises(ValueError):
        servico_redacao.corrigir_pela_api("texto", 25, "Tema", QUARTA, sessao=_SessaoFalsa({}))


def test_o_custo_estimado_e_positivo(pasta):
    entrada, saida, custo = servico_redacao.estimar(servico_redacao.TIPO_CORRECAO, "x" * 3500)
    assert entrada > 1000 and saida > 0 and custo > 0


# --- a tela -----------------------------------------------------------------

def test_a_aba_abre_com_o_metodo_e_o_tema(cliente):
    texto = cliente.get("/redacao?data=2026-10-28").text
    assert "<title>PRF &middot; Redação" in texto
    assert "MODO PRF" in texto
    assert 'class="item ativo" href="/redacao"' in texto
    assert "O papel da Polícia Militar na preservação da ordem pública" in texto
    for parte in ("Roteiro de ideias", "O esqueleto de 4 parágrafos", "Conectivos",
                  "Os erros que mais tiram ponto", "Repertório", "Regras do edital",
                  "NC − NE ÷ TL"):
        assert parte in texto


def test_sem_o_yml_a_aba_diz_o_que_falta(banco_temporario, tmp_path, monkeypatch):
    monkeypatch.setenv("RADAR_CONFIG_DIR", str(tmp_path))
    texto = TestClient(app).get("/redacao").text
    assert "Falta o arquivo" in texto


def test_corrigir_sem_api_grava_o_pedido(cliente):
    resposta = cliente.post("/redacao/corrigir", data={
        "texto": "Meu texto.", "linhas": "24", "tema": "Tema X", "data": "2026-10-28"},
        follow_redirects=False)
    assert resposta.status_code == 303
    assert "recado=pedido_correcao" in resposta.headers["location"]
    lote = json.loads(manual.caminho_do_pedido().read_text(encoding="utf-8"))
    assert lote["pedidos"][0]["linhas"] == 24

    pagina = cliente.get(resposta.headers["location"]).text
    assert "resposta_ia.json" in pagina


def test_sem_linhas_o_texto_volta_no_campo(cliente):
    resposta = cliente.post("/redacao/corrigir", data={
        "texto": "Texto que nao pode se perder.", "linhas": "", "tema": "Tema X"})
    assert resposta.status_code == 400
    assert "Texto que nao pode se perder." in resposta.text


def test_a_redacao_corrigida_mostra_a_conta(cliente):
    servico_redacao.escrever_pedido(servico_redacao.TIPO_CORRECAO, "Tema X", QUARTA, "Texto.", 25)
    manual.importar(_responder("resposta_correcao.json"))
    salvo = servico_redacao.historico()[0]

    texto = cliente.get(f"/redacao/{salvo['id']}").text
    assert "13,76" in texto
    assert "A IA tinha calculado 19,50" in texto
    assert "haviam muitos problemas" in texto
    assert "ds-selo--ia" in texto
    assert cliente.get("/redacao/nao-existe").status_code == 404

    aba = cliente.get("/redacao").text
    assert f'/redacao/{salvo["id"]}' in aba


def test_a_faixa_de_redacao_da_hoje_leva_a_aba(banco_temporario, monkeypatch):
    """Com o cronograma da copia PMSC: a quarta 28/10 tem a redacao da semana."""
    monkeypatch.setenv("RADAR_CONFIG_DIR", str(config.RAIZ / "pmsc" / "config"))
    texto = TestClient(app).get("/hoje?data=2026-10-28").text
    assert "Abrir na aba Redação" in texto
    assert 'href="/redacao?data=2026-10-28"' in texto


# --- a CLI e o sincronizar --------------------------------------------------

def test_o_sincronizar_leva_as_redacoes():
    assert "data/redacoes.json" in cli.ARQUIVOS_DO_RADAR


def test_cli_grava_o_pedido_de_correcao(pasta):
    texto = pasta / "minha_redacao.txt"
    texto.write_text("Minha redação de quarta.", encoding="utf-8")
    resultado = CliRunner().invoke(cli.app, [
        "redacao", "--pedido", str(texto), "--linhas", "24", "--data", "2026-10-28"],
        env={"COLUMNS": "200"})
    assert resultado.exit_code == 0, resultado.output
    lote = json.loads(manual.caminho_do_pedido().read_text(encoding="utf-8"))
    assert lote["pedidos"][0]["tema"] == "O papel da Polícia Militar na preservação da ordem pública"
    assert "resposta_ia.json" in resultado.output


def test_cli_importa_a_correcao(pasta):
    servico_redacao.escrever_pedido(servico_redacao.TIPO_CORRECAO, "Tema X", QUARTA, "Texto.", 25)
    resposta = _responder("resposta_correcao.json")
    resultado = CliRunner().invoke(cli.app, ["redacao", "--importar", str(resposta)],
                                   env={"COLUMNS": "200"})
    assert resultado.exit_code == 0, resultado.output
    assert "13.76" in resultado.output


# --- os textos motivadores e a correcao didatica (decisao PMSC-22) ----------

def _avaliacao(melhorou="em parte", comentario="Fixture: o exemplo ficou concreto."):
    """A resposta da reescrita, com o lote do pedido gravado."""
    lote = json.loads(manual.caminho_do_pedido().read_text(encoding="utf-8"))
    corpo = {"lote": lote["lote"], "modelo": "claude-opus-5-5",
             "respostas": [{"id": "r1", "avaliacao": {
                 "melhorou": melhorou, "comentario": comentario,
                 "o_que_ainda_falta": "Fixture: ligar o fecho à tese.",
                 "erros": [{"trecho": "a policia", "correcao": "a polícia", "regra": "acento"}]}}]}
    resposta = manual.caminho_do_pedido().with_name("resposta_ia.json")
    resposta.write_text(json.dumps(corpo, ensure_ascii=False), encoding="utf-8")
    return resposta


def test_o_tema_da_vez_traz_os_textos_com_fonte(pasta):
    vez = servico_redacao.tema_da_vez(QUARTA)
    assert [x["fonte"] for x in vez.textos] == ["CF, art. 144, § 5º", "Lei 14.751/2023, art. 3º"]
    assert all(x["url"].startswith("https://") for x in vez.textos)
    assert {x["tipo"] for x in vez.textos} == {"lei"}
    # O tema sem textos continua valendo, so sem eles; e sem comando, a frase generica.
    assert regras.textos_do_tema("Outro tema", []) == []
    assert vez.comando == ""


# --- a proposta do jeito da AOCP: a noticia e o comando (decisao PMSC-23) --

def test_a_noticia_entra_com_fonte_e_titulo_e_o_comando_vem_junto(pasta):
    vez = servico_redacao.tema_da_vez(date(2026, 11, 4))
    assert [(x["tipo"], x["fonte"]) for x in vez.textos] == [
        ("noticia", "Agência Fixture, 01/01/2026"), ("lei", "CF, art. 144")]
    assert vez.textos[0]["titulo"] == "Fixture: o título da notícia"
    assert vez.comando.startswith("Fixture de teste: redija um texto DISSERTATIVO")


def test_a_aba_mostra_o_comando_da_aocp_no_lugar_da_frase_generica(cliente):
    texto = cliente.get("/redacao?data=2026-11-04").text
    assert "Fixture: o título da notícia" in texto and "Agência Fixture, 01/01/2026" in texto
    assert "A SEGURANÇA É SÓ DO ESTADO OU DE TODOS?" in texto
    assert "A partir da leitura dos textos motivadores" not in texto
    assert "Este nao aparece" not in texto


def test_o_pedido_de_correcao_leva_o_comando(pasta):
    servico_redacao.escrever_pedido(servico_redacao.TIPO_CORRECAO,
                                    "Segurança pública: dever do Estado, direito e responsabilidade de todos",
                                    date(2026, 11, 4), "Texto.", 25)
    pedido = json.loads(manual.caminho_do_pedido().read_text(encoding="utf-8"))["pedidos"][0]
    assert "OU DE TODOS?" in pedido["comando"]
    assert [x["tipo"] for x in pedido["textos_motivadores"]] == ["noticia", "lei"]


def test_a_aba_mostra_os_textos_como_no_caderno(cliente):
    texto = cliente.get("/redacao?data=2026-10-28").text
    assert "TEXTO 1" in texto and "TEXTO 2" in texto and "TEXTO 3" not in texto
    assert "Adaptado de:" in texto and "Acesso em: 25 out. 2026" in texto
    assert "A partir da leitura dos textos motivadores" in texto
    assert "Este nao aparece" not in texto
    assert "corrige a redação" in texto


def test_o_pedido_leva_os_textos_e_a_origem(pasta):
    servico_redacao.escrever_pedido(servico_redacao.TIPO_CORRECAO,
                                    "O papel da Polícia Militar na preservação da ordem pública",
                                    QUARTA, "Texto.", 25, "foto")
    lote = json.loads(manual.caminho_do_pedido().read_text(encoding="utf-8"))
    pedido = lote["pedidos"][0]
    assert pedido["origem"] == "foto"
    assert len(pedido["textos_motivadores"]) == 2
    assert "LEGIBILIDADE" in lote["como_responder"] and "MELHORIAS" in lote["como_responder"]


def test_a_correcao_didatica_e_conferida_e_gravada(pasta):
    servico_redacao.escrever_pedido(servico_redacao.TIPO_CORRECAO, "Tema X", QUARTA, "Texto.", 25)
    manual.importar(_responder("resposta_correcao.json"))
    salvo = servico_redacao.historico()[0]

    assert salvo["criterios"][0]["positivos"] == ["Fixture: o tema foi atendido desde a introdução."]
    assert salvo["criterios"][1]["negativos"] == []
    assert [e["tipo"] for e in salvo["erros"][:4]] == ["concordância", "pontuação", "outro", ""]
    assert salvo["erros"][0]["explicacao"].startswith("Fixture")
    # A melhoria sem o original e o positivo vazio saem; os focos param em 3.
    assert len(salvo["melhorias"]) == 1
    assert salvo["pontos_positivos"] == ["Fixture: os quatro parágrafos estão no lugar."]
    assert len(salvo["focos"]) == 3
    assert salvo["legibilidade"]["avaliacao"] == "legível"
    assert salvo["origem"] == "digitado" and salvo["reescritas"] == []
    # A nota continua a do edital: as melhorias nao entram no NE.
    assert salvo["nota"]["ne"] == 6 and salvo["nota"]["final"] == 13.76


def test_o_texto_anotado_marca_cada_erro_no_lugar():
    pedacos = regras.texto_anotado("eles tem e haviam muitos problemas.",
                                   [{"trecho": "haviam muitos problemas"}, {"trecho": "eles tem"},
                                    {"trecho": "nao esta no texto"}])
    assert pedacos == [("eles tem", 2), (" e ", None), ("haviam muitos problemas", 1), (".", None)]
    assert regras.texto_anotado("", [{"trecho": "x"}]) == []


def test_a_reescrita_vai_para_a_redacao_de_origem(pasta):
    servico_redacao.escrever_pedido(servico_redacao.TIPO_CORRECAO, "Tema X", QUARTA, "Texto.", 25)
    manual.importar(_responder("resposta_correcao.json"))
    salvo = servico_redacao.historico()[0]

    servico_redacao.escrever_pedido_de_reescrita(salvo["id"], "Meu parágrafo novo, à mão.")
    lote = json.loads(manual.caminho_do_pedido().read_text(encoding="utf-8"))
    assert lote["tipo"] == "redacao_reescrita"
    assert lote["pedidos"][0]["paragrafo_reescrito_pelo_corretor"].startswith("Fixture")
    resultado = manual.importar(_avaliacao())
    assert resultado["gravadas"] == 1

    reescrita = servico_redacao.achar(salvo["id"])["reescritas"][0]
    assert reescrita["melhorou"] == "em parte" and reescrita["texto"] == "Meu parágrafo novo, à mão."
    assert reescrita["erros"][0]["correcao"] == "a polícia"

    servico_redacao.escrever_pedido_de_reescrita(salvo["id"], "De novo.")
    assert manual.importar(_avaliacao(melhorou="talvez"))["gravadas"] == 0
    with pytest.raises(ValueError):
        servico_redacao.escrever_pedido_de_reescrita("nao-existe", "x")


def test_a_redacao_corrigida_e_didatica(cliente):
    servico_redacao.escrever_pedido(servico_redacao.TIPO_CORRECAO, "Tema X", QUARTA,
                                    "eles tem e haviam muitos problemas.", 25)
    manual.importar(_responder("resposta_correcao.json"))
    salvo = servico_redacao.historico()[0]
    servico_redacao.escrever_pedido_de_reescrita(salvo["id"], "Meu parágrafo novo.")
    manual.importar(_avaliacao())

    texto = cliente.get(f"/redacao/{salvo['id']}").text
    for parte in ("O que está bom", "O que mais tirou nota", "Por critério",
                  "O seu texto, com os erros marcados", "<mark>haviam muitos problemas<sup>1</sup></mark>",
                  "Você escreveu → como fica melhor", "a polícia ostensiva previne o crime",
                  "Sua vez:", "melhorou em parte", "Para a próxima redação", "Letra:</b> legível"):
        assert parte in texto, parte


def test_cli_foto_e_reescrita(pasta):
    texto = pasta / "transcrita.txt"
    texto.write_text("Redação transcrita da foto.", encoding="utf-8")
    resultado = CliRunner().invoke(cli.app, [
        "redacao", "--pedido", str(texto), "--linhas", "23", "--data", "2026-10-28", "--foto"],
        env={"COLUMNS": "200"})
    assert resultado.exit_code == 0, resultado.output
    lote = json.loads(manual.caminho_do_pedido().read_text(encoding="utf-8"))
    assert lote["pedidos"][0]["origem"] == "foto"
    manual.importar(_responder("resposta_correcao.json"))
    salvo = servico_redacao.historico()[0]

    paragrafo = pasta / "paragrafo.txt"
    paragrafo.write_text("O parágrafo reescrito.", encoding="utf-8")
    resultado = CliRunner().invoke(cli.app, [
        "redacao", "--reescrita", salvo["id"], "--pedido", str(paragrafo)], env={"COLUMNS": "200"})
    assert resultado.exit_code == 0, resultado.output
    assert json.loads(manual.caminho_do_pedido().read_text(encoding="utf-8"))["tipo"] == "redacao_reescrita"
    resultado = CliRunner().invoke(cli.app, ["redacao", "--importar", str(_avaliacao())],
                                   env={"COLUMNS": "200"})
    assert resultado.exit_code == 0 and "avaliação" in resultado.output


# --- a redacao-modelo (decisao PMSC-24) -------------------------------------

RAIZ = Path(__file__).resolve().parent.parent


def test_o_modelo_so_aparece_na_correcao_e_nunca_na_proposta(pasta, cliente):
    tema = "O papel da Polícia Militar na preservação da ordem pública"
    (pasta / "redacoes_modelo.json").write_text(json.dumps({
        "procedencia": "Fixture (claude-opus-5-5), 26/10/2026",
        "modelos": [{"tema": tema, "texto": "Fixture: o primeiro paragrafo.\n\nFixture: o segundo.",
                     "pontos": ["Fixture: a tese no fim da introdução."]}]},
        ensure_ascii=False), encoding="utf-8")
    servico_redacao.escrever_pedido(servico_redacao.TIPO_CORRECAO, tema, QUARTA, "Texto.", 25)
    manual.importar(_responder("resposta_correcao.json"))
    salvo = servico_redacao.historico()[0]

    corrigida = cliente.get(f"/redacao/{salvo['id']}").text
    assert "A redação-modelo deste tema" in corrigida
    assert "Fixture: o segundo." in corrigida and "Fixture: a tese no fim" in corrigida
    # Antes de escrever, nada do modelo: ver o modelo antes ensina a copiar.
    assert "Fixture: o segundo." not in cliente.get("/redacao?data=2026-10-28").text
    # Tema sem modelo: a secao some.
    assert servico_redacao.modelo_do_tema("Outro tema") is None


def test_numero_sem_fonte_e_achado():
    fontes = ["Em 2025, foram 6.044 mortes.", "CF, art. 144, § 5º"]
    assert regras.numeros_sem_fonte("Foram 6.044 mortes em 2025 (art. 144, § 5º) e 1988.", fontes) == []
    assert regras.numeros_sem_fonte("Cerca de 40 mil mortes por ano.", fontes) == ["40"]


def test_os_modelos_reais_cobrem_os_temas_e_nao_inventam_numero():
    """Le o data/redacoes_modelo.json e o pmsc/config/redacao.yml reais."""
    dados = json.loads((RAIZ / "data" / "redacoes_modelo.json").read_text(encoding="utf-8"))
    import yaml
    config_pmsc = yaml.safe_load((RAIZ / "pmsc" / "config" / "redacao.yml").read_text(encoding="utf-8"))
    temas = {t["tema"]: t for t in config_pmsc["temas"]}
    assert "claude-opus-5-5" in dados["procedencia"]
    assert {m["tema"] for m in dados["modelos"]} == set(temas)
    for modelo in dados["modelos"]:
        paragrafos = [p for p in modelo["texto"].split("\n\n") if p.strip()]
        palavras = len(modelo["texto"].split())
        assert len(paragrafos) == 4, modelo["tema"]
        # 20 a 30 linhas a mao: umas 220 a 330 palavras.
        assert 220 <= palavras <= 330, (modelo["tema"], palavras)
        assert len(modelo["pontos"]) >= 3, modelo["tema"]
        fontes = regras.fontes_do_tema(temas[modelo["tema"]], config_pmsc["repertorio"])
        assert regras.numeros_sem_fonte(modelo["texto"], fontes) == [], modelo["tema"]

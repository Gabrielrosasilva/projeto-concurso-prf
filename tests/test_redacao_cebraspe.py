"""A aba Redacao no criterio do Cebraspe (PRF-37).

O que estes testes seguram:
  - a conta e NPD = NC - 4 x NE / TL (edital 2021, 10.6.4), sem minimo de linhas;
  - a NC sai dos conceitos (0 a 3) dos quesitos, e conceito fora da escala e recusado;
  - o pedido de correcao leva os quesitos do tema e o formato por conceitos;
  - a tela da aba e a da correcao mostram a regra do Cebraspe;
  - os textos motivadores do PRF/config/redacao.yml sao literais da lei (so onde
    as copias locais da lei existem: elas ficam fora do git).

Le o PRF/config/redacao.yml versionado; os dados vao para o tmp_path. Nada de
internet nem do dia de hoje.
"""
import json
import re
import shutil
from datetime import date

import pytest
import yaml
from fastapi.testclient import TestClient

from radar import config
from radar import redacao as regras
from radar.servico import manual
from radar.servico import redacao as servico_redacao
from radar.web.app import app

CONFIG_PRF = config.RAIZ / "PRF" / "config"
CEBRASPE = {"linhas_minimo": 0, "linhas_maximo": 30, "nota_maxima": 20, "nota_minima": 10,
            "fator_dos_erros": 4, "conceito_maximo": 3}
SABADO = date(2027, 1, 9)
TEMA = "As infrações de trânsito nas rodovias federais: o papel da PRF, da sociedade e do indivíduo"


def _correcao(*conceitos, **extra) -> dict:
    return {"criterios": [{"criterio": f"2.{i} Aspecto {i}", "nota": c, "comentario": "porque sim"}
                          for i, c in enumerate(conceitos, start=1)],
            "erros": [{"trecho": "haviam", "correcao": "havia", "regra": "haver impessoal",
                       "tipo": "concordância"}],
            "apresentacao": {"comentario": "Cinco parágrafos.", "problemas": ["Conclusão curta."]},
            **extra}


@pytest.fixture
def prf(banco_temporario, tmp_path, monkeypatch):
    """O redacao.yml e o cronograma da PRF, com os dados numa copia no tmp_path
    (o cronograma aponta para a arvore da PRF)."""
    for arquivo in (config.RAIZ / "data").glob("*.json"):
        shutil.copy2(arquivo, tmp_path / arquivo.name)
    (tmp_path / "redacoes.json").unlink(missing_ok=True)
    monkeypatch.setenv("RADAR_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("RADAR_CONFIG_DIR", str(CONFIG_PRF))
    monkeypatch.delenv("RADAR_ANTHROPIC_KEY", raising=False)
    return tmp_path


# --- a conta -----------------------------------------------------------------

def test_cada_erro_vale_4_sobre_as_linhas():
    n = regras.nota(15, 6, 30, CEBRASPE)
    assert (n.fator, n.bruta, n.final) == (4.0, 14.2, 14.2)    # 15 - 4 x 6 / 30


def test_sem_minimo_de_linhas_nao_ha_desconto():
    n = regras.nota(15, 3, 12, CEBRASPE)
    assert (n.linhas_faltando, n.desconto, n.final) == (0, 0.0, 14.0)


def test_abaixo_de_10_elimina_e_negativa_vira_zero():
    assert not regras.nota(11, 9, 20, CEBRASPE).aprovada          # 11 - 1,8 = 9,2
    assert regras.nota(2, 30, 20, CEBRASPE).final == 0.0


# --- os conceitos --------------------------------------------------------------

def test_a_nc_sai_dos_conceitos_e_a_da_ia_nao_vale():
    c = regras.conferir_correcao(_correcao(3, 2, 1, nota_conteudo=19), CEBRASPE)
    assert c.por_conceitos and c.nota_conteudo == 13.33           # 20 x 6 / 9
    assert c.apresentacao == {"comentario": "Cinco parágrafos.", "problemas": ["Conclusão curta."]}


@pytest.mark.parametrize("conceito", [4, 2.5, -1])
def test_conceito_fora_da_escala_e_recusado(conceito):
    with pytest.raises(regras.RespostaInvalida, match="inteiro de 0 a 3"):
        regras.conferir_correcao(_correcao(3, conceito, 1), CEBRASPE)


def test_na_aocp_continua_valendo_a_nota_de_conteudo():
    aocp = {k: v for k, v in CEBRASPE.items() if k not in ("fator_dos_erros", "conceito_maximo")}
    c = regras.conferir_correcao(_correcao(3, 2, nota_conteudo=14.5), aocp)
    assert not c.por_conceitos and c.nota_conteudo == 14.5


# --- o pedido e as telas -------------------------------------------------------

def test_o_pedido_leva_os_quesitos_e_o_formato_por_conceitos(prf):
    lote = servico_redacao.montar_lote(servico_redacao.TIPO_CORRECAO, TEMA, SABADO,
                                       "Meu texto.", 28)
    pedido = lote["pedidos"][0]
    assert len(pedido["quesitos"]) == 3 and pedido["quesitos"][0].startswith("2.1")
    assert len(pedido["textos_motivadores"]) == 1      # um, como na prova (PRF-67)
    formato = lote["formato_da_resposta"]["respostas"][0]["correcao"]
    assert "nota_conteudo" not in formato and "apresentacao" in formato
    assert "examinador do Cebraspe" in lote["como_responder"]


def test_a_aba_mostra_a_regra_do_cebraspe(prf):
    texto = TestClient(app).get("/redacao?data=2027-01-09").text
    assert "NC − 4 × NE ÷ TL" in texto and "até 30 linhas" in texto
    assert "medidas que a Polícia Rodoviária Federal adota" in texto      # o comando do tema
    assert "O esqueleto de 5 parágrafos" in texto
    assert "AOCP" not in texto and "PMSC" not in texto


def test_a_correcao_importada_mostra_os_conceitos_e_o_fator(prf):
    servico_redacao.escrever_pedido(servico_redacao.TIPO_CORRECAO, TEMA, SABADO,
                                    "Haviam muitas infrações.", 28)
    lote = json.loads(manual.caminho_do_pedido().read_text(encoding="utf-8"))
    resposta = manual.caminho_do_pedido().with_name("resposta_ia.json")
    resposta.write_text(json.dumps({"lote": lote["lote"], "modelo": "claude-opus-5-5",
                                    "respostas": [{"id": "r1", "correcao": _correcao(3, 2, 2)}]},
                                   ensure_ascii=False), encoding="utf-8")
    manual.importar(resposta)

    salvo = servico_redacao.historico()[0]
    assert salvo["nota"]["fator"] == 4.0 and salvo["nota_conteudo"] == 15.56   # 20 x 7 / 9
    assert salvo["nota"]["final"] == 15.42                                       # 15,56 - 4 x 1 / 28
    pagina = TestClient(app).get(f"/redacao/{salvo['id']}").text
    assert "4 × NE 1 ÷ TL 28" in pagina and "Por quesito" in pagina and "de 3" in pagina
    assert "Apresentação e estrutura textual" in pagina and "AOCP" not in pagina


# --- os textos motivadores sao literais ----------------------------------------

def _texto_da_lei(arquivo):
    corpo = arquivo.read_bytes()
    html = corpo.decode("latin-1") if corpo.count(b"\xc3") < 50 else corpo.decode("utf-8", "replace")
    texto = re.sub(r"<[^>]+>", " ", html).replace("\xa0", " ")
    # As notas da compilacao ("(Redação dada pela Lei...)") saem: nao sao da lei.
    texto = re.sub(r"\([^()]*(redação|Redação|acrescid|Acrescid|Vide|Inciso|Parágrafo|Caput|“Caput”|"
                   r"Pena|Infração|Penalidade|Medida)[^()]*\)", " ", texto)
    return re.sub(r"\s+", " ", texto)


def test_os_textos_motivadores_sao_literais_da_lei():
    leis = {"CF": config.RAIZ / "fontes" / "leis" / "cf-1988-camara.html",
            "CTB": config.RAIZ / "fontes" / "leis" / "ctb-lei-9503-1997-camara.html"}
    if not all(arquivo.exists() for arquivo in leis.values()):
        pytest.skip("as cópias locais da lei (fontes/leis/) ficam fora do git")
    textos = {nome: _texto_da_lei(arquivo) for nome, arquivo in leis.items()}
    dados = yaml.safe_load((CONFIG_PRF / "redacao.yml").read_text(encoding="utf-8"))
    for tema in dados["temas"]:
        for x in tema["textos"]:
            lei = textos["CF"] if x["lei"].startswith("CF") else textos["CTB"]
            for pedaco in (p.strip(" ;") for p in x["texto"].split("[...]")):
                if pedaco:
                    assert " ".join(pedaco.split()) in lei, (x["lei"], pedaco[:80])

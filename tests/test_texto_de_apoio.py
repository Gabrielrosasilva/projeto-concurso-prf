"""O texto de apoio da redacao (PRF-67).

O que estes testes seguram:
  - a aba mostra o texto de apoio do tema na proposta e, com ele, tira o
    "Me da ideias" (tema sem texto continua com o botao);
  - o pedido de correcao leva o texto de apoio (o corretor ve a copia);
  - no data/textos_de_apoio.json real: o tema existe no redacao.yml, nada de
    numero sem fonte, a lei citada e literal da copia da Camara (so onde a
    copia existe: leis/ fica fora do git) e a variedade: nenhuma abertura pela
    lei, nenhuma abertura repetida, nenhum dispositivo em mais de 3 textos.

Le o PRF/config/redacao.yml versionado; os dados vao para o tmp_path. Nada de
internet nem do dia de hoje.
"""
import json
import re
import shutil
from collections import Counter
from datetime import date

import pytest
import yaml
from fastapi.testclient import TestClient

from radar import config, textos_de_lei
from radar import redacao as regras
from radar.servico import redacao as servico_redacao
from radar.web.app import app

CONFIG_PRF = config.RAIZ / "PRF" / "config"
ARQUIVO = config.RAIZ / "data" / "textos_de_apoio.json"
TEMA = "As infrações de trânsito nas rodovias federais: o papel da PRF, da sociedade e do indivíduo"
SABADO = date(2027, 1, 9)
#: O tema de 16/01, que ainda nao tem texto de apoio no piloto.
SEM_APOIO = "2027-01-16"


@pytest.fixture
def prf(banco_temporario, tmp_path, monkeypatch):
    for arquivo in (config.RAIZ / "data").glob("*.json"):
        shutil.copy2(arquivo, tmp_path / arquivo.name)
    (tmp_path / "redacoes.json").unlink(missing_ok=True)
    monkeypatch.setenv("RADAR_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("RADAR_CONFIG_DIR", str(CONFIG_PRF))
    monkeypatch.delenv("RADAR_ANTHROPIC_KEY", raising=False)
    return tmp_path


def _apoio_de_teste(tema: str) -> dict:
    return {"procedencia": "Fixture.",
            "textos": [{"tema": tema, "contexto": "Fixture: o contexto.",
                        "caminhos": [{"titulo": "Fixture: caminho", "quesito": "2.1",
                                      "texto": "Fixture: o caminho."}],
                        "o_que_saber": ["Fixture: saber."], "situacoes": ["Fixture: situação."],
                        "base_legal": [], "fecho": "Fixture: o fecho."}]}


# --- a tela e o pedido ---------------------------------------------------------

def test_a_proposta_mostra_o_texto_de_apoio_e_tira_o_me_da_ideias(prf):
    (prf / "textos_de_apoio.json").write_text(
        json.dumps(_apoio_de_teste(TEMA), ensure_ascii=False), encoding="utf-8")
    cliente = TestClient(app)
    com = cliente.get("/redacao?data=2027-01-09").text
    assert "Texto de apoio" in com and "Fixture: o caminho." in com and "Fixture: o fecho." in com
    assert "Me dá ideias" not in com
    sem = cliente.get(f"/redacao?data={SEM_APOIO}").text
    assert "Fixture: o caminho." not in sem and "Me dá ideias" in sem


def test_o_pedido_de_correcao_leva_o_texto_de_apoio(prf):
    (prf / "textos_de_apoio.json").write_text(
        json.dumps(_apoio_de_teste(TEMA), ensure_ascii=False), encoding="utf-8")
    lote = servico_redacao.montar_lote(servico_redacao.TIPO_CORRECAO, TEMA, SABADO,
                                       "Meu texto.", 28)
    pedido = lote["pedidos"][0]
    assert "Fixture: o caminho." in pedido["texto_de_apoio"]
    assert "TEXTO DE APOIO" in lote["como_responder"]


def test_sem_arquivo_nao_ha_texto_de_apoio(prf):
    (prf / "textos_de_apoio.json").unlink(missing_ok=True)
    assert servico_redacao.texto_de_apoio_do_tema(TEMA) is None
    assert "texto_de_apoio" not in servico_redacao.montar_lote(
        servico_redacao.TIPO_CORRECAO, TEMA, SABADO, "Meu texto.", 28)["pedidos"][0]


# --- o arquivo real ------------------------------------------------------------

def _reais():
    dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
    redacao = yaml.safe_load((CONFIG_PRF / "redacao.yml").read_text(encoding="utf-8"))
    temas = {t["tema"]: t for t in redacao["temas"]}
    return dados, temas, redacao.get("repertorio") or []


def test_os_textos_reais_tem_procedencia_tema_e_todas_as_partes():
    dados, temas, _ = _reais()
    assert "claude-opus-5-5" in dados["procedencia"]
    for apoio in dados["textos"]:
        assert apoio["tema"] in temas, apoio["tema"]
        assert apoio["contexto"].strip() and apoio["fecho"].strip()
        assert len(apoio["caminhos"]) >= 4 and apoio["o_que_saber"] and apoio["situacoes"]
        # Cada aspecto do comando tem ao menos um caminho.
        numeros = {q.split()[0] for q in temas[apoio["tema"]]["quesitos"]}
        assert numeros <= {c["quesito"] for c in apoio["caminhos"]}, apoio["tema"]


def test_os_textos_reais_nao_inventam_numero():
    """Sem estatistica: numero so o que esta no tema, no comando, no texto
    motivador, no repertorio ou na lei citada (as mesmas fontes do modelo)."""
    dados, temas, repertorio = _reais()
    for apoio in dados["textos"]:
        fontes = regras.fontes_do_tema(temas[apoio["tema"]], repertorio)
        fontes += [f"{b['lei']} {b['trecho']}" for b in apoio["base_legal"]]
        texto = servico_redacao.texto_de_apoio_corrido({**apoio, "base_legal": []})
        assert regras.numeros_sem_fonte(texto, fontes) == [], apoio["tema"]


def test_a_lei_citada_e_literal_da_copia_da_camara():
    dados, _, _ = _reais()
    citacoes = [b for apoio in dados["textos"] for b in apoio["base_legal"]]
    for b in citacoes:
        assert b["url"].startswith("https://") and b["por_que"].strip(), b["lei"]
    copias = {b["arquivo"]: config.RAIZ / "leis" / b["arquivo"] for b in citacoes}
    if not all(caminho.exists() for caminho in copias.values()):
        pytest.skip("as cópias locais da lei (leis/) ficam fora do git")
    texto = {nome: " ".join(textos_de_lei.texto_do_arquivo(caminho).split())
             for nome, caminho in copias.items()}
    for b in citacoes:
        assert " ".join(b["trecho"].split()) in texto[b["arquivo"]], (b["lei"], b["trecho"][:80])


#: A abertura pela norma ("O Codigo de Transito Brasileiro estabelece...", "A
#: Constituicao Federal determina..."): o vicio dos textos antigos.
ABRE_PELA_LEI = re.compile(r"^\W*(\w+\s+){0,3}(C[óo]digo|Constitui[çc][ãa]o|CTB|CF|Lei|lei)\b")


def test_os_textos_reais_variam():
    dados, _, _ = _reais()
    aberturas = Counter(" ".join(a["contexto"].split()[:6]).casefold() for a in dados["textos"])
    assert all(n == 1 for n in aberturas.values()), aberturas
    for apoio in dados["textos"]:
        assert not ABRE_PELA_LEI.match(apoio["contexto"]), apoio["tema"]
    dispositivos = Counter(b["lei"] for a in dados["textos"] for b in a["base_legal"])
    assert all(n <= 3 for n in dispositivos.values()), dispositivos

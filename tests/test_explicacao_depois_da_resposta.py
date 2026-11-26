"""A explicacao depois da resposta e a Revisao do simulado (PRF-31).

O que estes testes seguram:

  * o pedido do item de Certo/Errado usa a instrucao em partes, com a chave;
  * a importacao confere o gabarito, descarta o "como ficaria certo" do item
    Certo e o trecho de lei que nao esta, palavra por palavra, no texto
    oficial do projeto - e a explicacao entra assim mesmo, com o aviso;
  * a explicacao nova e achada pela chave, e a antiga pela impressao;
  * no treino, o painel abre no acerto e no erro, com o gabarito por extenso,
    o no e a pegadinha da classificacao e as partes da explicacao;
  * a Revisao so abre com a rodada acabada, na ordem errei, chutei, em
    branco, acertei, e o "por que errei" so no erro de verdade.

Banco temporario, leis de teste numa pasta temporaria, datas fixas: nada de
internet nem do dia de hoje.
"""
import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from radar.db import sessao
from radar.models import Classificacao
from radar.questoes_certo_errado import EM_BRANCO
from radar.servico import explicacoes, manual
from radar.servico import simulado as rodadas
from radar.servico.classificacoes import chave_de
from radar.web.app import app
from tests.test_certo_errado_prf import _item
from tests.test_correcao_na_hora import _ids, _rodada

#: Um pedaco de lei de teste, no HTML da compilacao da Camara.
LEI_DE_TESTE = ("<html><body><p>Art. 280. Ocorrendo infra&ccedil;&atilde;o prevista na "
                "legisla&ccedil;&atilde;o de tr&acirc;nsito, lavrar-se-&aacute; auto de "
                "infra&ccedil;&atilde;o, do qual constar&aacute;:</p></body></html>")
TRECHO_CERTO = ("Ocorrendo infração prevista na legislação de trânsito, "
                "lavrar-se-á auto de infração")


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


@pytest.fixture
def leis_de_teste(tmp_path, monkeypatch):
    pasta = tmp_path / "leis"
    pasta.mkdir()
    (pasta / "ctb-de-teste.html").write_text(LEI_DE_TESTE, encoding="utf-8")
    monkeypatch.setattr(explicacoes, "pastas_das_leis", lambda: [pasta])
    return pasta


def _errar(rodada: int, questao_id: int, letra: str = "e") -> None:
    rodadas.responder(rodada, questao_id, letra)


def _importar(tmp_path, lote: dict, itens: list[dict]) -> dict:
    manual.salvar_pedido(lote)
    resposta = tmp_path / "resposta.json"
    resposta.write_text(json.dumps({
        "lote": lote["lote"], "modelo": "claude-opus-5-5",
        "respostas": [{"id": p["id"], "explicacao": item}
                      for p, item in zip(lote["pedidos"], itens)]}), encoding="utf-8")
    return manual.importar(resposta)


def _explicacao(correta: str, **mais) -> dict:
    base = {"correta": correta,
            "veredito": "O item esta errado: o auto de infracao e lavrado sempre que "
                        "ocorre a infracao, e nao so quando o condutor concorda.",
            "o_que_cobra": "A lavratura do auto de infracao de transito.",
            "dispositivo": "CTB, art. 280", "trecho_da_lei": TRECHO_CERTO,
            "pegadinha": "O 'somente' restringe o que a lei nao restringe.",
            "como_ficaria_certo": "Ocorrendo infracao, lavra-se o auto de infracao.",
            "fonte": "art. 280 do CTB"}
    return {**base, **mais}


# --- o pedido e a importacao -------------------------------------------------

def test_o_pedido_do_certo_errado_vai_em_partes_e_com_a_chave(banco_temporario):
    rodada = _rodada(_item(1, "c"))
    (item,) = _ids(rodada)
    _errar(rodada, item)

    (pedido,) = manual.pedido_de_explicacoes()["pedidos"]

    assert pedido["formato"] == "certo_errado"
    assert pedido["chave"] and pedido["gabarito"] == "c"
    assert "como_ficaria_certo" in pedido["instrucao"]


def test_a_importacao_confere_o_trecho_e_guarda_as_partes(banco_temporario, leis_de_teste,
                                                           tmp_path):
    rodada = _rodada(_item(1, "e"))
    (item,) = _ids(rodada)
    _errar(rodada, item, "c")
    lote = manual.pedido_de_explicacoes()

    resultado = _importar(tmp_path, lote, [_explicacao("e")])

    assert resultado["gravadas"] == 1 and not resultado["avisos"]
    (gravada,) = explicacoes.carregar()[0].values()
    assert gravada.trecho_da_lei == TRECHO_CERTO
    assert gravada.lei_do_trecho == "ctb-de-teste.html"
    assert gravada.como_ficaria_certo and gravada.em_partes


def test_o_trecho_que_nao_esta_na_lei_e_o_certo_reescrito_saem(banco_temporario, leis_de_teste,
                                                               tmp_path):
    """A IA copia, o radar confere: trecho que nao esta no texto oficial e
    descartado, e o item Certo nao tem "como ficaria certo"."""
    rodada = _rodada(_item(1, "c"))
    (item,) = _ids(rodada)
    _errar(rodada, item, "e")
    lote = manual.pedido_de_explicacoes()

    resultado = _importar(tmp_path, lote, [_explicacao(
        "c", veredito="O item esta certo: o auto e lavrado sempre que ocorre a infracao.",
        trecho_da_lei="lavrar-se-a auto de infracao somente com a concordancia do condutor")])

    assert resultado["gravadas"] == 1 and len(resultado["avisos"]) == 2
    (gravada,) = explicacoes.carregar()[0].values()
    assert gravada.trecho_da_lei is None and gravada.como_ficaria_certo is None


def test_explicacao_que_contradiz_o_gabarito_do_item_e_recusada(banco_temporario, tmp_path):
    rodada = _rodada(_item(1, "c"))
    (item,) = _ids(rodada)
    _errar(rodada, item)
    lote = manual.pedido_de_explicacoes()

    resultado = _importar(tmp_path, lote, [_explicacao("e")])

    assert resultado["gravadas"] == 0 and "gabarito oficial e c" in resultado["recusas"][0]


def test_a_explicacao_antiga_vale_pela_impressao(banco_temporario):
    questao = _item(1, "c")
    _rodada(questao)
    manual.caminho_das_explicacoes().write_text(json.dumps([{
        "impressao": questao.impressao, "correta": "c", "explicacao": "Um paragrafo antigo.",
        "fonte": "art. 1 da Lei de Teste", "modelo": "Claude Code", "criado_em": "2026-11-07",
    }]), encoding="utf-8")

    achada = explicacoes.da_questao(questao)

    assert achada is not None and achada.veredito == "Um paragrafo antigo."
    assert not achada.em_partes


# --- o painel no treino ------------------------------------------------------

def _classificar(questao, no="Legislação de Trânsito > Lei nº 9.503/1997", **mais):
    with sessao() as s:
        s.add(Classificacao(
            chave=chave_de(questao), conteudo=no, principal=True,
            status=mais.pop("status", "completa"), procedencia="Claude Code (teste)",
            classificada_em=datetime(2026, 11, 25, 12, 0), **mais))


def test_no_treino_o_painel_abre_no_acerto(cliente):
    questao = _item(1, "c")
    rodada = _rodada(questao)
    (item,) = _ids(rodada)
    _classificar(questao, pegadinha="O 'somente' da afirmacao.")
    cliente.post(f"/simulado/{rodada}/responder", data={"questao_id": item, "letra": "c"})

    tela = cliente.get(f"/simulado/{rodada}?ver={item}").text

    assert "ds-explica--certo" in tela and "O item está CERTO" in tela
    assert "📚 O que essa questão cobra" in tela and "Lei nº 9.503/1997" in tela
    assert "🎯 A pegadinha" in tela and "O &#39;somente&#39; da afirmacao." in tela
    assert "Explicação ainda não pedida" in tela


def test_o_painel_mostra_a_explicacao_em_partes(cliente, leis_de_teste, tmp_path):
    questao = _item(1, "e")
    rodada = _rodada(questao)
    (item,) = _ids(rodada)
    cliente.post(f"/simulado/{rodada}/responder", data={"questao_id": item, "letra": "c"})
    _importar(tmp_path, manual.pedido_de_explicacoes(), [_explicacao("e")])

    tela = cliente.get(f"/simulado/{rodada}?ver={item}").text

    assert "ds-explica--errado" in tela and "O item está ERRADO" in tela
    assert "O item esta errado: o auto de infracao" in tela
    assert "📜 O que a lei diz" in tela and "CTB, art. 280" in tela
    assert "Conferido palavra por palavra" in tela
    assert "✏️ Como ficaria certo" in tela
    assert "claude-opus-5-5" in tela and "Fonte citada: art. 280 do CTB" in tela


# --- a Revisao do simulado ----------------------------------------------------

def test_a_revisao_so_abre_com_a_rodada_acabada(cliente):
    rodada = _rodada(_item(1, "c"), _item(2, "c"),
                     filtros={"rodada": "composta", "quantidade": 2})
    primeiro, _ = _ids(rodada)
    cliente.post(f"/simulado/{rodada}/responder", data={"questao_id": primeiro, "letra": "e"})

    ida = cliente.get(f"/simulado/{rodada}/revisao", follow_redirects=False)

    assert ida.status_code == 303 and ida.headers["location"] == f"/simulado/{rodada}"


def test_a_revisao_vai_de_errei_a_acertei(cliente):
    rodada = _rodada(_item(1, "c"), _item(2, "c"), _item(3, "c"), _item(4, "c"),
                     filtros={"rodada": "composta", "quantidade": 4})
    acertei, errei, chutei, branco = _ids(rodada)
    rodadas.responder(rodada, acertei, "c")
    rodadas.responder(rodada, errei, "e")
    rodadas.responder(rodada, chutei, "c", chutou=True)
    rodadas.responder(rodada, branco, EM_BRANCO)

    revisao = rodadas.revisao_do_simulado(rodada)

    assert [i.grupo for i in revisao.itens] == ["errei", "chutei", "branco", "acertei"]
    assert revisao.contagem == {"errei": 1, "chutei": 1, "branco": 1, "acertei": 1}
    primeira = cliente.get(f"/simulado/{rodada}/revisao?q=1").text
    assert "✗ Errei" in primeira and "Por que errei?" in primeira
    assert "✗ Você marcou Errado" in primeira and "O item está CERTO" in primeira
    segunda = cliente.get(f"/simulado/{rodada}/revisao?q=2").text
    assert "🎲 Chutei" in segunda and "Por que errei?" not in segunda
    assert "Você deixou em branco" in cliente.get(f"/simulado/{rodada}/revisao?q=3").text
    ultima = cliente.get(f"/simulado/{rodada}/revisao?q=4").text
    assert "ds-explica--certo" in ultima and "Terminar a revisão" in ultima
    # O numero fora da conta cai na ponta mais perto.
    assert "Questão 4 de 4" in cliente.get(f"/simulado/{rodada}/revisao?q=99").text


def test_o_gabarito_buscado_por_ia_nao_vira_definitivo_no_painel(cliente):
    """O gabarito que o Claude Code buscou e ninguem conferiu (PMSC-27) leva o
    🟣 tambem no painel: nunca o 🟢 de definitivo."""
    questao = _item(1, "c", gabarito_a_conferir="buscado no site, por conferir")
    rodada = _rodada(questao)
    (item,) = _ids(rodada)
    cliente.post(f"/simulado/{rodada}/responder", data={"questao_id": item, "letra": "c"})

    tela = cliente.get(f"/simulado/{rodada}?ver={item}").text
    painel = tela.split('<section class="ds-explica')[1].split("</header>")[0]

    assert "Gabarito a verificar" in painel and "Gabarito definitivo" not in painel


def test_a_procedencia_sem_data_ganha_a_de_brasilia():
    """01:30 UTC do dia 26 ainda e o dia 25 em Brasilia."""
    sem_data = explicacoes.Explicacao(correta="c", veredito="x" * 40, fonte="f",
                                      modelo="Claude Code", criado_em="2026-11-26T01:30:00+00:00")
    com_data = explicacoes.Explicacao(correta="c", veredito="x" * 40, fonte="f",
                                      modelo="Claude Code, importado manualmente, em 25/11/2026",
                                      criado_em="2026-11-26T01:30:00+00:00")

    assert sem_data.procedencia == "Claude Code · 25/11/2026"
    assert com_data.procedencia == "Claude Code, importado manualmente, em 25/11/2026"

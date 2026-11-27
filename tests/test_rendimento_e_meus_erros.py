"""Navegacao nova, etapas 3 e 4 (PRF-63 e PRF-64).

  * Analises > Meu rendimento: a nota liquida por materia com o bruto ao
    lado, a seta de tendencia, a cor contra a meta e o "Ver detalhes";
  * Revisao > Meus erros: a ultima resposta errada entra sozinha (o chute
    errado e o em branco, nao), agrupada por materia e assunto; o "Refazer"
    abre a rodada e o acerto tira a questao da lista.

Banco temporario e datas relativas a um "agora" passado ao servico: nada
depende do dia nem da internet.
"""
from datetime import timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from radar.models import agora
from radar.questoes_certo_errado import ALTERNATIVAS, EM_BRANCO
from radar.servico import meus_erros, metricas, rendimento
from radar.servico import simulado as rodadas
from radar.web.app import app
from tests.test_correcao_na_hora import _ids, _rodada
from tests.test_simulado import _questao


def _item(numero: int, resposta: str = "c", **mais):
    """Um item de Certo/Errado do Cebraspe."""
    base = dict(banca="CEBRASPE", alternativas=dict(ALTERNATIVAS), resposta=resposta,
                impressao=f"re{numero}", enunciado=f"Item {numero} do rendimento.",
                materia="Direito Penal")
    return _questao(numero, **{**base, **mais})


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


# --- Meu rendimento ------------------------------------------------------------

def test_rendimento_tem_a_nota_liquida_e_o_bruto_ao_lado(banco_temporario):
    rodada = _rodada(_item(1), _item(2), _item(3), _item(4), _item(5))
    um, dois, tres, quatro, cinco = _ids(rodada)
    rodadas.responder(rodada, um, "c")
    rodadas.responder(rodada, dois, "c")
    rodadas.responder(rodada, tres, "e")                 # errada: -1 na nota
    rodadas.responder(rodada, quatro, EM_BRANCO)         # 0 na nota, fora do bruto
    rodadas.responder(rodada, cinco, "c", chutou=True)   # na nota conta; no bruto, nao

    chave = metricas._nome_da_materia()("Direito Penal")
    linha = metricas.rendimento_por_materia()[chave]
    assert (linha.nota.certos, linha.nota.errados, linha.nota.em_branco) == (3, 1, 1)
    assert linha.nota.nota == 2
    assert (linha.bruto.acertos, linha.bruto.medidas) == (2, 3)
    assert linha.feitas == 5
    assert (linha.bruto.chutes, linha.bruto.em_branco) == (1, 1)


def test_vale_a_ultima_resposta_de_cada_questao(banco_temporario):
    primeira = _rodada(_item(1))
    (um,) = _ids(primeira)
    rodadas.responder(primeira, um, "e")
    segunda = rodadas.criar_simulado_de_erros(quantidade=None)
    rodadas.responder(segunda.id, um, "c")
    chave = metricas._nome_da_materia()("Direito Penal")
    assert metricas.rendimento_por_materia()[chave].nota.nota == 1


def test_a_tendencia_compara_as_duas_janelas(banco_temporario, monkeypatch):
    rodada = _rodada(*[_item(n) for n in range(1, 5)])
    for questao_id in _ids(rodada):
        rodadas.responder(rodada, questao_id, "c")
    monkeypatch.setattr(metricas.regua, "carregar",
                        lambda: SimpleNamespace(do_nivel=lambda nivel: 2))
    chave = metricas._nome_da_materia()("Direito Penal")
    # Respondidas "agora": com a referencia 20 dias depois, caem na janela de antes.
    depois = metricas.rendimento_por_materia(agora() + timedelta(days=20))[chave]
    assert (depois.anterior, depois.recente) == (100, None)
    assert depois.tendencia is None
    hoje = metricas.rendimento_por_materia(agora() + timedelta(minutes=1))[chave]
    assert (hoje.recente, hoje.anterior) == (100, None)


def test_a_seta():
    linha = metricas.RendimentoDaMateria("X", recente=70, anterior=60)
    assert linha.tendencia == "subindo"
    assert metricas.RendimentoDaMateria("X", recente=55, anterior=60).tendencia == "caindo"
    assert metricas.RendimentoDaMateria("X", recente=62, anterior=60).tendencia == "estavel"


def _linha(feitas_certas: int, feitas_erradas: int, meta: int = 8, questoes: int = 10,
           minimo: int = 4) -> rendimento.LinhaDoRendimento:
    numeros = metricas.RendimentoDaMateria(
        "X", nota=metricas.NotaLiquida(certos=feitas_certas, errados=feitas_erradas))
    numeros.bruto.acertos = feitas_certas
    numeros.bruto.erros = feitas_erradas
    return rendimento.LinhaDoRendimento("X", questoes, meta, minimo, numeros)


def test_a_cor_contra_a_meta():
    # Meta 8 em 10 = 80%. A nota liquida e que vai contra ela.
    assert _linha(9, 1).cor == "verde"              # 9 - 1 = 8 em 10: 80%
    assert _linha(17, 3).cor == "amarelo"           # 14 em 20: 70%, ate 15 abaixo
    assert _linha(7, 3).cor == "vermelho"           # 4 em 10: 40%
    assert _linha(1, 1).cor == "pouca_amostra"
    assert rendimento.LinhaDoRendimento("X", 10, 8, 4).cor == "sem_dado"


def test_montar_poe_o_peso_e_a_materia_de_fora_no_fim(banco_temporario):
    rodada = _rodada(_item(1), _item(2, materia="Matéria que não está no plano"))
    for questao_id in _ids(rodada):
        rodadas.responder(rodada, questao_id, "c")
    chave = metricas._nome_da_materia()("Direito Penal")
    plano = SimpleNamespace(materias=[SimpleNamespace(nome="Outra", questoes=20, meta=15),
                                      SimpleNamespace(nome=chave, questoes=5, meta=4)])
    r = rendimento.montar(plano)
    assert [l.materia for l in r.linhas][:2] == ["Outra", chave]
    assert r.linhas[1].numeros.feitas == 1
    assert r.linhas[0].cor == "sem_dado"


def test_a_tela_meu_rendimento(cliente):
    texto = cliente.get("/analises").text
    assert "Meu rendimento" in texto
    assert 'href="/analises/edital"' in texto           # o Ver detalhes
    assert cliente.get("/analises/edital").status_code == 200


# --- Meus erros ----------------------------------------------------------------

def test_meus_erros_entra_sozinho_e_sai_quando_acerto(banco_temporario):
    rodada = _rodada(_item(1), _item(2), _item(3), _item(4))
    um, dois, tres, quatro = _ids(rodada)
    rodadas.responder(rodada, um, "e")                   # erro de verdade
    rodadas.responder(rodada, dois, "e", chutou=True)    # chute errado: fora
    rodadas.responder(rodada, tres, EM_BRANCO)           # em branco: fora
    rodadas.responder(rodada, quatro, "c")               # acerto

    erros = meus_erros.montar()
    assert erros.total == 1
    item = erros.materias[0].assuntos[0].erros[0].item
    assert (item.questao_id, item.simulado_id, item.escolhida) == (um, rodada, "e")
    assert erros.materias[0].assuntos[0].nome == meus_erros.SEM_ASSUNTO

    refazer = meus_erros.criar_rodada()
    assert _ids(refazer.id) == [um]
    rodadas.responder(refazer.id, um, "c")
    assert meus_erros.montar().total == 0


def test_refazer_so_uma_materia(banco_temporario):
    rodada = _rodada(_item(1), _item(2, materia="Direito Constitucional"))
    um, dois = _ids(rodada)
    rodadas.responder(rodada, um, "e")
    rodadas.responder(rodada, dois, "e")
    nome = metricas._nome_da_materia()("Direito Penal")
    assert _ids(meus_erros.criar_rodada(nome).id) == [um]
    assert meus_erros.criar_rodada("Matéria sem erro") is None


def test_ficha_do_no():
    escritas = [SimpleNamespace(id="a", tema="Penal geral", nos=["Penal"]),
                SimpleNamespace(id="b", tema="Lei no tempo", nos=["Penal > Lei penal no tempo"]),
                SimpleNamespace(id="c", tema="Crimes", nos=["Penal > Crimes > Furto"])]
    assert meus_erros.ficha_do_no("Penal > Lei penal no tempo > Retroatividade", escritas).ident == "b"
    assert meus_erros.ficha_do_no("Penal > Crimes", escritas).ident == "a"
    assert meus_erros.ficha_do_no("Civil > Contratos", escritas) is None
    sem_geral = escritas[1:]
    # Nenhuma contem o no: vale a que cobre um no dentro dele.
    assert meus_erros.ficha_do_no("Penal > Crimes", sem_geral).ident == "c"


def test_a_tela_meus_erros_e_o_refazer(cliente):
    rodada = _rodada(_item(1))
    (um,) = _ids(rodada)
    rodadas.responder(rodada, um, "e")
    texto = cliente.get("/revisao").text
    assert "Meus erros" in texto and "Item 1 do rendimento." in texto
    assert 'class="ativo" href="/revisao">Meus erros' in texto
    assert "Por que errei?" in texto                    # o motivo, opcional
    r = cliente.post("/revisao/refazer", data={}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/simulado/")


def test_sem_erro_a_tela_diz_e_o_refazer_volta(cliente):
    assert "Nenhum erro para rever agora" in cliente.get("/revisao").text
    r = cliente.post("/revisao/refazer", data={}, follow_redirects=False)
    assert r.headers["location"] == "/revisao"

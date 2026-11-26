"""O item de Certo/Errado escrito pela IA, por aula do cronograma (PRF-40).

O que estes testes seguram:

  * a forma: resposta "c" ou "e", as alternativas do Cebraspe sempre as mesmas
    (e por elas que a tela e a nota liquida reconhecem o item);
  * a importacao: sem artigo, sem explicacao, fora dos nos da aula ou copia de
    um exemplo real, o item e recusado e contado; o que entra guarda a
    explicacao e diz quantos certos e quantos errados;
  * o treino: o item gerado tem o "Deixar em branco" e nunca entra na nota
    liquida, que e so das questoes reais (regra 1).
"""
import json

import pytest
from sqlalchemy import select

from radar import gerador
from radar.db import sessao
from radar.models import QuestaoGerada, RespostaDeSimulado
from radar.questoes import impressao_de
from radar.questoes_certo_errado import ALTERNATIVAS, EM_BRANCO
from radar.servico import conteudos as servico_conteudos
from radar.servico import geradas, manual, metricas
from radar.servico import simulado as servico_simulado

MATERIA = "Legislação de Trânsito"
CTB = f"{MATERIA} > Código de Trânsito Brasileiro"
INFRACOES = f"{CTB} > Capítulo XV - Das infrações"
CRIMES = f"{CTB} > Capítulo XIX - Dos crimes de trânsito"
EXEMPLO = ("Conduzir veículo sob a influência de álcool é infração gravíssima, punida "
           "com multa e suspensão do direito de dirigir por doze meses.")


def _item(**mudancas):
    item = {"enunciado": "Quem dirige com a CNH vencida há mais de trinta dias comete "
                         "infração gravíssima.",
            "resposta": "c", "artigo": "CTB, art. 162, V", "conteudo": INFRACOES,
            "explicacao": "Certo: é a infração do art. 162, V, do CTB."}
    item.update(mudancas)
    return item


@pytest.fixture
def lote(banco_temporario, tmp_path):
    """Um lote de Certo/Errado de uma aula, como o `pedido_de_certo_errado` monta,
    com os nos da aula na arvore do banco temporario."""
    servico_conteudos.adicionar(None, MATERIA)
    servico_conteudos.adicionar(MATERIA, "Código de Trânsito Brasileiro")
    servico_conteudos.adicionar(CTB, "Capítulo XV - Das infrações")
    servico_conteudos.adicionar(CTB, "Capítulo XIX - Dos crimes de trânsito")
    lote = manual._novo_lote("certo_errado", [{
        "id": "ce1", "formato": "certo_errado", "modo": "do_zero", "quantas": 6,
        "materia": MATERIA, "assunto": None, "origem_impressao": None,
        "origem_chave": None, "tema": "CTB, infrações 1", "modo_do_pedido": "treino",
        "conteudo": CTB, "escopo": CTB, "escopo_dispositivos": [INFRACOES],
        "base": "fonte_oficial", "evidencia_da_base": "nenhuma", "niveis": None,
        "exemplos": [{"enunciado": EXEMPLO, "gabarito": "Certo",
                      "impressao": impressao_de(EXEMPLO)}],
        "instrucao": gerador.INSTRUCAO_CERTO_ERRADO, "pedido": "AULA: ..."}])
    pedido = tmp_path / "pedido.json"
    pedido.write_text(json.dumps(lote), encoding="utf-8")
    return lote, pedido


def _importar(lote_e_pedido, itens, tmp_path):
    lote, pedido = lote_e_pedido
    resposta = tmp_path / "resposta.json"
    resposta.write_text(json.dumps({
        "lote": lote["lote"], "modelo": "claude-opus-5-5",
        "respostas": [{"id": "ce1", "questoes": itens}]}), encoding="utf-8")
    return manual.importar(resposta, pedido)


def test_a_forma_do_item_e_a_do_cebraspe():
    certo = gerador.conferir_certo_errado(_item(resposta="C"))
    assert certo["alternativas"] == ALTERNATIVAS and certo["resposta"] == "c"
    assert gerador.conferir_certo_errado(_item(resposta="a")) is None
    assert gerador.conferir_certo_errado(_item(enunciado="Curto.")) is None


def test_a_importacao_recusa_o_que_nao_presta_e_guarda_a_explicacao(lote, tmp_path):
    resultado = _importar(lote, [
        _item(),
        _item(enunciado="O condutor que deixa de usar o cinto de segurança comete "
                        "infração média.", resposta="e", artigo="CTB, art. 167",
              explicacao="Errado: a infração é grave, e não média (CTB, art. 167)."),
        _item(enunciado="Item sem o artigo em que se apoia, que não pode entrar.",
              artigo=""),
        _item(enunciado="Item sem a explicação do certo ou do errado, recusado.",
              explicacao=""),
        _item(enunciado="Item de outra parte do CTB, fora dos nós da aula pedida.",
              conteudo=CRIMES),
        _item(enunciado=EXEMPLO),
    ], tmp_path)

    assert resultado["tipo"] == "certo_errado" and resultado["gravadas"] == 2
    assert (resultado["certos"], resultado["errados"]) == (1, 1)
    motivos = " | ".join(resultado["recusas"])
    for motivo in ("sem o artigo", "sem a explicacao", "nao e nenhum dos elementos pedidos",
                   "copia de um item real"):
        assert motivo in motivos
    with sessao() as s:
        gravada = s.scalar(select(QuestaoGerada).where(QuestaoGerada.resposta == "c"))
        assert gravada.alternativas == ALTERNATIVAS
        assert gravada.explicacao.startswith("Certo: é a infração do art. 162")
        assert gravada.conteudo == INFRACOES and gravada.evidencia_da_base == "nenhuma"
        assert "claude-opus-5-5" in gravada.modelo


def test_a_gerada_tem_em_branco_e_fica_fora_da_nota_liquida(lote, tmp_path):
    _importar(lote, [_item(), _item(enunciado="Outro item de treino sobre a "
                                              "CNH vencida, este errado.", resposta="e")],
              tmp_path)
    rodada = geradas.criar_simulado(quantidade=2, conteudo=INFRACOES)
    with sessao() as s:
        linhas = list(s.scalars(select(RespostaDeSimulado)
                                .where(RespostaDeSimulado.simulado_id == rodada.id)))
        assert len(linhas) == 2 and all(r.gerada for r in linhas)
        ids = [r.questao_id for r in linhas]
    assert servico_simulado.responder(rodada.id, ids[0], EM_BRANCO) is None
    assert servico_simulado.responder(rodada.id, ids[1], "c") is not None
    with sessao() as s:
        branco = s.scalar(select(RespostaDeSimulado)
                          .where(RespostaDeSimulado.questao_id == ids[0]))
        assert branco.escolhida == EM_BRANCO and branco.acertou is None
    # A nota liquida e so das reais: a gerada treina, nunca mede.
    assert metricas.nota_liquida_acumulada().itens == 0


def test_o_pedido_completa_a_aula_ate_o_numero_contando_as_geradas(banco_temporario, tmp_path,
                                                                   monkeypatch):
    # A aula e a de verdade (a ficha vem do data/fichas.json versionado, com o no
    # da parte do capitulo, PRF-40); o cronograma e trocado por ela so.
    import shutil
    from datetime import date
    from types import SimpleNamespace

    from radar import config

    shutil.copy2(config.RAIZ / "data" / "fichas.json", tmp_path / "fichas.json")
    titulo = "CTB, infrações 1 (arts. 161 a 190)"
    aula = SimpleNamespace(tipo="teoria", materia=MATERIA, titulo=titulo,
                           conteudo=f"{MATERIA} > Lei nº 9.503/1997")
    monkeypatch.setattr(manual, "_aulas", lambda materia, temas=None: [(date(2027, 1, 11), aula)])

    (pedido,) = manual.pedido_de_certo_errado(MATERIA, ate=35)["pedidos"]
    parte = next(n for n in pedido["escopo_dispositivos"] if n.endswith("CTB, arts. 161 a 190"))
    assert pedido["formato"] == "certo_errado" and pedido["quantas"] == 35
    assert pedido["evidencia_da_base"] == "nenhuma" and pedido["modo"] == "do_zero"

    with sessao() as s:
        for n in range(5):
            s.add(QuestaoGerada(modo="do_zero", modelo="teste", materia=MATERIA,
                                conteudo=parte, enunciado=f"Item gerado {n} da aula.",
                                alternativas=dict(ALTERNATIVAS), resposta="c",
                                impressao=f"imp{n}"))
    (pedido,) = manual.pedido_de_certo_errado(MATERIA, ate=35)["pedidos"]
    assert pedido["quantas"] == 30 and pedido["geradas_que_ja_tem"] == 5
    assert manual.pedido_de_certo_errado(MATERIA, ate=5)["pedidos"] == []


def test_a_rodada_da_faixa_traz_o_certo_errado_antes_da_multipla_escolha(banco_temporario):
    # PRF-41: o tema pode ter dezenas de geradas de multipla escolha herdadas da
    # PMSC; das nunca feitas, as de Certo/Errado vem primeiro.
    with sessao() as s:
        for n in range(6):
            s.add(QuestaoGerada(modo="variacao", modelo="teste", materia=MATERIA,
                                conteudo=INFRACOES, enunciado=f"Multipla escolha {n}.",
                                alternativas={"a": "um", "b": "dois", "c": "tres", "d": "quatro"},
                                resposta="a", impressao=f"me{n}"))
        for n in range(2):
            s.add(QuestaoGerada(modo="do_zero", modelo="teste", materia=MATERIA,
                                conteudo=INFRACOES, enunciado=f"Item de Certo ou Errado {n}.",
                                alternativas=dict(ALTERNATIVAS), resposta="c", impressao=f"ce{n}"))
        # O outro no da faixa so tem Certo/Errado: a rodada dos dois nos junta
        # o C/E de ambos antes de dar a multipla escolha do primeiro.
        for n in range(3):
            s.add(QuestaoGerada(modo="do_zero", modelo="teste", materia=MATERIA,
                                conteudo=CRIMES, enunciado=f"Item de crime de trânsito {n}.",
                                alternativas=dict(ALTERNATIVAS), resposta="e", impressao=f"cr{n}"))

    def formatos(quantidade, nos):
        rodada = geradas.criar_simulado(quantidade=quantidade, conteudos=nos)
        with sessao() as s:
            ids = list(s.scalars(select(RespostaDeSimulado.questao_id)
                                 .where(RespostaDeSimulado.simulado_id == rodada.id)))
            return sorted(s.get(QuestaoGerada, i).alternativas == ALTERNATIVAS for i in ids)

    for _ in range(5):  # o sorteio e aleatorio dentro do grupo: repete para pegar
        assert formatos(3, [INFRACOES]) == [False, True, True]
        assert formatos(5, [INFRACOES, CRIMES]) == [True] * 5
        assert formatos(6, [INFRACOES, CRIMES]) == [False] + [True] * 5


def test_o_apoio_do_item_so_aparece_depois_da_resposta(lote, tmp_path):
    # PRF-43: no C/E sem lei o `artigo` ("Bioma Pampa: so no RS") entrega o
    # gabarito; ele vem com o "Por que, segundo a IA", depois de responder.
    from fastapi.testclient import TestClient
    from radar.web.app import app

    _importar(lote, [_item(artigo="CTB, art. 162, V: CNH vencida há mais de 30 dias")], tmp_path)
    rodada = geradas.criar_simulado(quantidade=1, conteudo=INFRACOES)
    with sessao() as s:
        (qid,) = s.scalars(select(RespostaDeSimulado.questao_id)
                           .where(RespostaDeSimulado.simulado_id == rodada.id))
    cliente = TestClient(app)
    antes = cliente.get(f"/simulado/{rodada.id}").text
    assert "CNH vencida há mais de 30 dias" not in antes
    cliente.post(f"/simulado/{rodada.id}/responder", data={"questao_id": qid, "letra": "c"})
    depois = cliente.get(f"/simulado/{rodada.id}?ver={qid}").text
    assert "CNH vencida há mais de 30 dias" in depois and "segundo a IA" in depois


@pytest.mark.parametrize("fonte, serve", [
    ("MBFT (Res. CONTRAN 985/2022), Parte Geral, item 7.2", True),
    ("Res. CONTRAN 969/2022, Anexo I, itens 2.3 e 2.4", True),
    ("conforme o MBFT", False),
])
def test_o_item_do_mbft_e_dos_anexos_vale_como_fonte(fonte, serve):
    # A Parte Geral do MBFT e os anexos das resolucoes sao numerados por item.
    assert manual.fonte_serve(fonte, MATERIA) is serve


def test_o_formato_da_resposta_do_certo_errado_pede_o_modelo_e_a_explicacao():
    formato = manual._formato("certo_errado")
    assert list(formato)[:2] == ["lote", "modelo"]
    (item,) = formato["respostas"][0]["questoes"]
    assert {"enunciado", "resposta", "artigo", "conteudo", "explicacao"} <= set(item)

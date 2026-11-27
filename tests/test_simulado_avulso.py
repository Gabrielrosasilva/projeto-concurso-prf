"""O Simulado da tela Simulado (PRF-53) e as partes das geradas antigas (PRF-54).

O que estes testes seguram:

  * o Simulado traz primeiro a real que eu errei, depois as reais que nunca
    fiz e so entao o Certo/Errado da IA; a real que eu acertei nao volta;
  * as questoes se dividem pelas materias na proporcao da prova, e o que uma
    materia nao tem passa para as outras;
  * a rodada corrige no fim e mostra as reais e as geradas separadas;
  * o pedido das partes manda so as geradas de C/E sem pegadinha, e a
    importacao grava a pegadinha e o "como ficaria certo" com a procedencia,
    sem trocar o que ja existe.
"""
import json
import random

from sqlalchemy import select

from radar.db import sessao
from radar.models import QuestaoDeProva, QuestaoGerada, RespostaDeSimulado, Simulado
from radar.questoes_certo_errado import ALTERNATIVAS
from radar.servico import composicao, explicacoes, manual
from radar.servico import simulado as servico_simulado
from radar.servico import simulado_avulso as sa
from tests.test_composicao import INTERPRETACAO, PORTUGUES, acervo  # noqa: F401


def _escolhida(i, origem=sa.CEBRASPE, materia="A"):
    return sa.Escolhida(i, origem, materia, False)


def test_a_cota_segue_o_peso_e_a_falta_passa_para_outra_materia():
    filas = {"A": [_escolhida(i, materia="A") for i in range(2)],
             "B": [_escolhida(i, materia="B") for i in range(10, 20)]}
    escolhidas, por_materia = sa.escolher(6, filas, {"A": 2, "B": 1})
    # A pedia 4 (2/3 de 6) e so tinha 2: as outras 2 vieram de B.
    assert por_materia == {"A": 2, "B": 4} and len(escolhidas) == 6


def test_o_mesmo_id_nao_entra_duas_vezes_na_rodada():
    # O banco guarda a resposta por (rodada, questao_id): uma real e uma
    # gerada de mesmo id nao cabem juntas.
    filas = {"A": [_escolhida(7), _escolhida(7, sa.GERADA), _escolhida(8, sa.GERADA)]}
    escolhidas, _ = sa.escolher(5, filas, {"A": 1})
    assert [(e.origem, e.questao_id) for e in escolhidas] == [
        (sa.CEBRASPE, 7), (sa.GERADA, 8)]


def _gerada(n, conteudo=INTERPRETACAO, resposta="c", **campos):
    with sessao() as s:
        q = QuestaoGerada(modo="do_zero", modelo="Claude Code (claude-opus-5-5), em 26/11/2026",
                          materia=PORTUGUES, conteudo=conteudo,
                          enunciado=f"Item gerado de número {n} sobre o texto.",
                          alternativas=dict(ALTERNATIVAS), resposta=resposta,
                          impressao=f"g{n}", artigo="Regra: inferência",
                          explicacao="Certo: é o que o texto diz.", **campos)
        s.add(q)
        s.flush()
        return q.id


def _ids(rodada):
    with sessao() as s:
        return [(r.gerada, r.questao_id) for r in s.scalars(
            select(RespostaDeSimulado).where(RespostaDeSimulado.simulado_id == rodada.id)
            .order_by(RespostaDeSimulado.ordem))]


def test_os_erros_primeiro_depois_as_novas_e_a_ia_no_fim(acervo, monkeypatch):
    monkeypatch.setattr(composicao, "reserva_das_que_medem",
                        lambda data, plano=None: composicao.Reserva())
    with sessao() as s:
        reais = {q.numero: q.id for q in s.scalars(
            select(QuestaoDeProva).where(QuestaoDeProva.numero.in_([1, 2, 3, 8])))}
    gerada = _gerada(1, id=9001)   # longe dos ids das reais do banco de teste
    # Respondo a 1 errado e a 2 certo, numa rodada qualquer.
    with sessao() as s:
        antes = Simulado(filtros={"quantidade": 2})
        s.add(antes)
        s.flush()
        ident = antes.id
        s.add(RespostaDeSimulado(simulado_id=ident, questao_id=reais[1], ordem=1))
        s.add(RespostaDeSimulado(simulado_id=ident, questao_id=reais[2], ordem=2))
    servico_simulado.responder(ident, reais[1], "b")   # errada (o gabarito e a)
    servico_simulado.responder(ident, reais[2], "a")   # certa

    rodada = sa.criar(quantidade=10, materia=PORTUGUES, sorteio=random.Random(3))
    ordem = _ids(rodada)
    assert ordem[0] == (False, reais[1])                  # o erro primeiro
    assert (False, reais[2]) not in ordem                 # a acertada nao volta
    assert ordem[-1] == (True, gerada)                    # a IA onde as reais acabaram
    assert {(False, reais[3]), (False, reais[8])} <= set(ordem[1:-1])
    f = rodada.filtros
    assert f["rodada"] == sa.RODADA and f["geradas_na_rodada"] == 1 and f["a_rever"] == 1
    assert f["faltaram"] == 10 - len(ordem)
    assert not servico_simulado.corrige_na_hora(rodada)


def test_o_simulado_real_repete_as_acertadas_mais_antigas(acervo, monkeypatch):
    # PRF-55: so questao real; acabando as novas, as que eu acertei voltam,
    # a de mais tempo primeiro, e a rodada conta quantas eram repetidas.
    monkeypatch.setattr(composicao, "reserva_das_que_medem",
                        lambda data, plano=None: composicao.Reserva())
    _gerada(2, id=9002)
    with sessao() as s:
        todas = [q.id for q in s.scalars(
            select(QuestaoDeProva).where(QuestaoDeProva.anulada.is_not(True))
            .where(QuestaoDeProva.resposta.is_not(None)).order_by(QuestaoDeProva.id))]
        antes = Simulado(filtros={"quantidade": len(todas)})
        s.add(antes)
        s.flush()
        ident = antes.id
        for ordem, qid in enumerate(todas, start=1):
            s.add(RespostaDeSimulado(simulado_id=ident, questao_id=qid, ordem=ordem))
    errada, *certas = todas
    servico_simulado.responder(ident, errada, "b")          # errada
    for qid in certas:                                      # certas, uma depois da outra
        servico_simulado.responder(ident, qid, "a")

    rodada = sa.criar(quantidade=50, materia=PORTUGUES, modo=sa.REAL, sorteio=random.Random(1))
    ordem = _ids(rodada)
    assert all(not gerada for gerada, _ in ordem)            # nada da IA
    assert ordem[0] == (False, errada)                       # o erro primeiro
    repetidas = [qid for _g, qid in ordem[1:]]
    # As acertadas voltam na ordem em que foram respondidas (a mais antiga antes).
    assert repetidas == [q for q in certas if q in repetidas]
    f = rodada.filtros
    assert f["rodada"] == sa.RODADA_REAL and f["repetidas"] == len(repetidas) > 0
    assert not servico_simulado.corrige_na_hora(rodada)


# --- as partes das geradas antigas (PRF-54) -----------------------------------

def test_o_pedido_e_a_importacao_das_partes(banco_temporario, tmp_path):
    sem_certo = _gerada(10, resposta="c")
    sem_errado = _gerada(11, resposta="e")
    ja_tem = _gerada(12, resposta="e", pegadinha="A de antes.", como_ficaria_certo="Já certo.")
    lote = manual.pedido_de_partes()
    itens = {i["id"]: i for p in lote["pedidos"] for i in p["itens"]}
    assert set(itens) == {sem_certo, sem_errado} and itens[sem_errado]["resposta"] == "Errado"
    pedido = tmp_path / "pedido.json"
    pedido.write_text(json.dumps(lote), encoding="utf-8")

    resposta = tmp_path / "resposta.json"
    resposta.write_text(json.dumps({
        "lote": lote["lote"], "modelo": "claude-opus-5-5",
        "respostas": [{"id": lote["pedidos"][0]["id"], "itens": [
            {"id": sem_certo, "pegadinha": "Parece pouco, mas basta.", "como_ficaria_certo": "x",
             "suspeita": ""},
            {"id": sem_errado, "pegadinha": "Troca o prazo.", "como_ficaria_certo": "",
             "suspeita": "a lei mudou"},
            {"id": ja_tem, "pegadinha": "Nova.", "como_ficaria_certo": "Nova."}]}]}),
        encoding="utf-8")
    resultado = manual.importar(resposta, pedido)
    # O errado sem o "como ficaria certo" e recusado; o que nao era do pedido tambem.
    assert resultado["gravadas"] == 1 and len(resultado["recusas"]) == 2
    assert [m for _i, _c, m in resultado["suspeitas"]] == ["a lei mudou"]
    with sessao() as s:
        certo = s.get(QuestaoGerada, sem_certo)
        antiga = s.get(QuestaoGerada, ja_tem)
        assert certo.pegadinha == "Parece pouco, mas basta." and certo.como_ficaria_certo is None
        assert "claude-opus-5-5" in certo.partes_procedencia
        assert antiga.pegadinha == "A de antes." and antiga.partes_procedencia is None
        painel = explicacoes.painel_da_gerada(certo)
    assert painel.pegadinha_a_mostrar == "Parece pouco, mas basta."
    assert "claude-opus-5-5" in painel.procedencia_das_partes

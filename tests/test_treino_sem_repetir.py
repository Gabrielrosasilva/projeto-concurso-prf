"""O treino que nao repete e o Certo/Errado da IA (PRF-48).

O que estes testes seguram:

  * a rodada so de geradas de Certo/Errado tem a NOTA LIQUIDA (a errada anula
    uma certa), e ela nunca se soma a das reais (regra 1);
  * o botao "IA" da faixa traz so o Certo/Errado que eu nunca fiz; feitos
    todos, nao ha rodada - e a faixa diz que acabou, com o comando de gerar;
  * o pedido `--novas` completa a aula ate N itens que eu ainda nao fiz e leva
    os ja escritos, para a IA nao repetir;
  * o botao "Certo ou Errado" e uma rodada para responder, so com os itens
    reais de Certo/Errado que eu nunca fiz; o treino real tambem nao repete.
"""
import shutil
from datetime import date
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import select

from radar import config, fichas
from radar.db import sessao
from radar.models import QuestaoDeProva, QuestaoGerada, RespostaDeSimulado
from radar.questoes_certo_errado import ALTERNATIVAS, EM_BRANCO
from radar.servico import classificacoes, composicao, fepese_no_radar, geradas, manual, metricas
from radar.servico import simulado as servico_simulado
from radar.web.app import app
from tests.test_composicao import ALVO_2019, INTERPRETACAO, acervo  # noqa: F401

MATERIA = "Legislação de Trânsito"
INFRACOES = f"{MATERIA} > Código de Trânsito Brasileiro > Capítulo XV - Das infrações"


def _gerada(n, *, resposta="c", certo_errado=True, conteudo=INFRACOES) -> int:
    with sessao() as s:
        q = QuestaoGerada(
            modo="do_zero", modelo="Claude Code (claude-opus-5-5), em 26/11/2026",
            materia=MATERIA, conteudo=conteudo, enunciado=f"Item gerado número {n} da aula.",
            alternativas=(dict(ALTERNATIVAS) if certo_errado
                          else {"a": "um", "b": "dois", "c": "tres", "d": "quatro"}),
            resposta=resposta, impressao=f"ger{n}", artigo="CTB, art. 162, V",
            explicacao=f"{'Certo' if resposta == 'c' else 'Errado'}: o porque do item {n}.")
        s.add(q)
        s.flush()
        return q.id


def _ids_da_rodada(rodada) -> list[int]:
    with sessao() as s:
        return list(s.scalars(select(RespostaDeSimulado.questao_id)
                              .where(RespostaDeSimulado.simulado_id == rodada.id)
                              .order_by(RespostaDeSimulado.ordem)))


# --- a nota liquida da rodada de IA ---------------------------------------------

def test_a_rodada_de_ia_tem_a_nota_liquida_que_nao_soma_com_a_real(banco_temporario):
    respostas = {_gerada(1, resposta="c"): "c",       # certa
                 _gerada(2, resposta="e"): "c",       # errada
                 _gerada(3, resposta="c"): EM_BRANCO,  # em branco
                 _gerada(4, resposta="e"): "e"}       # certa
    rodada = geradas.criar_simulado(quantidade=4, conteudo=INFRACOES)
    for questao_id in _ids_da_rodada(rodada):
        servico_simulado.responder(rodada.id, questao_id, respostas[questao_id])

    resumo = metricas.resumo_do_simulado(rodada.id)
    nota = resumo["nota_ia"]
    assert (nota.certos, nota.errados, nota.em_branco, nota.nota) == (2, 1, 1, 1)
    # O acerto bruto continua o mesmo: 2 acertos. A nota e ao lado.
    assert resumo["acertos"] == 2 and resumo["nota"] is None
    # Treina, nunca mede: a nota das reais nao viu nada.
    assert metricas.nota_liquida_acumulada().itens == 0

    # O placar no topo da questao e o relatorio do fim dizem a nota.
    cliente = TestClient(app)
    ultima = _ids_da_rodada(rodada)[-1]
    tela = cliente.get(f"/simulado/{rodada.id}?ver={ultima}").text
    assert "nota 1 (2 certos − 1 errado, 1 em branco)" in tela
    fim = cliente.get(f"/simulado/{rodada.id}").text
    assert "na nota líquida" in fim and "nunca se soma à das questões reais" in fim


# --- o botao "IA": so o Certo/Errado que eu nunca fiz ---------------------------

def test_o_botao_ia_so_traz_certo_errado_que_eu_nunca_fiz(banco_temporario):
    multipla = [_gerada(n, resposta="a", certo_errado=False) for n in (10, 11)]
    ce = [_gerada(n) for n in (20, 21, 22)]
    # Fiz um dos itens de C/E numa rodada qualquer.
    antes = geradas.criar_simulado(quantidade=1, impressoes=["ger20"])
    servico_simulado.responder(antes.id, ce[0], "c")

    rodada = geradas.criar_simulado(quantidade=10, conteudos=[INFRACOES],
                                    so_certo_errado=True, sem_repetir=True)
    assert sorted(_ids_da_rodada(rodada)) == ce[1:]
    assert not set(_ids_da_rodada(rodada)) & set(multipla)
    assert rodada.filtros["so_certo_errado"] and "faltou" not in rodada.filtros

    for questao_id in _ids_da_rodada(rodada):
        servico_simulado.responder(rodada.id, questao_id, "c")
    # Feitos todos: nao ha rodada - o treino nao repete.
    assert geradas.criar_simulado(quantidade=10, conteudos=[INFRACOES],
                                  so_certo_errado=True, sem_repetir=True) is None


def test_a_faixa_conta_os_itens_novos_e_da_o_comando(banco_temporario, monkeypatch):
    for n in range(3):
        _gerada(n)
    _gerada(9, resposta="a", certo_errado=False)
    rodada = geradas.criar_simulado(quantidade=1, impressoes=["ger0"])
    servico_simulado.responder(rodada.id, _ids_da_rodada(rodada)[0], "c")
    tema = "CTB, infrações 1 (arts. 161 a 190)"
    monkeypatch.setattr(manual, "titulos_das_aulas", lambda: {(MATERIA, tema)})
    gf = fichas.GeradasDaFaixa(tema=tema, materia=MATERIA, questoes=15, filtro=None,
                               nos=tuple(fichas.geradas_por_no(15, [INFRACOES], {})))

    (ia,) = geradas.ia_das_faixas({("manha", 1): gf}).values()
    assert (ia.total, ia.novos, ia.feitos) == (3, 2, 1)
    assert ia.precisa_gerar and "Restam 2 itens novos" in ia.frase
    assert ia.comando == (r'.venv\Scripts\radar.exe gerar --pedido --certo-errado '
                          f'--materia "{MATERIA}" --tema "{tema}" --novas 50')


def test_o_aviso_diz_que_acabou_e_sem_aula_nao_ha_comando():
    sem_nada = geradas.CertoErradoDaIA(MATERIA, "Tema", total=0, novos=0)
    assert "ainda não escreveu" in sem_nada.frase and sem_nada.comando
    acabou = geradas.CertoErradoDaIA(MATERIA, "Tema", total=30, novos=0)
    assert "Você já fez os 30 itens" in acabou.frase and "não repete" in acabou.frase
    cheio = geradas.CertoErradoDaIA(MATERIA, "Tema", total=80, novos=50)
    assert not cheio.precisa_gerar and cheio.comando is None
    sem_aula = geradas.CertoErradoDaIA(MATERIA, "Tema", total=0, novos=0, tem_aula=False)
    assert sem_aula.comando is None


# --- o pedido --novas -------------------------------------------------------------

def test_o_pedido_com_novas_conta_so_as_que_eu_nao_fiz(banco_temporario, tmp_path,
                                                       monkeypatch):
    # A aula e a de verdade (a ficha do data/fichas.json versionado, PRF-40).
    shutil.copy2(config.RAIZ / "data" / "fichas.json", tmp_path / "fichas.json")
    titulo = "CTB, infrações 1 (arts. 161 a 190)"
    aula = SimpleNamespace(tipo="teoria", materia=MATERIA, titulo=titulo,
                           conteudo=f"{MATERIA} > Lei nº 9.503/1997")
    monkeypatch.setattr(manual, "_aulas", lambda materia, temas=None: (
        [(date(2027, 1, 11), aula)] if not temas or titulo in temas else []))

    (pedido,) = manual.pedido_de_certo_errado(MATERIA, novas=50)["pedidos"]
    parte = next(n for n in pedido["escopo_dispositivos"] if n.endswith("CTB, arts. 161 a 190"))
    ids = [_gerada(n, conteudo=parte) for n in range(5)]
    rodada = geradas.criar_simulado(quantidade=2, impressoes=["ger0", "ger1"])
    for questao_id in _ids_da_rodada(rodada):
        servico_simulado.responder(rodada.id, questao_id, "c")

    lote = manual.pedido_de_certo_errado(MATERIA, temas=[titulo], novas=50)
    (pedido,) = lote["pedidos"]
    assert pedido["quantas"] == 47 and pedido["geradas_que_nao_fiz"] == 3
    assert pedido["geradas_que_ja_tem"] == len(ids) and len(pedido["ja_escritos"]) == 5
    assert "ja_escritos" in pedido["instrucao"] and lote["novas"] == 50
    assert manual.pedido_de_certo_errado(MATERIA, temas=[titulo], novas=3)["pedidos"] == []
    # O --ate de sempre continua contando tudo, e sem a lista.
    (velho,) = manual.pedido_de_certo_errado(MATERIA, temas=[titulo], ate=35)["pedidos"]
    assert "ja_escritos" not in velho and velho["geradas_que_ja_tem"] == 5
    assert manual.pedido_de_certo_errado(MATERIA, temas=["Outra aula"],
                                         novas=50)["sem_aula"] == ["Outra aula"]


# --- o "Certo ou Errado" e o treino real sem repetir ------------------------------

def _real_de_certo_errado(numero):
    with sessao() as s:
        q = QuestaoDeProva(
            prova_url=ALVO_2019, banca="FEPESE", ano=2019, numero=numero,
            materia="Língua Portuguesa", enunciado=f"Item {numero} de Certo ou Errado.",
            alternativas=dict(ALTERNATIVAS), resposta="c", impressao=f"ce-{numero}",
            evidencia="alvo")
        s.add(q)
        s.flush()
        chave, ident = classificacoes.chave_de(q), q.id
    classificacoes.classificar(chave, INTERPRETACAO, "manual")
    return ident


def test_o_certo_ou_errado_e_uma_rodada_so_com_os_itens_novos(acervo, monkeypatch):
    monkeypatch.setattr(composicao, "reserva_das_que_medem",
                        lambda data, plano=None: composicao.Reserva())
    ce = {_real_de_certo_errado(50), _real_de_certo_errado(51)}
    dia = date(2026, 10, 6)

    resumo = fepese_no_radar.da_faixa([INTERPRETACAO], composicao.Reserva())
    assert (resumo.certo_errado, resumo.certo_errado_novos) == (2, 2)
    rodada = fepese_no_radar.criar_rodada([INTERPRETACAO], 10, dia, so_certo_errado=True)
    assert set(_ids_da_rodada(rodada)) == ce and rodada.filtros["so_certo_errado"]
    assert servico_simulado.corrige_na_hora(rodada)
    for questao_id in ce:
        servico_simulado.responder(rodada.id, questao_id, "c")

    assert fepese_no_radar.criar_rodada([INTERPRETACAO], 10, dia, so_certo_errado=True) is None
    resumo = fepese_no_radar.da_faixa([INTERPRETACAO], composicao.Reserva())
    assert (resumo.certo_errado, resumo.certo_errado_novos) == (2, 0)

    # O treino real tambem nao repete: feitas todas do tema, nao ha rodada.
    todas = fepese_no_radar.criar_rodada([INTERPRETACAO], 30, dia)
    for questao_id in _ids_da_rodada(todas):
        servico_simulado.responder(todas.id, questao_id, "a")
    assert fepese_no_radar.criar_rodada([INTERPRETACAO], 30, dia) is None
    assert fepese_no_radar.da_faixa([INTERPRETACAO], composicao.Reserva()).sugeridas == 0

"""O Certo/Errado so confere o assunto (decisao PMSC-19).

O que estes testes seguram:
  - a transcricao vira questao de duas alternativas, "c" e "e", com o comando
    junto, a materia da faixa da lista, o X anulado e o gabarito conferido;
  - o caderno de Certo/Errado e recusado no acervo complementar, com o motivo
    dito - e por isso fica fora de toda conta, treino e rodada;
  - o pedido de classificacao o leva mesmo recusado, e so ele: outra prova
    recusada continua de fora;
  - a tela "Certo ou Errado" mostra so os itens classificados no tema, com o
    gabarito escondido, e nao grava nada;
  - a faixa so ganha o link quando o tema tem item.
"""
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from radar import complementar as regras
from radar import questoes_certo_errado
from radar.db import sessao
from radar.models import QuestaoDeProva, RespostaDeSimulado, Simulado
from radar.servico import certo_errado, classificacoes, complementar, conteudos
from radar.servico import manual, outras_bancas
from radar.web.app import app
from tests.test_composicao import (CRASE, INTERPRETACAO, ORTOGRAFIA,  # noqa: F401
                                   PORTUGUES, PROGRAMA, RECUSADA, _questao)

PROVA_CE = "https://aocp.test/2022/ppdf-prova.pdf"


def _transcricao(tmp_path, itens):
    caminho = tmp_path / "transcricao.json"
    caminho.write_text(json.dumps({"prova": "teste", "procedencia": "teste", "itens": itens},
                                  ensure_ascii=False), encoding="utf-8")
    return caminho


def _item(numero, gabarito="C", **mais):
    return {"numero": numero, "materia": "Língua Portuguesa",
            "comando": "Julgue os itens a seguir.", "texto_base": None,
            "enunciado": f"Afirmação do item {numero}.", "gabarito": gabarito, **mais}


# --- a leitura -------------------------------------------------------------------

def test_a_transcricao_vira_questao_de_certo_ou_errado(tmp_path):
    caminho = _transcricao(tmp_path, [
        _item(1, "C", texto_base="ELES NÃO APRENDEM"),
        _item(2, "E"),
        _item(3, "X"),
        _item(30, "C"),              # fora do `ler`
        _item(96, "E"),              # a faixa da lista manda na materia
    ])
    lidas = questoes_certo_errado.ler_transcricao(
        caminho, ler=["1-21", "96"],
        materias=[(1, 21, "Língua Portuguesa"), (96, 96, "Direito Penal")])

    assert [q.numero for q in lidas] == [1, 2, 3, 96]
    um, dois, tres, noventa_e_seis = lidas
    assert um.alternativas == {"c": "Certo", "e": "Errado"}
    assert um.resposta == "c" and dois.resposta == "e"
    assert um.enunciado == "Julgue os itens a seguir.\n\nAfirmação do item 1."
    assert um.texto_base == "ELES NÃO APRENDEM" and dois.texto_base is None
    assert tres.anulada and tres.resposta is None
    assert noventa_e_seis.materia == "Direito Penal"
    assert questoes_certo_errado.e_certo_errado(um.alternativas)
    assert not questoes_certo_errado.e_certo_errado({"a": "1", "b": "2", "c": "3", "d": "4"})


def test_o_termo_destacado_vem_da_transcricao(tmp_path):
    caminho = _transcricao(tmp_path, [
        _item(11, enunciado="Em “eles respondem mal a penalizações”, o termo tem o sentido "
                            "de “Mal posso esperar”.", destaques=["mal", "Mal"]),
        _item(12),
    ])
    termos = questoes_certo_errado.termos_da_transcricao(caminho)
    assert set(termos) == {11}
    (lida, _) = questoes_certo_errado.ler_transcricao(caminho)

    marcas = questoes_certo_errado.marcas(lida.enunciado, *termos[11])
    # O comando vem antes e nao e procurado; cada termo, depois do anterior.
    assert [m["trecho"] for m in marcas] == ["mal", "Mal"]
    assert all(lida.enunciado[m["inicio"]:m["fim"]] == m["trecho"] for m in marcas)
    assert {m["tipo"] for m in marcas} == {"sublinhado"}
    # O termo que nao esta no texto fica sem marca.
    assert questoes_certo_errado.marcas(lida.enunciado, termos[11][0], ["inexistente"]) is None


def test_o_gabarito_fora_de_c_e_x_e_recusado(tmp_path):
    caminho = _transcricao(tmp_path, [_item(1, "A")])
    with pytest.raises(ValueError, match="item 1"):
        questoes_certo_errado.ler_transcricao(caminho)


def test_a_lista_com_formato_certo_errado_le_a_transcricao(tmp_path, monkeypatch):
    from radar.servico import provas
    monkeypatch.setattr(provas, "pasta_dos_baixados_a_mao", lambda: tmp_path)
    _transcricao(tmp_path, [_item(1), _item(2, "E")])
    prova = {"formato": "certo_errado", "arquivo_transcrito": "transcricao.json",
             "materias": {"1-2": "Língua Portuguesa"}}

    # O caderno escaneado nem e aberto: sem versao e sem gabarito, a
    # transcricao basta.
    lidas = provas._ler_aocp(tmp_path / "caderno.pdf", prova, None)
    assert [(q.numero, q.resposta, q.materia) for q in lidas] == [
        (1, "c", "Língua Portuguesa"), (2, "e", "Língua Portuguesa")]
    # Sem a transcricao, nada entra.
    assert provas._ler_aocp(tmp_path / "caderno.pdf", {"formato": "certo_errado"}, None) == []


def test_o_caderno_de_certo_errado_e_recusado_com_o_motivo():
    def caderno(letras):
        return regras.Caderno(
            prova_url=PROVA_CE, cargo="Policial Penal", ano=2022, gabarito=regras.DEFINITIVO,
            questoes=[regras.QuestaoDoCaderno(numero=n, materia_no_edital=PORTUGUES,
                                              letras=letras, resposta=letras[0])
                      for n in (1, 2, 3)])

    validacao = regras.validar(caderno(("c", "e")))
    assert validacao.situacao == "recusada"
    assert validacao.motivo == regras.CERTO_ERRADO
    # A multipla escolha de sempre continua validada.
    assert regras.validar(caderno(regras.LETRAS)).situacao == "validada"


# --- o banco, a tela e a faixa -------------------------------------------------------

def _de_certo_errado(numero, caminho=None, *, resposta="c", anulada=False, pendente=False,
                     enunciado=None):
    with sessao() as s:
        q = QuestaoDeProva(
            prova_url=PROVA_CE, banca="Instituto AOCP", ano=2022, numero=numero,
            materia=PORTUGUES,
            enunciado=enunciado or f"Julgue.\n\nItem de Certo/Errado {numero}.",
            alternativas=dict(questoes_certo_errado.ALTERNATIVAS),
            resposta=None if anulada else resposta, anulada=anulada,
            impressao=f"ce-{numero}", evidencia="complementar")
        s.add(q)
        s.flush()
        chave = classificacoes.chave_de(q)
    if caminho:
        classificacoes.classificar(chave, caminho, "manual",
                                   status="pendente" if pendente else None)
    return chave


@pytest.fixture
def acervo(banco_temporario):
    conteudos.semear(programa=PROGRAMA)
    _de_certo_errado(1, INTERPRETACAO, resposta="c")
    _de_certo_errado(2, INTERPRETACAO, resposta="e")
    _de_certo_errado(3, INTERPRETACAO, anulada=True)
    _de_certo_errado(4, INTERPRETACAO, pendente=True)
    _de_certo_errado(5, ORTOGRAFIA)
    # Uma prova recusada de multipla escolha: nunca e classificada.
    _questao(9, PORTUGUES, ORTOGRAFIA, RECUSADA, evidencia="complementar")
    complementar.caminho_do_registro().write_text(json.dumps(
        {"provas": [{"prova_url": PROVA_CE, "aceita": False, "motivo": regras.CERTO_ERRADO},
                    {"prova_url": RECUSADA, "aceita": False}]}), encoding="utf-8")


def test_o_certo_errado_fica_fora_do_acervo_e_do_treino(acervo):
    assert PROVA_CE not in complementar.provas_aceitas()
    assert PROVA_CE not in complementar.provas_dos_padroes()
    assert outras_bancas.estoque([INTERPRETACAO]) == []


def test_o_pedido_de_classificacao_leva_o_certo_errado_recusado(acervo):
    # O caso longo: a afirmacao que se julga vem no fim, depois dos 600
    # caracteres do corte do exemplo de estilo.
    nova = _de_certo_errado(6, enunciado="Julgue.\n\n" + "Contexto do caso. " * 50
                            + "Nesse caso, a conduta é atípica.")
    with sessao() as s:
        recusada = classificacoes.chave_de(s.scalars(
            select(QuestaoDeProva).where(QuestaoDeProva.numero == 9)).one())

    lote = manual.pedido_de_classificacao(None, "complementar")
    pedidas = {chave for p in lote["pedidos"] for chave in p["questoes"].values()}
    assert nova in pedidas
    assert recusada not in pedidas
    assert any("Nesse caso, a conduta é atípica." in p["pedido"] for p in lote["pedidos"])


def test_a_tela_mostra_so_os_itens_do_tema_e_nao_grava_nada(acervo):
    resposta = TestClient(app).get("/certo-errado",
                                   params={"no": INTERPRETACAO, "titulo": "Interpretação 1"})

    assert resposta.status_code == 200
    html = resposta.text
    assert "Certo ou Errado · Interpretação 1" in html
    assert "Item de Certo/Errado 1." in html and "Item de Certo/Errado 2." in html
    # A anulada, a pendente e a de outro no nao aparecem.
    for fora in ("Item de Certo/Errado 3.", "Item de Certo/Errado 4.", "Item de Certo/Errado 5."):
        assert fora not in html
    assert html.count("Ver o gabarito") == 2
    assert "<b>Certo</b>" in html and "<b>Errado</b>" in html
    with sessao() as s:
        assert s.scalar(select(func.count()).select_from(RespostaDeSimulado)) == 0
        assert s.scalar(select(func.count()).select_from(Simulado)) == 0


def test_a_tela_sem_no_conhecido_nao_mostra_nada(acervo):
    html = TestClient(app).get("/certo-errado", params={"no": "Nó que não existe"}).text
    assert "ainda não tem item de Certo/Errado" in html


def test_a_faixa_so_ganha_o_link_com_item(acervo):
    def faixa(*nos):
        return SimpleNamespace(sem_no=False, nos=[SimpleNamespace(no=n) for n in nos])

    assert certo_errado.das_faixas({
        ("noite", 0): faixa(PORTUGUES),
        ("noite", 1): faixa(CRASE),
        ("noite", 2): SimpleNamespace(sem_no=True, nos=[]),
    }) == {("noite", 0): 3}

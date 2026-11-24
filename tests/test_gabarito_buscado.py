"""O gabarito que o Claude Code buscou, e o "verificar a questao" (decisao PMSC-27).

O que estes testes seguram:
  - a questao do script sem o gabarito do site entra com o gabarito do
    `data/gabaritos_buscados.json`, com a nota de onde ele veio e o link; a do
    site fica com o dela, mesmo que o arquivo traga outra letra;
  - o arquivo recusa o que nao da para auditar (letra fora de a-e, sem
    procedencia, o Qconcursos e o TEC como fonte);
  - depois da conferencia do Gabriel, o aviso some;
  - a questao a conferir sem link so treina: a resposta a ela fica fora do
    acerto acumulado e da evolucao; com o link, mede;
  - a tela avisa "Verificar a questao" antes da resposta, sem dizer de onde
    veio a letra, e depois mostra a fonte.
"""
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from radar import config, servico
from radar.db import sessao
from radar.models import Classificacao, QuestaoDeProva
from radar.servico import conteudos, metricas
from radar.servico import questoes_do_qconcursos as qc
from radar.web.app import app
from tests.test_composicao import PROGRAMA
from tests.test_correcao_na_hora import _ids, _rodada
from tests.test_questoes_do_qconcursos import QUESTOES, URL, _banco_do_script
from tests.test_simulado import _questao

PROCEDENCIA = "Claude Code (claude-opus-5-5), 03/11/2026"
LINK = "https://example.org/gabarito-definitivo.pdf"


def _gabaritos(caminho, questoes: dict):
    caminho.write_text(json.dumps({"questoes": questoes}, ensure_ascii=False),
                       encoding="utf-8")
    return caminho


def _buscado(resposta, como="lei", fonte="CP, art. 312", link=None, **mais):
    return {"resposta": resposta, "como": como, "fonte": fonte, "link": link,
            "procedencia": PROCEDENCIA, **mais}


@pytest.fixture
def script(tmp_path, banco_temporario):
    conteudos.semear(programa=PROGRAMA)
    return _banco_do_script(tmp_path / "questoes.db", QUESTOES)


def _gravadas():
    with sessao() as s:
        return {q.numero: q for q in s.scalars(select(QuestaoDeProva).where(
            QuestaoDeProva.prova_url.startswith(qc.PREFIXO)))}


def test_a_questao_sem_o_gabarito_do_site_entra_com_o_buscado(script, tmp_path):
    arquivo = _gabaritos(tmp_path / "gabaritos.json", {
        # 102: a resposta provavel da IA era C; o Claude Code achou A, pela lei.
        "102": _buscado("A", palpite_do_script="c"),
        # 103: sem gabarito; achado na internet, com a pagina.
        "103": _buscado("d", como="internet", fonte="gabarito definitivo", link=LINK),
        # 100 tem o gabarito do site (B): o buscado nao passa por cima.
        "100": _buscado("e"),
    })

    triagem = qc.importar(script, aplicar=True, gabaritos=arquivo)

    # A 108 entra aqui porque este banco nao tem o caderno oficial dela.
    assert sorted(q.id_fonte for q in triagem.entram) == ["100", "101", "102", "103", "108"]
    gravadas = _gravadas()
    assert gravadas[102].resposta == "a"
    assert gravadas[102].gabarito_a_conferir == f"{PROCEDENCIA}, pela lei: CP, art. 312"
    assert gravadas[102].gabarito_link is None
    assert gravadas[103].resposta == "d"
    assert gravadas[103].gabarito_a_conferir.endswith("na internet: gabarito definitivo")
    assert gravadas[103].gabarito_link == LINK
    assert (gravadas[100].resposta, gravadas[100].gabarito_a_conferir) == ("b", None)
    assert metricas.so_treina(gravadas[102])
    assert not metricas.so_treina(gravadas[103])
    assert not metricas.so_treina(gravadas[100])


def test_conferido_pelo_gabriel_o_aviso_some(script, tmp_path):
    arquivo = tmp_path / "gabaritos.json"
    qc.importar(script, aplicar=True, gabaritos=_gabaritos(arquivo, {"102": _buscado("a")}))
    assert _gravadas()[102].gabarito_a_conferir

    qc.importar(script, aplicar=True, gabaritos=_gabaritos(
        arquivo, {"102": _buscado("a", conferido_em="2026-11-10")}))

    q = _gravadas()[102]
    assert (q.resposta, q.gabarito_a_conferir) == ("a", None)
    assert not metricas.so_treina(q)


@pytest.mark.parametrize("item, problema", [
    (_buscado("f"), "não é de a a e"),
    (_buscado("a", como="palpite"), "'como' tem de ser"),
    ({**_buscado("a"), "procedencia": ""}, "procedência"),
    (_buscado("a", como="internet", link="https://www.qconcursos.com/questoes/1"),
     "não servem de fonte"),
    (_buscado("a", como="internet", link="www.site.com/gabarito"), "não é um endereço"),
])
def test_o_arquivo_recusa_o_que_nao_da_para_auditar(tmp_path, item, problema):
    arquivo = _gabaritos(tmp_path / "gabaritos.json", {"102": item})

    with pytest.raises(ValueError, match=problema):
        qc.carregar_gabaritos(arquivo)


def test_sem_arquivo_nenhum_gabarito(tmp_path):
    assert qc.carregar_gabaritos(tmp_path / "nao_existe.json") == {}


def test_o_arquivo_versionado_passa_na_conferencia():
    # O arquivo de verdade: nenhum gabarito sem procedencia, sem fonte, ou
    # tirado do Qconcursos ou do TEC.
    arquivo = config.RAIZ / "data" / "gabaritos_buscados.json"
    if not arquivo.exists():
        pytest.skip("ainda sem gabaritos buscados")
    assert qc.carregar_gabaritos(arquivo)


# --- o destaque do site -------------------------------------------------------------

SUBLINHADO = '<span style="text-decoration-line: underline;" class="q-text-decoration-underline">'


def _de_portugues(enunciado, html, alternativas):
    return qc.DoScript(id_fonte="9", url=URL.format("9"), materia="Português", banca="FGV",
                       orgao="X", prova="", ano=2024, enunciado=enunciado,
                       enunciado_html=html, alternativas=alternativas, gabarito="A")


def test_o_sublinhado_do_site_vira_o_destaque_da_questao():
    q = _de_portugues(
        "Assinale a alternativa em que a expressão destacada tem o mesmo sentido que em "
        "“justamente por contrariar experiências”.",
        '<span style="font-weight: bold;">Assinale a alternativa em que a expressão '
        'destacada tem o mesmo sentido que em “justamente ' + SUBLINHADO + 'por</span> '
        'contrariar experiências”.</span>',
        [{"letra": "A", "texto": "uma ferramenta adquirida pela humanidade",
          "html": "uma ferramenta adquirida " + SUBLINHADO + "pela</span>\nhumanidade"},
         {"letra": "B", "texto": "acompanhados pela impossibilidade",
          "html": "acompanhados <u>pela</u> impossibilidade"},
         {"letra": "C", "texto": "sem marca", "html": "sem marca"},
         {"letra": "D", "texto": "outra", "html": "outra"}])

    marcas = {(m["campo"], m["tipo"], m["trecho"]) for m in qc.destaques_do_html(q)}

    # O negrito do enunciado inteiro e enfeite do site, e fica de fora.
    assert marcas == {("enunciado", "sublinhado", "por"), ("a", "sublinhado", "pela"),
                      ("b", "sublinhado", "pela")}
    assert qc.pede_destaque(q)
    assert qc.motivo_de_fora(q, set(), grupos=(qc.DO_SITE,)) is None


def test_sem_a_marca_a_questao_de_destaque_fica_fora():
    sem_marca = [{"letra": letra, "texto": f"opção {letra}", "html": f"opção {letra}"}
                 for letra in "ABCD"]
    q = _de_portugues("O termo destacado exerce a função de", "O termo destacado exerce a função de",
                      sem_marca)

    assert qc.motivo_de_fora(q, set(), grupos=(qc.DO_SITE,)) == qc.DESTAQUE_PERDIDO
    # No Direito a palavra nao depende da marca.
    q.materia = "Direito Penal"
    assert qc.motivo_de_fora(q, set(), grupos=(qc.DO_SITE,)) is None


def test_classificar_de_novo_nao_regrava_a_que_nao_mudou(script):
    from tests.test_composicao import ORTOGRAFIA
    from tests.test_questoes_do_qconcursos import _mapa

    triagem = qc.importar(script, aplicar=True)
    mapa = _mapa({"1:10": (ORTOGRAFIA, qc.PASSOU)})
    qc.classificar_pelo_link(triagem.entram, mapa)
    with sessao() as s:
        antes = {c.chave: c.classificada_em for c in s.scalars(select(Classificacao))}

    assert qc.classificar_pelo_link(triagem.entram, mapa)["conferida"] == len(antes)
    with sessao() as s:
        depois = {c.chave: c.classificada_em for c in s.scalars(select(Classificacao))}
    assert depois == antes


def test_o_assunto_de_um_lote_novo_leva_a_procedencia_dele(script):
    from tests.test_composicao import CRASE, ORTOGRAFIA
    from tests.test_questoes_do_qconcursos import _do_script

    mapa = qc.Mapa(procedencia="lote 1", assuntos={
        "1:10": qc.AssuntoDoSite(no=ORTOGRAFIA, amostra=qc.PASSOU),
        "1:11": qc.AssuntoDoSite(no=CRASE, amostra=qc.PASSOU, procedencia="lote 2")},
        questoes={"3": qc.DaAmostra(no=CRASE, procedencia="lote 2, amostra")})
    antiga, nova, da_amostra = (_do_script("1", ["1:10"]), _do_script("2", ["1:10", "1:11"]),
                                _do_script("3", ["1:10"]))

    assert mapa.procedencia_de(antiga) == "lote 1"
    assert mapa.procedencia_de(nova) == "lote 2"
    assert mapa.procedencia_de(da_amostra) == "lote 2, amostra"
    qc.classificar_pelo_link([antiga, nova, da_amostra], mapa)
    with sessao() as s:
        procedencias = {c.procedencia for c in s.scalars(select(Classificacao))}
    assert procedencias == {"lote 1", "lote 2", "lote 2, amostra"}


# --- a conta e a tela ------------------------------------------------------------

A_CONFERIR = f"{PROCEDENCIA}, pela lei: CP, art. 312"


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


def test_a_que_so_treina_fica_fora_do_acerto_e_a_com_link_mede(cliente):
    rodada = _rodada(
        _questao(1),
        _questao(2, impressao="i2", gabarito_a_conferir=A_CONFERIR),
        _questao(3, impressao="i3", gabarito_a_conferir=A_CONFERIR, gabarito_link=LINK))
    for questao_id in _ids(rodada):
        cliente.post(f"/simulado/{rodada}/responder",
                     data={"questao_id": questao_id, "letra": "c"})

    # As tres acertadas; so a 2 (sem link) fica fora.
    assert (metricas.acumulado().respondidas, metricas.acumulado().acertos) == (2, 2)
    assert metricas.evolucao().respondidas == 2
    with sessao() as s:
        assert len(metricas.respostas_reais(s)) == 3
        assert len(metricas.respostas_reais(s, so_as_que_medem=True)) == 2


def test_a_tela_avisa_antes_sem_entregar_e_depois_mostra_a_fonte(cliente):
    rodada = _rodada(_questao(1, gabarito_a_conferir=A_CONFERIR),
                     _questao(2, impressao="i2"))
    primeira, segunda = _ids(rodada)

    antes = cliente.get(f"/simulado/{rodada}").text
    assert "Verificar a questão" in antes
    assert "Só treina" in antes
    assert "CP, art. 312" not in antes

    cliente.post(f"/simulado/{rodada}/responder", data={"questao_id": primeira, "letra": "a"})
    depois = cliente.get(f"/simulado/{rodada}?ver={primeira}").text
    assert "Verificar a questão" in depois
    assert "CP, art. 312" in depois
    assert "✓ gabarito a verificar" in depois

    # A questao de gabarito certo nao tem aviso.
    cliente.post(f"/simulado/{rodada}/responder", data={"questao_id": segunda, "letra": "a"})
    assert "Verificar a questão" not in cliente.get(f"/simulado/{rodada}?ver={segunda}").text


def test_no_relatorio_o_gabarito_buscado_leva_o_selo_da_ia(banco_temporario):
    item = servico.simulado.ItemDeRevisao(
        enunciado="?", escolhida="a", correta="c", texto_escolhido="",
        texto_correto="", acertou=False, gabarito_a_conferir=A_CONFERIR)

    assert item.origem_da_resposta == "ia"
    assert servico.simulado.ItemDeRevisao(
        enunciado="?", escolhida="a", correta="c", texto_escolhido="",
        texto_correto="", acertou=False).origem_da_resposta == "oficial"


def test_so_treina_olha_o_aviso_e_o_link():
    assert not metricas.so_treina(SimpleNamespace())
    assert metricas.so_treina(SimpleNamespace(gabarito_a_conferir="x", gabarito_link=None))
    assert not metricas.so_treina(SimpleNamespace(gabarito_a_conferir="x", gabarito_link=LINK))

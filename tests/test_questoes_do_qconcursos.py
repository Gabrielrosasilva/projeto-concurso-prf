"""As questoes do Qconcursos que o script do Gabriel coletou (decisao PMSC-26).

O que estes testes seguram:
  - a triagem: so entra o gabarito do proprio site; ficam fora a resposta
    provavel da IA e a sem gabarito, o Certo/Errado, a escrita pelo site, a com
    imagem, o Portugues de texto e a que o radar ja tem pelo caderno;
  - a gravacao: o link do site no `prova_url`, o numero Q no `numero`, a letra
    minuscula, a AOCP com o nome do radar, e rodar de novo nao duplica;
  - a da banca do alvo entra no acervo (complementar aceito, nos padroes) e
    nunca na conta de quanto cai, e o levantamento dos cadernos nao a ve;
  - a classificacao pelo link: o no do assunto do site, o no em comum de dois
    assuntos, a pendente do contradito e a conferida do assunto que passou.

O banco do script e montado aqui, num arquivo temporario: nenhum teste le a
pasta vltool/ de verdade. Os testes rodam com o config/ da raiz (a banca do
alvo e a FEPESE), e por isso a "banca do alvo" daqui e a FEPESE.
"""
import json
import sqlite3

import pytest
from sqlalchemy import select
from typer.testing import CliRunner

from radar import incidencia as regra
from radar.cli import app as cli
from radar.db import sessao
from radar.models import Classificacao, QuestaoDeProva
from radar.servico import classificacoes, conteudos
from radar.servico import complementar as acervo
from radar.servico import incidencia as servico_incidencia
from radar.servico import questoes_do_qconcursos as qc
from tests.test_composicao import ORTOGRAFIA, PORTUGUES, PROGRAMA, CRASE

URL = qc.PREFIXO + "{}-ab"
CINCO = [{"letra": letra, "texto": f"opção {letra.lower()}", "html": f"opção {letra.lower()}"}
         for letra in "ABCDE"]


def _banco_do_script(caminho, questoes):
    """O banco como o script do Gabriel o grava (so as colunas que o radar le)."""
    conexao = sqlite3.connect(caminho)
    conexao.execute("""CREATE TABLE questoes (
        id INTEGER PRIMARY KEY, fonte TEXT, id_fonte TEXT, url TEXT, materia TEXT,
        assunto TEXT, subassunto TEXT, banca TEXT, orgao TEXT, prova TEXT, ano INTEGER,
        enunciado TEXT, enunciado_html TEXT, alternativas_json TEXT, gabarito TEXT,
        gabarito_observacao TEXT)""")
    conexao.execute("""CREATE TABLE questoes_assuntos (
        discipline_id INTEGER, subject_id INTEGER, questao_id INTEGER)""")
    for i, q in enumerate(questoes, start=1):
        conexao.execute(
            "INSERT INTO questoes VALUES (?, 'qconcursos', ?, ?, ?, '', '', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (i, q["id"], URL.format(q["id"]), q.get("materia", PORTUGUES), q.get("banca", "FGV"),
             q.get("orgao", "PC-XX"), q.get("prova", f"FGV - 2024 - PC-XX - Agente {q['id']} 2024"),
             q.get("ano", 2024), q["enunciado"], q.get("html", q["enunciado"]),
             json.dumps(q.get("alternativas", CINCO), ensure_ascii=False),
             q.get("gabarito", "B"), q.get("observacao", "")))
        for assunto in q.get("assuntos", ["1:10"]):
            disciplina, numero = assunto.split(":")
            conexao.execute("INSERT INTO questoes_assuntos VALUES (?, ?, ?)",
                            (int(disciplina), int(numero), i))
    conexao.commit()
    conexao.close()
    return caminho


QUESTOES = [
    {"id": "100", "enunciado": "Assinale a grafia correta do vocábulo."},
    {"id": "101", "enunciado": "Assinale a forma correta do verbo.", "banca": "FEPESE",
     "orgao": "Câmara de Sapucaia - RJ",
     "prova": "FEPESE - 2024 - Câmara de Sapucaia - RJ - Procurador Jurídico 2024"},
    {"id": "102", "enunciado": "Pergunta com a resposta provável da IA.", "gabarito": "C",
     "observacao": "Resposta provável sugerida pela análise do enunciado, sem confirmação externa"},
    {"id": "103", "enunciado": "Pergunta ainda sem gabarito.", "gabarito": ""},
    {"id": "104", "enunciado": "Julgue o item.", "gabarito": "CERTO",
     "alternativas": [{"letra": "C", "texto": "Certo"}, {"letra": "E", "texto": "Errado"}]},
    {"id": "105", "enunciado": "Pergunta escrita pelo site.", "banca": "Qconcursos"},
    {"id": "106", "enunciado": "Observe a figura.", "html": 'Observe <img src="x.png">'},
    {"id": "107", "enunciado": "No segundo parágrafo do texto, o termo destacado é"},
    {"id": "108", "enunciado": "A mesma questão do caderno oficial."},
]


@pytest.fixture
def script(tmp_path, banco_temporario):
    conteudos.semear(programa=PROGRAMA)
    # A 108 o radar ja tem, lida de um caderno.
    with sessao() as s:
        s.add(QuestaoDeProva(
            prova_url="https://fepese.test/ap2019.pdf", banca="FEPESE", ano=2019, numero=1,
            materia=PORTUGUES, enunciado="A mesma questão do caderno oficial.",
            alternativas={c["letra"].lower(): c["texto"] for c in CINCO}, resposta="b",
            impressao="x", evidencia="alvo"))
    return _banco_do_script(tmp_path / "questoes.db", QUESTOES)


def test_a_triagem_so_deixa_o_gabarito_do_site(script):
    triagem = qc.importar(script)

    assert [q.id_fonte for q in triagem.entram] == ["100", "101"]
    motivos = {q.id_fonte: motivo for q, motivo in triagem.fora}
    assert motivos == {
        "102": qc.GABARITO_NAO_CONFIRMADO, "103": qc.GABARITO_NAO_CONFIRMADO,
        "104": qc.CERTO_ERRADO, "105": qc.AUTORIA_DO_SITE, "106": qc.IMAGEM,
        "107": qc.PORTUGUES_DE_TEXTO, "108": qc.JA_NO_RADAR}
    # Sem --aplicar, nada no radar.
    with sessao() as s:
        assert s.scalar(select(QuestaoDeProva).where(
            QuestaoDeProva.prova_url.startswith(qc.PREFIXO))) is None


def test_o_cargo_sai_do_nome_da_prova_mesmo_com_hifen_e_banca_abreviada():
    def questao(banca, orgao, prova):
        return qc.DoScript(id_fonte="1", url="", materia="", banca=banca, orgao=orgao,
                           prova=prova, ano=2024, enunciado="", enunciado_html="",
                           alternativas=[], gabarito="A")

    assert qc.cargo_do_radar(questao(
        "INSTITUTO AOCP", "PC-ES", "INSTITUTO AOCP - 2024 - PC-ES - Escrivão de Polícia 2024")
    ) == "PC-ES - Escrivão de Polícia"
    assert qc.cargo_do_radar(questao(
        "Fundação FAPEC", "Câmara de X - RJ", "FAPEC - 2024 - Câmara de X - RJ - Procurador")
    ) == "Câmara de X - RJ - Procurador"
    assert qc.cargo_do_radar(questao("INSTITUTO AOCP", "UFRB", "")) == "UFRB"
    assert qc.banca_do_radar("INSTITUTO AOCP") == "Instituto AOCP"
    assert qc.banca_do_radar("FGV") == "FGV"


def test_a_gravacao_guarda_o_link_e_o_numero_q_e_nao_duplica(script):
    qc.importar(script, aplicar=True)
    qc.importar(script, aplicar=True)

    with sessao() as s:
        gravadas = {q.numero: q for q in s.scalars(select(QuestaoDeProva).where(
            QuestaoDeProva.prova_url.startswith(qc.PREFIXO)))}
    assert sorted(gravadas) == [100, 101]
    q = gravadas[100]
    assert q.prova_url == URL.format("100")
    assert q.alternativas == {"a": "opção a", "b": "opção b", "c": "opção c",
                              "d": "opção d", "e": "opção e"}
    assert q.resposta == "b"
    assert q.cargo == "PC-XX - Agente 100"
    # A banca do alvo (a FEPESE, no config dos testes) e complementar; as
    # outras, fora - a regra unica do servico/evidencia.py.
    assert q.evidencia == "fora"
    assert gravadas[101].evidencia == "complementar"
    assert gravadas[101].cargo == "Câmara de Sapucaia - RJ - Procurador Jurídico"


def test_a_da_banca_do_alvo_entra_no_acervo_e_nunca_na_conta_de_quanto_cai(script):
    qc.importar(script, aplicar=True)
    da_banca = URL.format("101")
    with sessao() as s:
        q = s.scalar(select(QuestaoDeProva).where(QuestaoDeProva.prova_url == da_banca))
        chave = classificacoes.chave_de(q)
    classificacoes.classificar(chave, ORTOGRAFIA, "manual")

    assert da_banca in acervo.provas_aceitas()
    assert da_banca in acervo.provas_dos_padroes()
    # O levantamento dos cadernos nao a ve: ela nao veio de caderno.
    assert all(c.prova_url != da_banca for c in acervo.cadernos())

    ocorrencias = servico_incidencia.ocorrencias_complementares()
    [o] = [o for o in ocorrencias if o.prova == da_banca]
    assert o.prova_do_qconcursos == "FEPESE 2024 Câmara de Sapucaia - RJ - Procurador Jurídico"
    linhas = servico_incidencia.linhas_complementares(ocorrencias)
    assert linhas[ORTOGRAFIA].questoes == 0
    assert regra.complementar_do_escopo(
        ORTOGRAFIA, lambda c: c == ORTOGRAFIA, ocorrencias).questoes == 0


def test_nos_padroes_duas_questoes_do_mesmo_concurso_sao_uma_prova():
    def ocorrencia(numero, prova_do_qconcursos):
        return regra.Ocorrencia(
            prova=URL.format(numero), ano=2024, materia=PORTUGUES, conteudo=ORTOGRAFIA,
            status="completa", enunciado=f"Questão {numero}?", resposta="a",
            impressao=f"chave-{numero}", alternativas={"a": "um", "b": "dois"},
            prova_do_qconcursos=prova_do_qconcursos)

    minimos = regra.Minimos(questoes=3, provas=2)
    mesmo_concurso = [ocorrencia(n, "FEPESE 2024 PC-XX - Agente") for n in (1, 2, 3)]
    assert not regra.padroes_complementares(ORTOGRAFIA, mesmo_concurso, minimos).suficiente
    dois_concursos = mesmo_concurso + [ocorrencia(4, "FEPESE 2023 PC-YY - Agente")]
    assert regra.padroes_complementares(ORTOGRAFIA, dois_concursos, minimos).suficiente


def _mapa(assuntos, questoes=None):
    return qc.Mapa(procedencia="mapa de teste",
                   assuntos={chave: qc.AssuntoDoSite(no=no, amostra=amostra)
                             for chave, (no, amostra) in assuntos.items()},
                   questoes=questoes or {})


def _do_script(id_fonte, assuntos):
    return qc.DoScript(id_fonte=id_fonte, url=URL.format(id_fonte), materia=PORTUGUES,
                       banca="FGV", orgao="PC-XX", prova="", ano=2024,
                       enunciado=f"Questão {id_fonte}?", enunciado_html="",
                       alternativas=CINCO, gabarito="A", assuntos=assuntos)


def test_o_no_vem_do_assunto_do_site_e_dois_assuntos_dao_o_no_em_comum(banco_temporario):
    conteudos.semear(programa=PROGRAMA)
    mapa = _mapa({"1:10": (ORTOGRAFIA, qc.PASSOU),
                  "1:11": (ORTOGRAFIA + " > Acentuação", qc.PASSOU),
                  "1:12": (CRASE, qc.PASSOU)})

    assert qc.no_pelo_link(_do_script("1", ["1:10"]), mapa) == ORTOGRAFIA
    assert qc.no_pelo_link(_do_script("2", ["1:10", "1:11"]), mapa) == ORTOGRAFIA
    # Assuntos diferentes: sem no em comum abaixo da materia, pendente.
    assert qc.no_pelo_link(_do_script("3", ["1:10", "1:12"]), mapa) is None
    assert qc.no_pelo_link(_do_script("4", ["9:99"]), mapa) is None


def test_a_amostra_decide_se_a_questao_vem_conferida_ou_pendente(banco_temporario):
    conteudos.semear(programa=PROGRAMA)
    mapa = _mapa({"1:10": (ORTOGRAFIA, qc.PASSOU),
                  "1:11": (CRASE, qc.SEM_CONFIRMACAO),
                  "1:12": (CRASE, qc.CONTRADITO)},
                 # A 5 nenhum no serve; a 6 a leitura as cegas confirmou noutro
                 # no; a 7 so o desempate leu, e fica sem conferencia.
                 questoes={"5": qc.DaAmostra(no=None),
                           "6": qc.DaAmostra(no=CRASE),
                           "7": qc.DaAmostra(no=CRASE, conferida=False)})
    questoes = [_do_script("1", ["1:10"]), _do_script("2", ["1:11"]),
                _do_script("3", ["1:12"]), _do_script("5", ["1:10"]),
                _do_script("6", ["1:10"]), _do_script("7", ["1:10"])]

    contagem = qc.classificar_pelo_link(questoes, mapa)

    assert contagem == {"conferida": 2, "sem conferência": 2, "pendente": 2}
    with sessao() as s:
        por_chave = {c.chave: c for c in s.scalars(select(Classificacao))}
    leituras = {q.id_fonte: qc.ler_pelo_link(q, mapa) for q in questoes}
    conferida = por_chave[leituras["1"].chave]
    assert (conferida.conteudo, conferida.conferida_por) == (ORTOGRAFIA, qc.CONFERIDA_PELA_AMOSTRA)
    assert conferida.procedencia == "mapa de teste"
    sem = por_chave[leituras["2"].chave]
    assert (sem.conteudo, sem.conferida_em) == (CRASE, None)
    da_amostra = por_chave[leituras["6"].chave]
    assert (da_amostra.conteudo, da_amostra.conferida_por) == (CRASE, qc.CONFERIDA_NA_AMOSTRA)
    desempatada = por_chave[leituras["7"].chave]
    assert (desempatada.conteudo, desempatada.conferida_em) == (CRASE, None)
    for pendente in ("3", "5"):
        c = por_chave[leituras[pendente].chave]
        assert (c.status, c.conteudo) == ("pendente", PORTUGUES)


def test_a_materia_sozinha_e_pendente_e_a_fora_do_treino_nao_volta(banco_temporario):
    conteudos.semear(programa=PROGRAMA)
    mapa = _mapa({"1:10": (PORTUGUES, qc.PASSOU), "1:11": (ORTOGRAFIA, qc.PASSOU)})
    na_materia, revogada = _do_script("1", ["1:10"]), _do_script("2", ["1:11"])

    assert qc.classificar_pelo_link([na_materia, revogada], mapa) == {
        "pendente": 1, "conferida": 1}
    chave = qc.ler_pelo_link(revogada, mapa).chave
    classificacoes.fora_do_treino(chave, "manual", "a lei mudou")

    assert qc.classificar_pelo_link([na_materia, revogada], mapa)["fora do treino"] == 1
    with sessao() as s:
        c = s.scalar(select(Classificacao).where(Classificacao.chave == chave)
                     .where(Classificacao.principal.is_(True)))
    assert (c.status, c.conteudo) == ("pendente", PORTUGUES)


def test_o_mapa_le_o_caminho_do_arquivo(tmp_path):
    # A chave e `caminho`: no YAML, a chave `no` viraria o booleano falso, e
    # toda questao sairia pendente (aconteceu na primeira rodada, 02/11).
    arquivo = tmp_path / "qconcursos_nos.yml"
    arquivo.write_text(
        'procedencia: "mapa"\n'
        'assuntos:\n'
        '  "1:10":\n    nome: "1 Ortografia"\n    caminho: "' + ORTOGRAFIA + '"\n'
        '    amostra: "passou"\n'
        'questoes:\n'
        '  "5":\n    caminho: null\n    conferida: false\n'
        '  "6":\n    caminho: "' + CRASE + '"\n    conferida: true\n', encoding="utf-8")

    mapa = qc.carregar_mapa(arquivo)

    assert mapa.assuntos["1:10"] == qc.AssuntoDoSite(no=ORTOGRAFIA, amostra=qc.PASSOU)
    assert mapa.questoes == {"5": qc.DaAmostra(no=None, conferida=False),
                             "6": qc.DaAmostra(no=CRASE, conferida=True)}


def test_o_comando_mostra_a_triagem_sem_gravar(script):
    resultado = CliRunner().invoke(cli, ["questoes-do-qconcursos", "--banco", str(script)])

    assert resultado.exit_code == 0, resultado.output
    assert "2 questão(ões) entram" in resultado.output
    assert "Nada foi gravado" in resultado.output
    with sessao() as s:
        assert s.scalar(select(QuestaoDeProva).where(
            QuestaoDeProva.prova_url.startswith(qc.PREFIXO))) is None

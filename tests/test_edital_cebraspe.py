"""O programa do edital do Cebraspe vira a arvore de conteudos (Etapa 1 da PRF).

O texto abaixo e INVENTADO, no formato do edital da PRF de 2021 (item 24,
"objetos de avaliacao"), com os defeitos que o edital de verdade tem: o numero
que pula (2 -> 2.2), o ponto esquecido antes do topico, a lista do CONTRAN, a
secao em numero romano, o numero da pagina e a assinatura no meio do texto.
Nada aqui le PDF, banco real ou internet.
"""
import json

from typer.testing import CliRunner

from radar import cli
from radar import conteudos as arvore
from radar import edital_cebraspe as ec
from radar.servico import conteudos

EDITAL = """MINISTÉRIO DO TESTE
EDITAL CONCURSO TESTE Nº 3, DE 5 DE MAIO DE 2020
9.1 A prova objetiva abrangerá os objetos de avaliação constantes do item 24.
24 DOS OBJETOS DE AVALIAÇÃO (HABILIDADES E CONHECIMENTOS)
24.1 HABILIDADES
24.1.1 Os itens das provas poderão avaliar habilidades.
24.2 CONHECIMENTOS
BLOCO I
LÍNGUA TESTE: 1 Leitura de textos variados. 2 Ortografia oficial. 3 Coesão textual.
3.1 Emprego de conectores. 3.2 Emprego de tempos verbais. 4 Correspondência
38
oficial (conforme o Manual). 4.1 Aspectos gerais.
RACIOCÍNIO LÓGICO-MATEMÁTICO: 1 Equações do 1º e 2º graus. 2 Noção de função.
2 .1 Análise gráfica. 2.2 Funções afim e quadrática.
GEOGRAFIA DO PAÍS: 1 O país: nação e território. 2 A divisão inter-
regional do trabalho. 3 Rede de transporte: modais e infraestruturas 4 A integração
econômica. 5 Gestão ambiental.
LÍNGUA ESTRANGEIRA (INGLÊS OU ESPANHOL): I LÍNGUA INGLESA: 1 Compreensão de texto
em inglês. 2 Itens gramaticais. II LÍNGUA ESPANHOLA: 1 Compreensão de texto em
espanhol. 2 Itens gramaticais.
BLOCO II
LEGISLAÇÃO DE TRÂNSITO: 1 Lei nº 9.503/1997 e suas alterações. 2 Resoluções do
CONTRAN e suas alterações: 04/1998; 14/1998; 92/1998, exceto os anexos; 810/2020.
BLOCO III
DIREITO PENAL: 1 Princípios básicos. 2 Aplicação da lei penal. 2.2 Lei penal no
tempo. 2.2.1 Tempo do crime. 2.2.2 Conflito de leis. 3 Crimes.
LEGISLAÇÃO ESPECIAL: 1 Lei nº 5.553/1968. 2 Decreto nº 1.655/1995 e art. 47 do
Decreto nº 9.662/2019. 3 Lei nº 13.869/2019.

FULANO DE TAL
DIRETOR-GERAL DO ÓRGÃO DE TESTE
ANEXO I
CRONOGRAMA PREVISTO
"""

PROCEDENCIA = "EDITAL CONCURSO TESTE Nº 3, DE 5 DE MAIO DE 2020, item 24"


def _materias():
    return {m.nome: m for m in ec.ler_programa(EDITAL)}


def _textos(topicos):
    return [(t.numero, t.texto) for t in topicos]


# --- ler o programa -----------------------------------------------------------

def test_as_materias_saem_na_ordem_do_edital_com_o_bloco():
    materias = ec.ler_programa(EDITAL)
    assert [(m.bloco, m.nome) for m in materias] == [
        ("BLOCO I", "Língua Teste"),
        ("BLOCO I", "Raciocínio Lógico-Matemático"),
        ("BLOCO I", "Geografia do País"),
        ("BLOCO I", "Língua Estrangeira (Inglês ou Espanhol)"),
        ("BLOCO II", "Legislação de Trânsito"),
        ("BLOCO III", "Direito Penal"),
        ("BLOCO III", "Legislação Especial"),
    ]
    assert materias[1].nome_no_edital == "RACIOCÍNIO LÓGICO-MATEMÁTICO"


def test_o_nome_da_materia_sai_da_caixa_alta():
    assert ec.nome_da_materia("ÉTICA E CIDADANIA") == "Ética e Cidadania"
    assert ec.nome_da_materia("LEGISLAÇÃO  DE TRÂNSITO ") == "Legislação de Trânsito"
    assert ec.nome_da_materia("RACIOCÍNIO LÓGICO-MATEMÁTICO") == "Raciocínio Lógico-Matemático"


def test_os_topicos_tem_o_numero_e_o_texto_do_edital():
    lingua = _materias()["Língua Teste"]
    assert _textos(lingua.topicos) == [
        ("1", "Leitura de textos variados."),
        ("2", "Ortografia oficial."),
        ("3", "Coesão textual."),
        ("4", "Correspondência oficial (conforme o Manual)."),   # sem o "38" da pagina
    ]
    assert _textos(lingua.topicos[2].filhos) == [
        ("3.1", "Emprego de conectores."), ("3.2", "Emprego de tempos verbais.")]
    # "2 .1" e defeito de extracao: volta a ser o 2.1.
    funcao = _materias()["Raciocínio Lógico-Matemático"].topicos[1]
    assert [t.numero for t in funcao.filhos] == ["2.1", "2.2"]


def test_numero_no_meio_da_frase_nao_vira_topico():
    especial = _materias()["Legislação Especial"]
    assert _textos(especial.topicos) == [
        ("1", "Lei nº 5.553/1968."),
        ("2", "Decreto nº 1.655/1995 e art. 47 do Decreto nº 9.662/2019."),
        ("3", "Lei nº 13.869/2019."),
    ]
    assert _materias()["Raciocínio Lógico-Matemático"].topicos[0].texto == \
        "Equações do 1º e 2º graus."


def test_o_numero_que_pula_e_o_ponto_esquecido():
    penal = _materias()["Direito Penal"]
    # O edital vai do 2 direto ao 2.2: o texto e o dele, e o 2.2 e filho do 2.
    assert _textos(penal.topicos[1].filhos) == [("2.2", "Lei penal no tempo.")]
    assert [t.numero for t in penal.topicos[1].filhos[0].filhos] == ["2.2.1", "2.2.2"]
    # Sem o ponto antes, o 4 so e topico porque e exatamente o seguinte do 3.
    geografia = _materias()["Geografia do País"]
    assert [t.numero for t in geografia.topicos] == ["1", "2", "3", "4", "5"]
    assert geografia.topicos[2].texto == "Rede de transporte: modais e infraestruturas"


def test_o_hifen_no_fim_da_linha_e_da_palavra():
    geografia = _materias()["Geografia do País"]
    assert geografia.topicos[1].texto == "A divisão inter-regional do trabalho."


def test_a_lista_depois_do_dois_pontos_vira_filhos():
    resolucoes = _materias()["Legislação de Trânsito"].topicos[1]
    assert [t.texto for t in resolucoes.filhos] == [
        "04/1998", "14/1998", "92/1998, exceto os anexos", "810/2020"]
    assert all(t.numero == "" for t in resolucoes.filhos)


def test_a_secao_em_numero_romano_tem_os_topicos_dela():
    estrangeira = _materias()["Língua Estrangeira (Inglês ou Espanhol)"]
    assert _textos(estrangeira.topicos) == [("I", "LÍNGUA INGLESA"), ("II", "LÍNGUA ESPANHOLA")]
    assert _textos(estrangeira.topicos[1].filhos) == [
        ("1", "Compreensão de texto em espanhol."), ("2", "Itens gramaticais.")]


def test_a_assinatura_e_o_anexo_ficam_de_fora():
    ultimo = _materias()["Legislação Especial"].topicos[-1]
    assert "FULANO" not in ultimo.texto and "DIRETOR" not in ultimo.texto


def test_a_procedencia_e_a_identificacao_do_edital_e_o_item():
    assert ec.procedencia(EDITAL) == PROCEDENCIA


def test_texto_sem_o_item_do_programa_devolve_vazio():
    # A mencao em minuscula no corpo do edital (subitem 9.1) nao conta.
    assert ec.ler_programa("9.1 A prova abrangerá os objetos de avaliação do item 24.") == []


# --- os nos da arvore ---------------------------------------------------------

def _nos(taxonomia=None):
    return {no.caminho: no for no in ec.nos_da_arvore(ec.ler_programa(EDITAL), PROCEDENCIA,
                                                       taxonomia)}


def test_materia_assunto_e_subassunto_com_o_texto_do_edital():
    nos = _nos()
    materia = nos["Língua Teste"]
    assert (materia.nivel, materia.texto_do_edital) == ("materia", "LÍNGUA TESTE")
    assert materia.procedencia == f"{PROCEDENCIA}, BLOCO I"
    assunto = nos["Língua Teste > Coesão textual"]          # sem o ponto final
    assert (assunto.nivel, assunto.pai, assunto.texto_do_edital) == (
        "assunto", "Língua Teste", "3 Coesão textual.")
    sub = nos["Língua Teste > Coesão textual > Emprego de conectores"]
    assert (sub.nivel, sub.origem, sub.ordem) == ("subassunto", "edital", 0)


def test_o_terceiro_nivel_fica_no_texto_do_subassunto():
    nos = _nos()
    tempo = nos["Direito Penal > Aplicação da lei penal > Lei penal no tempo"]
    assert tempo.texto_do_edital == ("2.2 Lei penal no tempo. 2.2.1 Tempo do crime. "
                                     "2.2.2 Conflito de leis.")
    assert not any(no.nivel == "elemento" for no in nos.values())


def test_a_lista_vira_subassunto_e_a_secao_vira_assunto():
    nos = _nos()
    resolucoes = "Legislação de Trânsito > Resoluções do CONTRAN e suas alterações"
    assert nos[resolucoes].texto_do_edital.startswith("2 Resoluções do CONTRAN e suas alterações: 04/1998;")
    assert nos[f"{resolucoes} > 92/1998, exceto os anexos"].nivel == "subassunto"
    inglesa = "Língua Estrangeira (Inglês ou Espanhol) > Língua Inglesa"
    assert (nos[inglesa].nivel, nos[inglesa].texto_do_edital) == ("assunto", "I LÍNGUA INGLESA")
    assert nos[f"{inglesa} > Itens gramaticais"].nivel == "subassunto"


def test_a_materia_fora_do_edital_entra_marcada():
    taxonomia = arvore.Taxonomia(
        familias={}, elementos_comuns=[], tipos_de_questao=[], sinonimos_de_materia={},
        materias_fora_do_edital=[{"nome": "História da Casa", "procedencia": "prova de 2019"},
                                 {"nome": "Direito Penal", "procedencia": "ja esta no edital"}])
    nos = _nos(taxonomia)
    fora = [no for no in nos.values() if no.fora_do_edital]
    assert [(no.nome, no.origem, no.procedencia) for no in fora] == [
        ("História da Casa", "manual", "prova de 2019")]


# --- gravar no banco e o comando ----------------------------------------------

def test_semear_nos_grava_escreve_o_json_e_nao_duplica(banco_temporario, tmp_path):
    nos = ec.nos_da_arvore(ec.ler_programa(EDITAL), PROCEDENCIA)
    assert conteudos.semear_nos(nos) == len(nos)
    assert conteudos.semear_nos(nos) == 0
    no_arquivo = json.loads((tmp_path / "conteudos.json").read_text(encoding="utf-8"))
    assert len(no_arquivo) == len(nos)
    assert conteudos.caminhos()[0] == "Língua Teste"


def test_o_comando_semeia_pelo_pdf_do_edital(banco_temporario, monkeypatch):
    monkeypatch.setattr(ec, "texto_do_pdf", lambda caminho: EDITAL)
    resultado = CliRunner().invoke(cli.app, ["conteudos", "--semear", "--edital", "edital.pdf"],
                                   env={"COLUMNS": "200"})
    assert resultado.exit_code == 0, resultado.output
    assert "do edital (7 matérias)" in resultado.output
    assert "Legislação de Trânsito > Resoluções do CONTRAN e suas alterações > 810/2020" \
        in conteudos.caminhos()


def test_o_comando_recusa_pdf_sem_programa(banco_temporario, monkeypatch):
    monkeypatch.setattr(ec, "texto_do_pdf", lambda caminho: "um PDF qualquer")
    resultado = CliRunner().invoke(cli.app, ["conteudos", "--semear", "--edital", "x.pdf"],
                                   env={"COLUMNS": "200"})
    assert resultado.exit_code == 1
    assert "Não achei o programa" in resultado.output
    assert conteudos.caminhos() == []

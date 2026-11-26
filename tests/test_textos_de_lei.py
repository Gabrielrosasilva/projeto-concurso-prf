"""O texto da lei que vai no pedido de gerar (decisao PMSC-8).

A fixture e uma lei de mentira no jeito da pagina da ALESC: o artigo revogado
riscado com <s>, o "º" de "§ 1º" dentro de <s> (a LC 587 faz isso), um
paragrafo riscado por estilo e a quebra de linha no meio do paragrafo.
"""
from pathlib import Path

from radar import textos_de_lei

FIXTURE = Path(__file__).parent / "fixtures" / "textos_de_lei" / "lei_ficticia.html"


def _texto():
    return textos_de_lei.texto_plano(FIXTURE.read_text(encoding="utf-8"))


def test_o_riscado_sai_e_o_ordinal_riscado_fica():
    texto = _texto()
    assert "Redação antiga" not in texto
    assert "Parágrafo revogado" not in texto
    assert "§ 1º Salvo o caso do § 2º, o prazo é de trinta dias." in texto
    assert "Art. 2º O ingresso depende de concurso público." in texto


def test_sem_estilo_nem_script_e_o_paragrafo_numa_linha_so():
    texto = _texto()
    assert "nao e texto" not in texto and "MsoNormal" not in texto
    assert "Art. 1º Esta Lei vale para os militares estaduais, na forma do regulamento." in texto.splitlines()


def test_o_intervalo_sai_do_nome_do_no():
    assert textos_de_lei.intervalo("Título I - Da aplicação (arts. 1º a 28)") == ((1, ""), (28, ""))
    assert textos_de_lei.intervalo("CTB arts. 256 a 279-A") == ((256, ""), (279, "A"))
    assert textos_de_lei.intervalo("CTB art. 23") == ((23, ""), (23, ""))
    assert textos_de_lei.intervalo("Título IV - Do concurso (arts. 53 e 54)") == ((53, ""), (54, ""))
    assert textos_de_lei.intervalo("Lei 5.209/1976 - Conselho de Disciplina") is None


def test_o_trecho_vai_do_primeiro_ao_ultimo_artigo_sem_o_titulo_seguinte():
    trecho = textos_de_lei.trecho(_texto(), (1, ""), (3, "A"))
    assert trecho.startswith("Art. 1º Esta Lei")
    assert trecho.endswith("Art. 3º-A A promoção ocorre por antiguidade ou merecimento.")
    assert "TÍTULO II" not in trecho and "Dos deveres" not in trecho
    assert textos_de_lei.trecho(_texto(), (40, ""), (41, "")) is None


def test_do_no_usa_o_item_mais_especifico_e_o_intervalo_do_no(tmp_path):
    (tmp_path / "leis").mkdir()
    (tmp_path / "leis" / "lei.html").write_bytes(FIXTURE.read_bytes())
    lista = tmp_path / "textos_de_lei.yml"
    lista.write_text(
        "textos:\n"
        "  - conteudo: Legislação Institucional\n"
        "    fonte: Outra\n    arquivo: leis/nao_existe.html\n"
        "  - conteudo: Legislação Institucional > Lei 1.234/2000 - Teste\n"
        "    fonte: Lei 1.234/2000\n    url: https://exemplo.org/lei\n    arquivo: leis/lei.html\n",
        encoding="utf-8")
    no = "Legislação Institucional > Lei 1.234/2000 - Teste > Título II - Dos deveres (arts. 4º e 5º)"
    achado = textos_de_lei.do_no(no, lista=lista, raiz=tmp_path)
    assert achado.fonte == "Lei 1.234/2000" and achado.artigos == "arts. 4º e 5º"
    assert achado.texto.startswith("Art. 4º São deveres") and "Art. 1º" not in achado.texto
    inteira = textos_de_lei.do_no("Legislação Institucional > Lei 1.234/2000 - Teste",
                                  lista=lista, raiz=tmp_path)
    assert inteira.artigos == "a lei inteira" and inteira.texto.startswith("LEI Nº 1.234")
    # O item de cima aponta um arquivo que nao existe: nada vai.
    assert textos_de_lei.do_no("Legislação Institucional > Outra lei", lista=lista, raiz=tmp_path) is None
    assert textos_de_lei.do_no("Direito Penal", lista=lista, raiz=tmp_path) is None


def test_o_no_pode_ter_varios_textos_e_o_intervalo_da_lista(tmp_path):
    # PRF-41: o no da CF nao tem intervalo no nome (o `artigos` da lista diz o
    # trecho, e vale antes do nome), e um no pode ter duas normas ou dois trechos.
    (tmp_path / "lei.html").write_bytes(FIXTURE.read_bytes())
    lista = tmp_path / "lista.yml"
    lista.write_text(
        "textos:\n"
        "  - conteudo: Direito Constitucional\n    fonte: Geral\n    arquivo: lei.html\n"
        "  - conteudo: \"Direito Constitucional > Poder Executivo: art. 9\"\n"
        "    fonte: CF\n    arquivo: lei.html\n    artigos: arts. 1º a 2º\n"
        "  - conteudo: \"Direito Constitucional > Poder Executivo: art. 9\"\n"
        "    fonte: Outra lei\n    arquivo: lei.html\n    artigos: a lei inteira\n"
        "  - conteudo: \"Direito Constitucional > Poder Executivo: art. 9\"\n"
        "    fonte: Sem o arquivo\n    arquivo: nao_existe.html\n",
        encoding="utf-8")
    no = "Direito Constitucional > Poder Executivo: art. 9"
    textos = textos_de_lei.todos_do_no(no, lista=lista, raiz=tmp_path)
    assert [(t.fonte, t.artigos) for t in textos] == [("CF", "arts. 1º a 2º"),
                                                      ("Outra lei", "a lei inteira")]
    assert textos[0].texto.startswith("Art. 1º") and "Art. 3º" not in textos[0].texto
    assert textos[1].texto.startswith("LEI Nº 1.234")
    # O primeiro e o que o `do_no` devolve; o item de cima nao entra.
    assert textos_de_lei.do_no(no, lista=lista, raiz=tmp_path).fonte == "CF"
    assert textos_de_lei.todos_do_no("Direito Penal", lista=lista, raiz=tmp_path) == []


def test_o_trecho_maior_que_o_limite_nao_vai(tmp_path, monkeypatch):
    (tmp_path / "lei.html").write_bytes(FIXTURE.read_bytes())
    lista = tmp_path / "lista.yml"
    lista.write_text("textos:\n  - conteudo: Legislação de Trânsito\n    fonte: CTB\n"
                     "    arquivo: lei.html\n", encoding="utf-8")
    monkeypatch.setattr(textos_de_lei, "LIMITE", 50)
    assert textos_de_lei.do_no("Legislação de Trânsito", lista=lista, raiz=tmp_path) is None

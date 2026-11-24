"""O leitor do caderno do Instituto AOCP, a banca da PMSC (decisao PMSC-6).

As fixtures sao texto: o gabarito pos-recursos da PM-ES 2022, o da PM-GO 2022
com o Soldado Musico antes do Combatente, e um trecho das paginas do Tipo 1
do caderno da PM-ES 2022 ja sem o cabecalho (os textos de Portugues cortados
no primeiro paragrafo). A lista do pciconcursos e inventada, com a marca
d'agua falsa: a de verdade traz o endereco de quem baixou.
"""
from pathlib import Path

import pytest

from radar import complementar, questoes_aocp
from radar.servico import provas

PASTA = Path(__file__).parent / "fixtures" / "aocp_provas"


def _ler(nome: str) -> str:
    return (PASTA / nome).read_text(encoding="utf-8")


# --- as paginas do tipo -----------------------------------------------------------

def test_so_entram_as_paginas_do_tipo_da_lista():
    paginas = [
        "capa\nPROVA\n01",
        "PM\nSOLDADO  Tipo  01 – Página 2\n1\nEnunciado",
        "SOLDADO  Tipo  01 – Página 3\n2\nOutro",
        "capa\nPROVA\n02",
        "SOLDADO  Tipo  02 – Página 2\n1\nEnunciado do tipo 2",
    ]
    do_tipo_1 = questoes_aocp.paginas_da_versao(paginas, "TIPO 1")
    assert do_tipo_1 == paginas[1:4]
    assert questoes_aocp.paginas_da_versao(paginas, "TIPO 2") == paginas[4:]
    assert questoes_aocp.paginas_da_versao(paginas, "TIPO 3") == []


def test_o_caderno_com_o_numero_do_tipo_em_branco_tem_uma_versao_so():
    # A Policia Penal PR 2024 (24/10): "Tipo   – Pagina 2", sem o numero.
    paginas = ["capa\nPROVA",
               "POLICIAL PENAL  Tipo   – Página 2\n1\nEnunciado",
               "POLICIAL PENAL  Tipo   – Página 3\n2\nOutro"]
    assert questoes_aocp.paginas_da_versao(paginas, "TIPO 1") == paginas
    # Sem o cabecalho nenhum, continua nada: nao se adivinha a versao.
    assert questoes_aocp.paginas_da_versao(["capa", "1\nEnunciado"], "TIPO 1") == []


# --- o gabarito -------------------------------------------------------------------

def test_o_gabarito_transcrito_de_imagem_vem_do_txt(tmp_path):
    # A SEJUSP-MG 2026 so publicou a tabela em imagem (24/10): quem transcreveu
    # fica antes de "Gabarito", e o X e a anulada.
    txt = tmp_path / "gabarito_transcrito.txt"
    txt.write_text("SEJUSP-MG 2026 - transcrito em 24/10/2026 da imagem do gabarito.\n"
                   "Gabarito\n1 A\n2 D\n58 X\n60 C\n", encoding="utf-8")
    assert questoes_aocp.ler_gabarito(txt, "TIPO 1", None) == {1: "a", 2: "d", 58: None, 60: "c"}


def test_o_gabarito_pos_recursos_tem_um_bloco_por_tipo():
    blocos = questoes_aocp.blocos_do_gabarito(_ler("gabarito_pm_es_2022.txt"))
    cargo = "soldado combatente (qpmp-c)"
    assert sorted(blocos) == [(cargo, f"TIPO {n}") for n in range(1, 5)]
    tipo_1 = blocos[(cargo, "TIPO 1")]
    assert len(tipo_1) == 80
    assert (tipo_1[1], tipo_1[2], tipo_1[80]) == ("d", "c", "e")
    # O X e a anulada: 21, 28 e 60 no Tipo 1, e outras no Tipo 2.
    assert [n for n, letra in tipo_1.items() if letra is None] == [21, 28, 60]
    assert [n for n, letra in blocos[(cargo, "TIPO 2")].items() if letra is None] == [22, 29, 41]


def test_o_bloco_e_o_do_cargo_da_lista_e_nao_o_do_outro_cargo():
    texto = _ler("gabarito_pm_go_2022_dois_cargos.txt")
    combatente = questoes_aocp.respostas_do_gabarito(
        texto, "TIPO 1", "Soldado de 2ª Classe QPPM - Combatente")
    musico = questoes_aocp.respostas_do_gabarito(
        texto, "TIPO 1", "Soldado de 2ª Classe QPM - Músico")
    assert (combatente[16], musico[16]) == ("d", "a")
    assert combatente[41] == "e" and musico[41] is None
    with pytest.raises(ValueError, match="nao tem o bloco"):
        questoes_aocp.respostas_do_gabarito(texto, "TIPO 2", "Soldado de 2ª Classe QPPM - Combatente")


LISTA_DO_PCICONCURSOS = """pcimarkpci MARCA-FALSA
www.pciconcursos.com.br
Questão
Gabarito
1
C
7
X
11
A
11
B
12
C
12
E
57
pcimarkpci MARCA-FALSA
www.pciconcursos.com.br
D
58
A
"""


def test_a_lista_do_pciconcursos_sem_a_marca_dagua_e_sem_a_questao_de_duas_letras():
    respostas = questoes_aocp.respostas_do_gabarito(LISTA_DO_PCICONCURSOS, "TIPO 1", None)
    # O 57 e o D ficam em paginas diferentes, com a marca d'agua no meio.
    assert respostas == {1: "c", 7: None, 57: "d", 58: "a"}
    _, repetidas = questoes_aocp.gabarito_da_lista(LISTA_DO_PCICONCURSOS)
    assert repetidas == {11, 12}


# --- as questoes ------------------------------------------------------------------

@pytest.fixture
def trecho():
    respostas = questoes_aocp.respostas_do_gabarito(
        _ler("gabarito_pm_es_2022.txt"), "TIPO 1", "SOLDADO COMBATENTE (QPMP-C)")
    return questoes_aocp.questoes_do_texto(
        _ler("pm_es_2022_tipo1_trecho.txt"), respostas,
        materias=[(1, 20, "Língua Portuguesa")])


def test_le_as_questoes_com_a_resposta_do_tipo(trecho):
    assert [q.numero for q in trecho] == [1, 2, 12, 13, 14, 80]
    assert [q.resposta for q in trecho] == ["d", "c", "e", "a", "d", "e"]
    primeira = trecho[0]
    assert primeira.enunciado.startswith("Sobre o excerto “Depois de checar os sintomas")
    assert sorted(primeira.alternativas) == list("abcde")
    assert primeira.alternativas["c"] == "A vírgula é facultativa."


def test_a_materia_vem_da_faixa_da_lista(trecho):
    assert {q.numero: q.materia for q in trecho} == {
        1: "Língua Portuguesa", 2: "Língua Portuguesa", 12: "Língua Portuguesa",
        13: "Língua Portuguesa", 14: "Língua Portuguesa", 80: None}


def test_o_texto_de_portugues_vai_para_as_questoes_do_aviso(trecho):
    por_numero = {q.numero: q for q in trecho}
    assert por_numero[1].texto_base.startswith("COMO O DOUTOR GOOGLE")
    assert por_numero[12].texto_base == por_numero[1].texto_base
    assert por_numero[13].texto_base.startswith("CLÍNICA VIRTUAL")
    assert por_numero[80].texto_base is None
    # O paragrafo com recuo abre um paragrafo novo.
    assert "\n\nEm 2012, quando era pesquisador" in por_numero[1].texto_base


def test_o_aviso_do_texto_seguinte_nao_gruda_na_alternativa(trecho):
    doze = next(q for q in trecho if q.numero == 12)
    assert doze.alternativas["e"] == "hiperonímia."


def test_o_bloco_da_materia_seguinte_nao_gruda_na_alternativa():
    goias = ("Realidade étnica, social, histórica,\ngeográfica, cultural, política e\n"
             "econômica do Estado de Goiás\n")
    estrangeira = "Responda somente à Língua Estrangeira de sua preferência e lembre-se de preencher.\n"
    for bloco in (goias, estrangeira):
        caderno = ("10\nAssinale a alternativa que NÃO caracteriza redação oficial.\n"
                   + "".join(f"({l}) Atributo {l}.\n" for l in "ABCD")
                   + "(E) Concisão.\n" + bloco
                   + "11\nTexto qualquer em inglês?\n"
                   + "".join(f"({l}) Option {l}.\n" for l in "ABCDE"))
        dez = questoes_aocp.questoes_do_texto(caderno, {10: "e", 11: "a"}, ler=["10"])[0]
        assert dez.alternativas["e"] == "Concisão."


def test_a_linha_da_marca_dagua_sai_da_pagina():
    marca = _Linha([_Letra(40, 550, "pcimarkpci MARCA-FALSA")])
    texto = _Linha([_Letra(40, 280, "(E) Concisão.")])
    assert questoes_aocp._sem_marca_dagua([marca, texto]) == [texto]


def test_a_redacao_nao_gruda_na_ultima_alternativa(trecho):
    oitenta = trecho[-1]
    assert oitenta.alternativas["e"].endswith("doadas a donatários de confiança da Coroa Portuguesa.")
    assert "Redação" not in oitenta.alternativas["e"]


def test_questao_sem_resposta_no_gabarito_recusa_o_caderno():
    with pytest.raises(ValueError, match=r"nao tem as questoes \[1, 2"):
        questoes_aocp.questoes_do_texto(_ler("pm_es_2022_tipo1_trecho.txt"), {80: "e"})


def test_sem_aviso_o_texto_vem_depois_do_titulo_e_vale_ate_a_materia_seguinte():
    texto_longo = "Missão da Nasa decola rumo ao asteroide Psyche\n" + (
        "A agência espacial americana alça voo para o asteroide.\n" * 10)
    caderno = (
        "Língua Portuguesa\n" + texto_longo
        + "1\nA partir da leitura do texto, assinale a correta.\n"
        + "".join(f"({l}) alternativa {l}.\n" for l in "ABCDE")
        + "2\nAssinale a alternativa correta.\n"
        + "".join(f"({l}) outra {l}.\n" for l in "ABCDE")
        + "História de Pernambuco\n"
        + "3\nA formação de Olinda está relacionada a quem?\n"
        + "".join(f"({l}) nome {l}.\n" for l in "ABCDE"))
    base = questoes_aocp.textos_base(caderno)
    assert sorted(base) == [1, 2]
    assert base[1].startswith("Missão da Nasa decola")


def test_o_hifen_no_fim_da_linha_e_da_palavra():
    # PC-GO 2022, questao 2: a de colocacao pronominal perdia o hifen ("mantêla").
    caderno = ("1\nAssinale a alternativa correta.\n(A) É preciso mantê-\nla saudável.\n"
               + "".join(f"({l}) outra {l}.\n" for l in "BCDE"))
    questao = questoes_aocp.questoes_do_texto(caderno, {1: "a"})[0]
    assert questao.alternativas["a"] == "É preciso mantê-la saudável."


def test_o_aviso_da_pm_df_abre_o_texto_e_sai_dele():
    caderno = ("Responda as questões de 1 a 2 de acordo com o texto a seguir.\n"
               "Polícia e comunidade\n" + "A presença da polícia previne o crime.\n" * 5
               + "1\nSegundo o texto, assinale a correta.\n"
               + "".join(f"({l}) alternativa {l}.\n" for l in "ABCDE")
               + "2\nAssinale a alternativa correta.\n"
               + "".join(f"({l}) outra {l}.\n" for l in "ABCDE"))
    base = questoes_aocp.textos_base(caderno)
    assert sorted(base) == [1, 2]
    assert base[1].startswith("Polícia e comunidade")


# --- as colunas -------------------------------------------------------------------

class _Letra:
    def __init__(self, x0, x1, texto):
        self.x0, self.x1, self.texto = x0, x1, texto

    def get_text(self):
        return self.texto


class _Espaco:
    """O `LTAnno` do pdfminer: o espaco que ele poe, sem posicao."""

    def get_text(self):
        return " "


class _Linha(list):
    def __init__(self, itens, y0=400, y1=410):
        super().__init__(itens)
        self.y0, self.y1 = y0, y1

    def get_text(self):
        return "".join(item.get_text() for item in self)


def test_a_linha_que_cruza_o_meio_da_pagina_e_partida_em_duas_colunas():
    linha = _Linha([_Letra(43, 48, "d"), _Letra(48, 53, "o"), _Espaco(),
                    _Letra(312, 317, "p"), _Letra(317, 322, "e")])
    assert questoes_aocp._pedacos_por_coluna(linha, 297) == [(0, 43, "do "), (1, 312, "pe")]


def test_a_pagina_com_letra_em_cima_do_meio_e_de_uma_coluna_so():
    cheia = [_Linha([_Letra(280, 300, "x")], y0=400 - 20 * n, y1=410 - 20 * n) for n in range(3)]
    duas_colunas = [_Linha([_Letra(43, 280, "x"), _Espaco(), _Letra(312, 550, "y")])] * 5
    assert questoes_aocp._uma_coluna(cheia, 595, 842)
    assert not questoes_aocp._uma_coluna(duas_colunas, 595, 842)


# --- o caminho das outras bancas e o acervo complementar ----------------------------

def test_a_aocp_tem_leitor_e_sem_versao_nada_entra(tmp_path):
    leitor = provas.LEITORES_DE_OUTRAS_BANCAS["INSTITUTO AOCP"]
    assert leitor(tmp_path / "caderno.pdf", {"banca": "Instituto AOCP"}, tmp_path / "g.pdf") == []


def _caderno(numeros, letras_das_questoes=complementar.LETRAS, **campos):
    return complementar.Caderno(
        prova_url="https://exemplo.org/caderno", cargo="Policial Penal", ano=2026,
        gabarito=complementar.DEFINITIVO, questoes=[
            complementar.QuestaoDoCaderno(numero=n, materia_no_edital="Língua Portuguesa",
                                          letras=letras_das_questoes, resposta="a")
            for n in numeros], **campos)


def test_o_caderno_de_quatro_alternativas_passa_quando_a_lista_diz():
    quatro = complementar.LETRAS[:4]
    sem_a_lista = complementar.validar(_caderno(range(1, 4), letras_das_questoes=quatro))
    assert "alternativas diferentes de a-e" in sem_a_lista.motivo
    com_a_lista = _caderno(range(1, 4), letras_das_questoes=quatro, letras=quatro)
    assert complementar.validar(com_a_lista).pode_classificar
    # E o caderno de 4 recusa a questao que veio com 5.
    misturado = _caderno(range(1, 4), letras=quatro)
    assert "alternativas diferentes de a-d" in complementar.validar(misturado).motivo


def test_a_numeracao_e_conferida_dentro_do_ler_da_lista():
    lidas = [1, 2, 3, 6, 7]
    assert not complementar.validar(_caderno(lidas)).pode_classificar
    assert complementar.validar(_caderno(lidas, ler=["1-3", "6-7"])).pode_classificar
    faltando = complementar.validar(_caderno([1, 2, 6, 7], ler=["1-3", "6-7"]))
    assert "falta 3" in faltando.motivo

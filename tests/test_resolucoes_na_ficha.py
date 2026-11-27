"""A resolucao do CONTRAN na ficha (PRF-47).

O que estes testes seguram: a resolucao do CONTRAN e lida como norma, do jeito
que o resumo a escreve ("Res. CONTRAN 945/2022", "Res. 955/2022", "Resolução
CONTRAN nº 508/2014"), e a de outro orgao nao; o numero de dentro da
resolucao nao vira outra lei; os blocos de "Os artigos" saem agrupados por
norma, com o titulo que a traducao da; e a traducao aceita o "comece por
aqui" e o titulo das normas, com as mesmas travas das outras partes.
"""
import copy

import pytest

from radar import artigos, fichas, traducao

TRANSITO = "Legislação de Trânsito"
R945, R955 = "Res. CONTRAN 945/2022", "Res. CONTRAN 955/2022"
DO_TEMA = artigos.do_tema(
    "Resoluções do CONTRAN: cargas", f"{R945}, arts. 1º a 6º; Res. 955/2022, arts. 2º a 10; "
    "CTB, art. 108", TRANSITO)
CODIGOS = {"2021-q85": "e"}


@pytest.mark.parametrize("fonte, rotulo", [
    ("Res. CONTRAN 945/2022, art. 4º, §§ 3º e 5º", "Res. CONTRAN 945/2022, art. 4º"),
    ("Res. 955/2022, art. 10", "Res. CONTRAN 955/2022, art. 10"),
    ("Resolução CONTRAN nº 508/2014, art. 5º, I", "Res. CONTRAN 508/2014, art. 5º"),
    ("Resolução do CONTRAN 508/2014, art. 2º", "Res. CONTRAN 508/2014, art. 2º"),
    # Da milesima em diante, com o ponto ou sem: a mesma sigla, com o ponto.
    ("Res. CONTRAN 1.027/2026, art. 5º", "Res. CONTRAN 1.027/2026, art. 5º"),
    ("Resolução CONTRAN nº 1027/2026, art. 5º", "Res. CONTRAN 1.027/2026, art. 5º"),
])
def test_a_resolucao_do_contran_e_norma(fonte, rotulo):
    assert artigos.da_fonte(fonte).rotulo == rotulo


def test_a_resolucao_de_outro_orgao_nao_e_lida():
    assert artigos.citados("Res. CNJ 213/2015, art. 1º") == []


def test_o_numero_de_dentro_da_resolucao_nao_vira_outra_lei():
    # "801/2022" e um dos nomes da LC 801/2022 de SC (copia da PMSC).
    assert artigos.da_fonte("Res. CONTRAN 801/2022, art. 2º").lei == "Res. CONTRAN 801/2022"


@pytest.mark.parametrize("texto, numeros", [
    ("Res. CONTRAN 918/2022: arts. 2º, 3º, § 5º, 4º e 21", ["2º", "3º", "4º", "21"]),
    ("CTB, arts. 257, §§ 7º e 8º, 259, 282, § 6º, e 284", ["257", "259", "282", "284"]),
    ("Res. CONTRAN 723/2018, arts. 7º, §§ 3º e 4º, 10, §§ 1º e 5º, 17-A",
     ["7º", "10", "17-A"]),
])
def test_o_paragrafo_no_meio_da_lista_nao_acaba_a_lista(texto, numeros):
    assert [f.rotulo.rsplit(" ", 1)[1] for f in artigos.citados(texto)] == numeros


def test_a_faixa_da_resolucao_vem_do_ler_exatamente():
    rotulos = [f.rotulo for f in DO_TEMA]
    assert f"{R945}, arts. 1º a 6º" in rotulos
    assert f"{R955}, arts. 2º a 10" in rotulos
    assert "CTB, art. 108" in rotulos


def _frase(texto, fonte):
    return {"texto": texto, "fontes": [fonte]}


PARTES = {
    "dominar": [{"texto": "Visão geral das duas resoluções.",
                 "fontes": [f"{R945}, art. 4º", f"{R955}, art. 10"]}],
    "artigos": [_frase("Fator de segurança de 2 vezes o peso.", f"{R945}, art. 4º"),
                _frase("Por dentro das guardas laterais.", f"{R945}, art. 6º"),
                _frase("A bicicleta é carga indivisível.", f"{R955}, art. 10")],
}


def test_a_frase_de_um_artigo_da_resolucao_vira_bloco():
    enxuto = fichas.resumo_enxuto(PARTES, TRANSITO)
    assert [b.rotulo for b in enxuto.blocos] == [
        f"{R945}, art. 4º", f"{R945}, art. 6º", f"{R955}, art. 10"]
    # A de duas normas fica no "dominar", como a de dois artigos.
    assert [f.texto for f in enxuto.dominar] == ["Visão geral das duas resoluções."]


def test_os_blocos_saem_agrupados_por_norma_com_o_titulo_da_traducao():
    enxuto = fichas.resumo_enxuto(PARTES, TRANSITO, {
        "normas": [{"norma": R945, "do_que_trata": "amarração de cargas"}]})
    grupos = [(titulo, [b.rotulo_curto for b in blocos]) for titulo, blocos in enxuto.por_norma]
    assert grupos == [(f"{R945}: amarração de cargas", ["art. 4º", "art. 6º"]),
                      (R955, ["art. 10"])]


def test_o_comece_por_aqui_vai_para_o_topo_do_resumo():
    comece = [_frase("Primeiro a amarração, depois a bicicleta.", f"{R945}, art. 1º")]
    enxuto = fichas.resumo_enxuto(PARTES, TRANSITO, {"comece_por_aqui": comece})
    assert [f.texto for f in enxuto.comece] == ["Primeiro a amarração, depois a bicicleta."]
    assert enxuto.traduzido


# --- a traducao com o "comece por aqui" e as normas ----------------------------------------

def _linha(texto, *fontes):
    return {"texto": texto, "fontes": list(fontes)}


BOA = {
    "comece_por_aqui": [_linha("A 945 é a amarração: comece por ela.", f"{R945}, art. 1º"),
                        _linha("A 955 é a carga por fora; caiu na 2021-q85 (gabarito E).",
                               f"{R955}, art. 2º", "2021-q85 (gabarito E)")],
    "normas": [{"norma": R945, "do_que_trata": "amarração de cargas"},
               {"norma": "CTB", "do_que_trata": "passageiro em veículo de carga"}],
    "itens": [{"artigo": f"{R945}, art. 4º",
               "na_real": _linha("A cinta aguenta o dobro do peso.", f"{R945}, art. 4º"),
               "exemplo": _linha("Faltou ponto, prende no chassi.", f"{R945}, art. 4º, § 5º"),
               "na_prova": _linha("2 vezes, e não 1,5.", f"{R945}, art. 4º",
                                  "2021-q85 (gabarito E)")}],
}


def _conferir(bruto):
    return traducao.conferir_traducao(bruto, tema=DO_TEMA, codigos=CODIGOS)


def test_a_traducao_com_o_comece_e_as_normas_passa():
    partes, _ = _conferir(copy.deepcopy(BOA))
    assert len(partes["comece_por_aqui"]) == 2
    assert partes["normas"][0] == {"norma": R945, "do_que_trata": "amarração de cargas"}
    assert partes["itens"][0]["artigo"] == f"{R945}, art. 4º"


def test_a_traducao_sem_o_comece_e_sem_as_normas_continua_valendo():
    bruto = copy.deepcopy(BOA)
    del bruto["comece_por_aqui"], bruto["normas"]
    partes, _ = _conferir(bruto)
    assert partes["comece_por_aqui"] == [] and partes["normas"] == []


@pytest.mark.parametrize("mudar, motivo", [
    (lambda b: b["comece_por_aqui"].append(_linha("Fora do tema.", "CTB, art. 109")),
     "não é do tema"),
    (lambda b: b["comece_por_aqui"].append(_linha("Sem fonte nenhuma aqui.")), "sem fonte"),
    (lambda b: b["comece_por_aqui"].extend(
        [_linha("Linha a mais no mapa.", f"{R945}, art. 1º")] * 4), "no máximo 5"),
    (lambda b: b["normas"].append({"norma": "Res. CONTRAN 882/2021", "do_que_trata": "pesos"}),
     "não é norma do tema"),
    (lambda b: b["normas"].append({"norma": R955, "do_que_trata": ""}), "sem o do_que_trata"),
    (lambda b: b["comece_por_aqui"].append(_linha("Isso vai cair na prova.", f"{R945}, art. 1º")),
     "previsão"),
])
def test_o_comece_e_as_normas_sao_recusados(mudar, motivo):
    bruto = copy.deepcopy(BOA)
    mudar(bruto)
    with pytest.raises(fichas.FichaRecusada, match=motivo):
        _conferir(bruto)


# --- a sigla do glossario so casa em caixa alta (PRF-49) -----------------------------------

def test_a_sigla_do_glossario_nao_marca_a_palavra_comum():
    from radar import glossario

    na = {"termo": "NA", "variantes": [], "significado": "Notificação de autuação.",
          "fontes": ["Res. CONTRAN 918/2022, art. 2º"]}
    marcados = [t.texto for t in glossario.trechos("Identificado na hora, recebe a NA.",
                                                   [na], set()) if t.termo]
    assert marcados == ["NA"]


def test_o_termo_comum_continua_sem_caixa():
    from radar import glossario

    tara = {"termo": "tara", "variantes": [], "significado": "O peso do veículo vazio.",
            "fontes": ["Res. CONTRAN 882/2021, art. 3º"]}
    marcados = [t.texto for t in glossario.trechos("A Tara do caminhão.", [tara], set())
                if t.termo]
    assert marcados == ["Tara"]


# --- as leis das outras materias e o bloco por inciso (PRF-52) ----------------------------

@pytest.mark.parametrize("fonte, rotulo", [
    ("Lei 8.112/1990, art. 116, III", "Lei 8.112/1990, art. 116"),
    ("Lei 14.133/2021, art. 75, II", "Lei 14.133/2021, art. 75"),
    ("Decreto-Lei 200/1967, art. 4º, II", "Decreto-Lei 200/1967, art. 4º"),
    ("ADCT, art. 2º", "ADCT, art. 2º"),
    ("CADH, art. 7º", "Convenção Americana, art. 7º"),
    # O Anexo I numera de novo: nao e o art. 2º do decreto.
    ("Decreto 11.348/2023, Anexo I, art. 2º", "Decreto 11.348/2023, Anexo I, art. 2º"),
    ("Decreto 11.348/2023, art. 1º", "Decreto 11.348/2023, art. 1º"),
])
def test_as_leis_das_outras_materias_sao_lidas(fonte, rotulo):
    assert artigos.da_fonte(fonte).rotulo == rotulo


@pytest.mark.parametrize("fonte, rotulo", [
    ("CF, art. 5º, XI", "CF, art. 5º, XI"),
    ("CF, art. 5º, inciso LXVIII", "CF, art. 5º, LXVIII"),
    ("CF, art. 7º, XXXIII", "CF, art. 7º, XXXIII"),
    # Varios incisos, faixa, paragrafo ou caput: o bloco do artigo.
    ("CF, art. 5º, XI e XII", "CF, art. 5º"),
    ("CF, art. 5º, incisos XI a XIII", "CF, art. 5º"),
    ("CF, art. 5º, § 3º", "CF, art. 5º"),
    ("CF, art. 5º, caput", "CF, art. 5º"),
    # Fora de POR_INCISO, o inciso nao separa.
    ("CF, art. 37, II", "CF, art. 37"),
])
def test_no_artigo_longo_o_bloco_e_o_inciso(fonte, rotulo):
    assert artigos.da_fonte(fonte).rotulo == rotulo


def test_os_blocos_de_inciso_saem_na_ordem_da_lei():
    partes = {"artigos": [_frase("Mandado de segurança.", "CF, art. 5º, LXIX"),
                          _frase("Casa é asilo inviolável.", "CF, art. 5º, XI"),
                          _frase("Todos são iguais.", "CF, art. 5º, caput"),
                          _frase("Habeas corpus.", "CF, art. 5º, LXVIII")]}
    enxuto = fichas.resumo_enxuto(partes, "Direito Constitucional")
    assert [b.rotulo for b in enxuto.blocos] == [
        "CF, art. 5º", "CF, art. 5º, XI", "CF, art. 5º, LXVIII", "CF, art. 5º, LXIX"]


def test_a_traducao_do_inciso_cita_o_proprio_inciso():
    tema = artigos.do_tema("Direitos e deveres (art. 5º)", "CF, art. 5º", "Direito Constitucional")
    item = {"artigo": "CF, art. 5º, XI",
            "na_real": _linha("A casa é protegida.", "CF, art. 5º, XI"),
            "exemplo": _linha("Mandado só de dia.", "CF, art. 5º, XI"),
            "na_prova": _linha("De dia, com ordem do juiz.", "CF, art. 5º, XI")}
    partes, _ = traducao.conferir_traducao({"itens": [item]}, tema=tema, codigos={})
    assert partes["itens"][0]["artigo"] == "CF, art. 5º, XI"
    # O "na real" que cita o artigo inteiro nao e o proprio inciso.
    errado = copy.deepcopy(item)
    errado["na_real"] = _linha("A casa é protegida.", "CF, art. 5º")
    with pytest.raises(fichas.FichaRecusada, match="não é o próprio artigo"):
        traducao.conferir_traducao({"itens": [errado]}, tema=tema, codigos={})


def test_a_resolucao_de_outro_orgao_escrito_depois_nao_e_do_contran():
    # "Resolução 5/2012 do Senado": os artigos depois dela sao da Lei 11.343.
    texto = ("Lei 11.343/2006 (a Resolução 5/2012 do Senado suspendeu a vedação), "
             "arts. 3º a 17")
    assert [f.rotulo for f in artigos.citados(texto)] == ["Lei 11.343/2006, arts. 3º a 17"]


def test_a_lei_nomeada_depois_da_citacao_e_so_dela():
    # "do art. 144 da CF" nao faz o art. 121-A, que vem depois, ser da CF.
    texto = "CP: art. 121 (protege os agentes do art. 144 da CF) e art. 121-A; 3) art. 129"
    assert [f.rotulo for f in artigos.citados(texto)] == [
        "CP, art. 121", "CF, art. 144", "CP, art. 121-A", "CP, art. 129"]


@pytest.mark.parametrize("fonte, rotulo", [
    ("CF, art. 144, § 2º", "CF, art. 144, § 2º"),
    ("CF, art. 144, § 10", "CF, art. 144, § 10"),
    ("CF, art. 144, §§ 1º e 2º", "CF, art. 144"),
    ("CF, art. 144, caput, II", "CF, art. 144"),
])
def test_o_art_144_se_divide_por_paragrafo(fonte, rotulo):
    # O § 2º e a PRF: o bloco dele e a traducao dele.
    assert artigos.da_fonte(fonte).rotulo == rotulo


def test_o_paragrafo_com_letra_e_outro_paragrafo():
    assert artigos.da_fonte("CF, art. 144, § 5º-A").rotulo == "CF, art. 144, § 5º-A"


def test_a_traducao_do_artigo_inteiro_puxa_os_paragrafos_sem_traducao():
    # A ficha de antes traduzia o art. 144 de uma vez: as frases dos §§ ficam
    # no bloco dele, com a letra, e nao em blocos soltos sem traducao.
    partes = {"artigos": [_frase("Policias militares.", "CF, art. 144, § 5º"),
                          _frase("Policias penais.", "CF, art. 144, § 5º-A")]}
    item = {"artigo": "CF, art. 144", "na_real": _linha("Os orgaos.", "CF, art. 144"),
            "exemplo": _linha("A PM.", "CF, art. 144"), "na_prova": _linha("PP.", "CF, art. 144")}
    enxuto = fichas.resumo_enxuto(partes, "Direito Constitucional", {"itens": [item]})
    assert [(b.rotulo, len(b.frases), bool(b.traducao)) for b in enxuto.blocos] == [
        ("CF, art. 144", 2, True)]

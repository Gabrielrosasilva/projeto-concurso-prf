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
])
def test_a_resolucao_do_contran_e_norma(fonte, rotulo):
    assert artigos.da_fonte(fonte).rotulo == rotulo


def test_a_resolucao_de_outro_orgao_nao_e_lida():
    assert artigos.citados("Res. CNJ 213/2015, art. 1º") == []


def test_o_numero_de_dentro_da_resolucao_nao_vira_outra_lei():
    # "801/2022" e um dos nomes da LC 801/2022 de SC (copia da PMSC).
    assert artigos.da_fonte("Res. CONTRAN 801/2022, art. 2º").lei == "Res. CONTRAN 801/2022"


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

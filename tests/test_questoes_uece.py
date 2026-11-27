"""O leitor do caderno da UECE-CEV (DETRAN/CE 2018, PRF-68): as duas colunas
do modo layout, o cabecalho, o bloco do gabarito e a divisao em questoes.
Texto fixo, como o pypdf o entrega - sem PDF e sem internet."""
from radar import questoes_por_rodada
from radar import questoes_uece as uece

# Uma pagina de questao no modo layout: o cabecalho de ponta a ponta, a linha
# do numero do gabarito com a pagina, e duas colunas (a da direita com a
# alternativa recuada, que comeca em outra posicao).
PAGINA = """GOVERNO DO ESTADO DO CEARÁ – UNIVERSIDADE ESTADUAL D O CEARÁ – COMISSÃO EXECUTIVA DO VESTIBULAR
CONCURSO  PÚBLICO  DE  PROVAS  E  TÍTULOS  E  DE  PROVAS  PARA  CARGOS  EFETIVOS COM  LOTAÇÃO
LOCALIZADAS EM FORTALEZA E NO INTERIOR DO ESTADO DO CEARÁ – PROVA OBJETIVA REALIZADA EM 2018
O número do gabarito deste caderno de prova é 1.                                     Página 12

52.    São exemplos de medidas administrativas:                              55.    O infrator será submetido a curso de
A)   transbordo do excesso de carga e recolhimento                                 reciclagem quando se envolver em acidente
     da Carteira Nacional de Habilitação.                                          grave,
B)   retenção do veículo e multa.                                            A)    para o qual haja contribuído, dependendo do
C)   remoção do veículo e suspensão do direito de                                  resultado do processo judicial.
     dirigir.                                                                B)    ainda que não haja contribuído,
D)   frequência obrigatória em curso de reciclagem.                                independentemente de processo judicial.
                                                                             C)    para o qual haja contribuído,
53.    Compete às Juntas Administrativas de Recursos                               independentemente de processo judicial.
de Infração                                                                  D)    ainda que não haja contribuído, dependendo do
A)   organizar o Registro Nacional.                                                resultado do processo judicial.
B)   proceder à supervisão.
C)   apurar a infração.
D)   julgar os recursos interpostos pelos infratores.
"""

GABARITO = """VISTORIADOR
      GABARITO 1
51 52 53 54 55
B A D B C

GABARITO 2
51 52 53 54 55
A B A C D
"""


def test_o_cabecalho_sai_e_o_numero_do_gabarito_e_lido():
    assert uece.numero_do_gabarito(" ".join(PAGINA.split())) == 1
    limpa = uece.limpar(PAGINA)
    assert "GOVERNO" not in limpa and "LOCALIZADAS" not in limpa
    assert "número do gabarito" not in limpa and "Página" not in limpa


def test_as_duas_colunas_viram_uma_a_esquerda_antes_da_direita():
    texto = uece.em_uma_coluna(uece.limpar(PAGINA))
    assert texto.index("52.") < texto.index("53.") < texto.index("55.")
    # A alternativa recuada da direita nao fica cortada nem vai para a esquerda.
    assert "ainda que não haja contribuído, dependendo do" in texto


def test_a_pagina_de_uma_coluna_fica_como_esta():
    capa = "PROVA OBJETIVA PARA O CARGO DE\nVISTORIADOR\nDATA DA APLICAÇÃO: 25 DE FEVEREIRO DE 2018\n"
    assert uece.em_uma_coluna(capa) == capa


def test_o_gabarito_le_so_o_bloco_do_caderno():
    assert uece.ler_gabarito(GABARITO, 1) == {51: "b", 52: "a", 53: "d", 54: "b", 55: "c"}
    assert uece.ler_gabarito(GABARITO, 2)[52] == "b"
    assert uece.ler_gabarito(GABARITO, 3) == {}


def test_a_divisao_em_questoes_com_a_letra_do_gabarito():
    texto = questoes_por_rodada.sem_cabecalho([uece.em_uma_coluna(uece.limpar(PAGINA))])
    questoes = {q.numero: q for q in questoes_por_rodada.dividir_em_questoes(
        texto, uece.ler_gabarito(GABARITO, 1), marca="ponto", alternativa="fecha", letras="ABCD")}
    assert set(questoes) == {52, 53, 55}
    assert questoes[52].enunciado == "São exemplos de medidas administrativas:"
    assert questoes[52].resposta == "a"
    assert questoes[53].alternativas["d"] == "julgar os recursos interpostos pelos infratores."
    assert questoes[55].resposta == "c"
    assert questoes[55].alternativas["b"] == "ainda que não haja contribuído, independentemente de processo judicial."

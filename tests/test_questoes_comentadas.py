"""O leitor da prova comentada (FCC DETRAN/SP 2019 da Estrategia, PRF-70):
so o texto antes do "Comentário:", a letra do quadro final conferida com a da
questao, e o que fica de fora. Texto fixo, como o pypdf o entrega."""
from radar import questoes_comentadas as qc

PAGINA_1 = """

   2
29
CTB E RESOLUÇÕES – PROVA AGENTE DE TRÂNSITO (PROVA TIPO I)
21.  [FCC – AGENTE ESTADUAL DE TRÂNSITO – DETRAN/SP - 2019]
Ao condutor que se evadir da fiscalização, não submetendo veículo à
pesagem obrigatória, será aplicada a seguinte penalidade:
(A) multa e apreensão do veículo.
(B) multa, apenas.
(C) apreensão do veículo e suspensão
do direito de dirigir.
(D) multa e suspensão do direito de dirigir.
(E) apreensão do veículo.
Comentário:
O art. 278 remete ao art. 209:
(A) isto parece alternativa, mas e o comentario.
Gabarito: B
22. [FCC – AGENTE ESTADUAL DE TRÂNSITO – DETRAN/SP - 2019]
Transitar com farol desregulado constitui em:

Comentário:
As alternativas estavam em imagem.
Gabarito: C
"""

PAGINA_2 = """
   3
29
23. [FCC – AGENTE ESTADUAL DE TRÂNSITO – DETRAN/SP - 2019]
A JARI terá necessariamente
(A) quatro integrantes.
(B) dois integrantes.
(C) um integrante.
(D) cinco integrantes.
(E) seis integrantes.
Comentário:
Questão polêmica.
Gabarito: E
24. [FCC – AGENTE ESTADUAL DE TRÂNSITO – DETRAN/SP - 2019]
Pergunta com letra que nao bate.
(A) a.
(B) b.
(C) c.
(D) d.
(E) e.
Comentário:
...
Gabarito: A
"""

QUADRO = """
   29
29
GABARITO
21 22 23 24
B C E** D

** - Anulável
"""

TEXTO = "\n".join(qc.sem_numero_da_pagina(p) for p in (PAGINA_1, PAGINA_2, QUADRO))


def test_o_numero_da_pagina_sai_do_topo():
    assert qc.sem_numero_da_pagina(PAGINA_2).startswith("23. [FCC")


def test_o_quadro_final_e_a_anulavel():
    assert qc.ler_quadro(TEXTO) == {21: "b", 22: "c", 23: None, 24: "d"}


def test_so_entra_o_texto_antes_do_comentario():
    questoes = {q.numero: q for q in qc.dividir(TEXTO, qc.ler_quadro(TEXTO))}
    q21 = questoes[21]
    assert q21.resposta == "b"
    assert q21.enunciado.startswith("Ao condutor que se evadir")
    # A alternativa que quebra a linha vira uma so; a "(A)" do comentario nao entra.
    assert q21.alternativas["c"] == "apreensão do veículo e suspensão do direito de dirigir."
    assert q21.alternativas["a"] == "multa e apreensão do veículo."


def test_fica_de_fora_sem_alternativas_anulavel_e_letra_que_nao_bate():
    # 22: alternativas em imagem; 23: "E**" anulavel; 24: quadro D, questao A.
    assert [q.numero for q in qc.dividir(TEXTO, qc.ler_quadro(TEXTO))] == [21]

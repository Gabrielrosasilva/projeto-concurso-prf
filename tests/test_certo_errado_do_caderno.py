"""O caderno de Certo/Errado do Cebraspe lido direto do PDF (Etapa 2 da PRF).

O caderno abaixo e INVENTADO, no formato que o pypdf devolve das provas da
PRF de 2019 e 2021, com os defeitos de verdade: o cabecalho da pagina, o
"BLOCO", o "Espaço livre", a palavra partida pelo texto justificado, o texto
com rotulo, a situacao, o comando em duas linhas, o item de figura e o item
anulado. Nada aqui le PDF, banco ou internet.
"""
import pytest

from radar import questoes_certo_errado as ce

CADERNO = """CEBRASPE – TESTE – Edital: 2020
Nas questões a seguir, marque, para cada item, C caso julgue o item CERTO.
BLOCO I
Texto 1A1-I
  O farol da ilha acende quando a tarde cai, e os ba rcos voltam
devagar para o porto.
  Ninguém sabe quem acendeu o farol pela primeira vez.
Fulano. Revista de Teste, 2019.
Com relação às ideias do texto 1A1-I precedente, julgue os itens a
seguir.
1 O farol acende de manhã.
2 Os barcos voltam devagar para o porto, segundo o
texto.
Considerando os sentidos do texto 1A1-I, julgue o item que se segue.
3 A palavra “farol” poderia ser substituída por lanterna.
Espaço livre

CEBRASPE – TESTE – Edital: 2020
  Em uma operação, foram fiscalizados 20 veículos na primeira hora e
40 na segunda.
Considerando essa situação hipotética, julgue os itens seguintes.
4 Foram fiscalizados 60 veículos nas duas horas.
5 Na segunda hora foi fiscalizado o dobro da primeira.
       Figura 1A2-I
A partir da figura precedente, julgue o item a seguir.
6
BLOCO II
No que se refere ao Siste ma Nacional de Trânsito, julgue os
itens a seguir.
7 O condutor norte- americano infere -se habilitado.
8 O agente pode reter o veículo.
"""

# O gabarito como o pdfminer o devolve: a grade em pares, numero e letra.
GABARITO = "CARGO: TESTE\nItem\nGabarito\n1\nE\n2\nC\n3\nX\n4\nE\n5\nC\n6\nC\n7\nE\n8\nC\n"

# O vocabulario vem do texto do pdfminer, que nao parte palavra.
PALAVRAS = ce.vocabulario(
    "O farol da ilha acende quando a tarde cai, e os barcos voltam devagar. "
    "Sistema Nacional de Trânsito. O condutor norte-americano infere-se habilitado.")


def _itens():
    return {item.numero: item for item in ce.itens_do_caderno(CADERNO, PALAVRAS)}


# --- o gabarito -------------------------------------------------------------------

def test_o_gabarito_sai_dos_pares_numero_e_letra():
    assert ce.ler_gabarito_do_cebraspe(GABARITO) == {
        1: "E", 2: "C", 3: "X", 4: "E", 5: "C", 6: "C", 7: "E", 8: "C"}


@pytest.mark.parametrize("texto, motivo", [
    ("1 C 2 E 2 C", "duas letras"),
    ("1 C 3 E", "faltam itens"),
    ("Item Gabarito", "nao tem item"),
])
def test_gabarito_pela_metade_nao_entra(texto, motivo):
    with pytest.raises(ValueError, match=motivo):
        ce.ler_gabarito_do_cebraspe(texto)


def test_a_letra_com_asterisco_e_a_do_gabarito_alterado():
    """"*C" e o item cujo preliminar foi alterado: a letra vale (PRF-32). Sem
    isso o item sumia - o 120 da PM/AL 2017 - ou faltava no meio."""
    assert ce.ler_gabarito_do_cebraspe("1 *E 2 C 3 *X 4 E") == {1: "E", 2: "C", 3: "X", 4: "E"}


# O gabarito do caderno com espanhol e ingles: uma grade por lingua, e os
# itens de lingua (aqui o 1 e o 2) nas duas, as vezes com letras diferentes.
DUAS_GRADES = GABARITO + "Língua Inglesa\n1\nC\n2\nC\n"


def test_os_itens_das_duas_grades_sao_os_de_lingua():
    assert ce.itens_em_duas_grades(DUAS_GRADES) == {1, 2}
    assert ce.itens_em_duas_grades(GABARITO) == set()


def test_com_duas_linguas_os_itens_de_lingua_ficam_de_fora():
    questoes = _questoes_de(texto_do_gabarito=DUAS_GRADES, duas_linguas=True)
    assert sorted(questoes) == [3, 4, 5, 7, 8]
    assert questoes[4].resposta == "e"


def test_duas_linguas_sem_as_duas_grades_e_recusado():
    with pytest.raises(ValueError, match="duas grades"):
        _questoes_de(texto_do_gabarito=GABARITO, duas_linguas=True)


def test_o_texto_da_outra_lingua_sai_do_comeco_do_texto_base():
    """No CBM/AL 2017 o texto em ingles grudava no texto-base do primeiro grupo
    em portugues (PRF-32): sai o que vem antes da primeira frase em portugues."""
    texto = ("Learning a second language is difficult. The findings provide more evidence. "
             "Internet: <www.exemplo.com> (with adaptations). "
             "O açúcar arrasou o Nordeste. A faixa úmida do litoral tinha um solo fértil.")
    assert ce.sem_a_outra_lingua(texto) == ("O açúcar arrasou o Nordeste. A faixa úmida do "
                                            "litoral tinha um solo fértil.")
    so_portugues = "O farol acende quando a tarde cai. Os barcos voltam."
    assert ce.sem_a_outra_lingua(so_portugues) == so_portugues
    assert ce.sem_a_outra_lingua("The end of the text.") == "The end of the text."


def test_os_gabaritos_por_parte_se_juntam(monkeypatch, tmp_path):
    """O DEPEN 2020: um caderno, um gabarito para cada parte."""
    partes = {"basicos.pdf": "1 E 2 C 3 X 4 E", "especificos.pdf": "5 C 6 C 7 E 8 C"}
    monkeypatch.setattr(ce, "_texto_do_pdfminer", lambda caminho: partes[caminho.name])
    questoes = ce.ler_caderno(None, [tmp_path / "basicos.pdf", tmp_path / "especificos.pdf"],
                              texto=CADERNO, palavras=PALAVRAS)
    assert [q.numero for q in questoes] == [1, 2, 3, 4, 5, 7, 8]


def _questoes_de(**opcoes):
    return {q.numero: q for q in ce.ler_caderno(None, None, texto=CADERNO,
                                                 palavras=PALAVRAS, **opcoes)}


# --- a palavra partida ------------------------------------------------------------

def test_a_palavra_partida_volta_inteira_so_quando_existe():
    assert ce.religar("o Siste ma de trânsito", PALAVRAS) == "o Sistema de trânsito"
    assert ce.religar("o norte- americano e infere -se", PALAVRAS) == \
        "o norte-americano e infere-se"
    # "de" e "vida" sao palavras: a juncao "devida" nao e conserto.
    assert ce.religar("de vida", ce.vocabulario("de vida devida")) == "de vida"


# --- os itens ---------------------------------------------------------------------

def test_cada_item_tem_o_numero_e_o_texto_dele():
    itens = _itens()
    assert sorted(itens) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert itens[2].afirmacao == "Os barcos voltam devagar para o porto, segundo o texto."
    assert itens[3].afirmacao == "A palavra “farol” poderia ser substituída por lanterna."
    assert itens[7].afirmacao == "O condutor norte-americano infere-se habilitado."


def test_o_texto_com_rotulo_vale_para_o_grupo_que_so_o_cita():
    itens = _itens()
    assert itens[1].comando == ("Com relação às ideias do texto 1A1-I precedente, "
                                "julgue os itens a seguir.")
    assert itens[1].texto_base.startswith("O farol da ilha acende quando a tarde cai, e os barcos")
    assert itens[1].texto_base.endswith("Fulano. Revista de Teste, 2019.")
    # A instrucao do caderno ("caso julgue o item CERTO") nao e o comando.
    assert itens[3].comando == "Considerando os sentidos do texto 1A1-I, julgue o item que se segue."
    assert itens[3].texto_base == itens[1].texto_base


def test_a_situacao_e_o_comando_que_vem_depois_do_item():
    itens = _itens()
    assert itens[4].texto_base == ("Em uma operação, foram fiscalizados 20 veículos na "
                                   "primeira hora e 40 na segunda.")
    assert itens[5].comando == "Considerando essa situação hipotética, julgue os itens seguintes."
    # O comando em duas linhas, logo depois do item de figura, com a palavra
    # consertada; o "BLOCO II" e a legenda da figura nao entram em nada.
    assert itens[7].comando == ("No que se refere ao Sistema Nacional de Trânsito, "
                                "julgue os itens a seguir.")
    assert itens[7].texto_base is None
    assert itens[6].afirmacao == "" and itens[6].texto_base is None


def test_a_numeracao_da_margem_nao_vira_item():
    # Os numeros de linha do segundo texto (1, 4, 7, 10), soltos pelo pypdf,
    # caem logo depois do item 3: o "4" deles era tomado pelo item 4.
    caderno = ("Considerando o texto do farol, julgue os itens a seguir.\n"
               "1 O farol acende de manhã.\n2 Os barcos voltam cedo.\n3 A ilha não tem porto.\n"
               "\\t/1\n\n4\n\n7\n\n10\n"
               "  O porto da ilha recebe barcos de pesca todos os dias.\n"
               "Julgue os itens seguintes, a respeito do texto do porto.\n"
               "4 O porto recebe barcos de pesca.\n5 Os barcos chegam só aos domingos.\n")
    itens = {item.numero: item for item in ce.itens_do_caderno(caderno, PALAVRAS)}
    assert sorted(itens) == [1, 2, 3, 4, 5]
    assert itens[3].afirmacao == "A ilha não tem porto."
    assert itens[4].afirmacao == "O porto recebe barcos de pesca."
    assert itens[4].comando == "Julgue os itens seguintes, a respeito do texto do porto."
    assert itens[4].texto_base == "O porto da ilha recebe barcos de pesca todos os dias."


def test_o_item_de_figura_seguido_nao_e_numeracao_da_margem():
    # Tres itens de figura seguidos crescem de um em um: ficam.
    caderno = ("A partir da figura precedente, julgue os itens a seguir.\n"
               "1\n2\n3\n4 O mapa mostra o porto.\n")
    assert [i.numero for i in ce.itens_do_caderno(caderno, PALAVRAS)] == [1, 2, 3, 4]


def test_as_instrucoes_numeradas_da_capa_nao_viram_itens():
    caderno = ("1 Ao receber este caderno de provas, confira os seus dados.\n"
               "2 Durante a realização das provas, não se comunique com ninguém.\n"
               "3 Não serão fornecidas folhas suplementares para rascunho.\n"
               "Considerando o texto do farol, julgue os itens a seguir.\n"
               "1 O farol acende de manhã.\n2 Os barcos voltam cedo.\n3 A ilha não tem porto.\n")
    itens = ce.itens_do_caderno(caderno, PALAVRAS)
    assert [i.afirmacao for i in itens] == ["O farol acende de manhã.", "Os barcos voltam cedo.",
                                            "A ilha não tem porto."]
    assert itens[0].comando == "Considerando o texto do farol, julgue os itens a seguir."


def test_o_comando_que_o_item_completa_nao_precisa_de_julgue():
    # Sem "julgue" no comando, a ultima frase com "julgue" era a instrucao do
    # caderno ("caso julgue o item CERTO").
    caderno = ("Nas questões a seguir, marque C caso julgue o item CERTO.\n"
               "  O farol da ilha acende quando a tarde cai.\n"
               "A correção gramatical do texto seria mantida se\n"
               "1 o termo “quando” fosse substituído por assim que.\n"
               "2 a vírgula fosse posta depois de “farol”.\n")
    itens = ce.itens_do_caderno(caderno, PALAVRAS)
    assert [i.comando for i in itens] == ["A correção gramatical do texto seria mantida se"] * 2
    assert itens[0].afirmacao == "o termo “quando” fosse substituído por assim que."
    assert itens[0].texto_base == "O farol da ilha acende quando a tarde cai."


def test_o_cabecalho_da_pagina_entre_dois_itens_nao_vira_comando():
    # Na PM-AL 2021 o cabecalho vem com dois espacos, como paragrafo de texto,
    # e sem ponto no fim: nao e comando, e o grupo continua o mesmo.
    caderno = ("Considerando o texto do farol, julgue os itens a seguir.\n"
               "1 O farol acende de manhã.\n"
               "  CEBRASPE | TESTE – Aplicação: 2021\n"
               "2 Os barcos voltam cedo.\n")
    itens = ce.itens_do_caderno(caderno, PALAVRAS)
    assert [i.comando for i in itens] == [
        "Considerando o texto do farol, julgue os itens a seguir."] * 2


def test_o_rotulo_texto_sem_codigo_abre_o_texto_e_fecha_o_item():
    caderno = ("Considerando o texto, julgue os itens a seguir.\n"
               "1 O farol acende de manhã.\n"
               " Texto\n"
               "  O porto da ilha recebe barcos de pesca.\n"
               "Com relação ao texto precedente, julgue os itens que se seguem.\n"
               "2 O porto recebe barcos de pesca.\n")
    itens = ce.itens_do_caderno(caderno, PALAVRAS)
    assert itens[0].afirmacao == "O farol acende de manhã."
    assert itens[1].texto_base == "O porto da ilha recebe barcos de pesca."


def test_o_comando_em_ingles_tambem_vale():
    caderno = ("  A deep freeze hit Texas this week.\n"
               "About ideas stated in the text above, judge the following items.\n"
               "1 Texas was cold.\n2 Texas was hot.\n")
    itens = ce.itens_do_caderno(caderno, set())
    assert itens[1].comando.endswith("judge the following items.")
    assert itens[1].texto_base == "A deep freeze hit Texas this week."


# --- o caderno em que o pypdf perde o recuo (FUB e SEE/DF de 2016) ---------------

# INVENTADO, na forma da FUB: o pypdf nao poe os dois espacos do paragrafo, e
# o cabecalho da pagina abre com o codigo de barras do caderno.
CADERNO_SEM_RECUO = """||999XYZ_001_01N123456|| CESPE | CEBRASPE – XYZ – Aplicação: 2016
Um carro parte do repouso e atinge 20 m/s em 10 s.
Considerando essa situação hipotética, julgue os itens a seguir.
51 A aceleração média do carro foi de
2 m/s2.
52 O carro percorreu 100 m. Nesse caso, a velocidade média foi
de 10 m/s.
Uma bola de 1 kg cai de uma altura de 5 m.
A respeito dessa situação, julgue os itens seguintes.
53 A bola chega ao chão com 50 J de energia
cinética.
||999XYZ_001_01N123456|| CESPE | CEBRASPE – XYZ – Aplicação: 2016
54 O peso da bola é de 10 N.
"""

# O mesmo trecho como o pdfminer o devolve: blocos separados por linha vazia,
# a primeira linha do item num bloco so dela e a continuacao no seguinte.
PDFMINER_SEM_RECUO = """||999XYZ_001_01N123456||

CESPE | CEBRASPE – XYZ – Aplicação: 2016

Um  carro  parte  do  repouso  e  atinge  20  m/s  em  10  s.

Considerando essa situação hipotética, julgue os itens a seguir.

51 A aceleração média do carro foi de

2 m/s2.

52 O carro percorreu 100 m. Nesse caso, a velocidade média foi

de 10 m/s.

Uma  bola  de  1  kg  cai  de  uma  altura  de  5  m.

A respeito dessa situação, julgue os itens seguintes.

53 A bola chega ao chão com 50 J de energia

cinética.

1

¿Qué hora es?

54 O peso da bola é de 10 N.
"""


def _itens_sem_recuo(paragrafos):
    itens = ce.itens_do_caderno(CADERNO_SEM_RECUO, set(), primeiro=51, paragrafos=paragrafos)
    return {item.numero: item for item in itens}


def test_sem_o_recuo_a_situacao_seguinte_grudava_no_item():
    # O defeito, para lembrar: sem os paragrafos do pdfminer.
    itens = _itens_sem_recuo(None)
    assert itens[52].afirmacao.endswith("Uma bola de 1 kg cai de uma altura de 5 m.")
    assert itens[53].texto_base is None


def test_o_paragrafo_do_pdfminer_separa_a_situacao_do_item():
    itens = _itens_sem_recuo(ce.inicios_de_paragrafo(PDFMINER_SEM_RECUO))
    assert itens[51].texto_base == "Um carro parte do repouso e atinge 20 m/s em 10 s."
    # O item de duas frases fica inteiro: a segunda nao vira paragrafo.
    assert itens[52].afirmacao == "O carro percorreu 100 m. Nesse caso, a velocidade média foi de 10 m/s."
    assert itens[53].texto_base == "Uma bola de 1 kg cai de uma altura de 5 m."
    assert itens[53].comando == "A respeito dessa situação, julgue os itens seguintes."


def test_o_cabecalho_com_o_codigo_de_barras_nao_gruda_no_item():
    itens = _itens_sem_recuo(None)
    assert itens[53].afirmacao == "A bola chega ao chão com 50 J de energia cinética."
    assert ce.MOBILIA_DO_CADERNO.match("714005_01N167818 CEBRASPE – SEE/PE – Edital: 2022")


# O caderno de 2022 (Policia Cientifica de AL): o codigo de 14 caracteres antes
# do CEBRASPE, e o comando do grupo seguinte logo depois do cabecalho.
CADERNO_DE_2022 = """Julgue os itens que se seguem com base em aspectos linguísticos do texto.
9 A vírgula poderia ser retirada.
10 Haveria prejuízo da correção gramatical do texto.

 701CB201597439 CEBRASPE – POLC/AL – Edital: 2022


NOÇÕES DE INFORMÁTICA
No que se refere a sistemas operacionais, julgue os itens que se
seguem.
11 O Linux tem o diretório /etc.
"""


def test_o_codigo_de_14_caracteres_nao_leva_o_comando_novo_para_o_item_de_antes():
    """Sem reconhecer o "701CB201597439", o comando de Informatica grudava no
    item 10, e o 11 ficava com o comando de Portugues (PRF-32)."""
    itens = {i.numero: i for i in ce.itens_do_caderno(CADERNO_DE_2022, set(), primeiro=9)}
    assert itens[10].afirmacao == "Haveria prejuízo da correção gramatical do texto."
    assert itens[11].comando.startswith("No que se refere a sistemas operacionais")
    for cabecalho in ("701CB201597439 CEBRASPE – POLC/AL – Edital: 2022",
                      "705CG101604107 CEBRASPE – PC/AL – Edital: 2022",
                      "70100101732652 CEBRASPE – POLC/AL – Edital: 2022"):
        assert ce.MOBILIA_DO_CADERNO.match(cabecalho)


def test_inicios_de_paragrafo_pula_a_continuacao_do_item_e_o_numero_da_margem():
    inicios = ce.inicios_de_paragrafo(PDFMINER_SEM_RECUO)
    # A continuacao do item 52 comeca com minuscula; a do 51 vem logo depois
    # da primeira linha: nenhuma das duas abre paragrafo.
    assert ce._chave_da_linha("de 10 m/s.") not in inicios
    assert ce._chave_da_linha("2 m/s2.") not in inicios
    # O "1" sozinho e numeracao da margem: a linha depois dele abre paragrafo,
    # e a chave casa com a linha do pypdf, que traz o numero colado no fim.
    assert ce._chave_da_linha("¿Qué hora es? 1") in inicios


# --- as questoes ------------------------------------------------------------------

def _questoes(**opcoes):
    return {q.numero: q for q in ce.ler_caderno(None, None, texto=CADERNO,
                                                 texto_do_gabarito=GABARITO,
                                                 palavras=PALAVRAS, **opcoes)}


def test_o_item_vira_questao_de_certo_ou_errado_com_o_gabarito_definitivo():
    questoes = _questoes()
    assert 6 not in questoes                     # o item de figura fica de fora
    assert questoes[1].alternativas == {"c": "Certo", "e": "Errado"}
    assert (questoes[1].resposta, questoes[2].resposta) == ("e", "c")
    assert questoes[3].anulada and questoes[3].resposta is None
    assert questoes[1].enunciado == ("Com relação às ideias do texto 1A1-I precedente, julgue "
                                     "os itens a seguir.\n\nO farol acende de manhã.")
    assert questoes[1].materia is None           # sem faixa, sem materia


def test_a_materia_vem_da_faixa_e_o_item_fora_de_faixa_fica_de_fora():
    questoes = _questoes(materias=[(1, 3, "Língua Portuguesa"), (7, 8, "Legislação de Trânsito")])
    assert sorted(questoes) == [1, 2, 3, 7, 8]
    assert questoes[2].materia == "Língua Portuguesa"
    assert questoes[8].materia == "Legislação de Trânsito"


def test_caderno_e_gabarito_que_nao_batem_sao_recusados():
    with pytest.raises(ValueError, match="o caderno tem os itens"):
        ce.ler_caderno(None, None, texto=CADERNO, texto_do_gabarito=GABARITO + "9\nC\n",
                       palavras=PALAVRAS)


def test_a_lista_de_outras_bancas_manda_o_certo_errado_para_este_leitor(monkeypatch, tmp_path):
    from radar.servico import provas

    chamadas = []
    monkeypatch.setattr(ce, "ler_caderno",
                        lambda caminho, gabarito, **opcoes: chamadas.append(opcoes) or ["ok"])
    prova = {"formato": "certo_errado", "materias": {"1-3": "Língua Portuguesa"}}
    assert provas._ler_cebraspe(tmp_path / "c.pdf", prova, tmp_path / "g.pdf") == ["ok"]
    assert chamadas == [{"ler": None, "materias": [(1, 3, "Língua Portuguesa")],
                         "duas_linguas": False}]


def test_a_lista_manda_os_gabaritos_por_parte_e_as_duas_linguas(monkeypatch, tmp_path):
    """O DEPEN 2020 (um gabarito por parte) e o CBM/AL 2017 (espanhol e
    ingles na mesma grade) pela lista (PRF-32)."""
    from radar.servico import provas

    chamadas = []
    monkeypatch.setattr(ce, "ler_caderno",
                        lambda caminho, gabarito, **opcoes: chamadas.append((gabarito, opcoes)) or [])
    monkeypatch.setattr(provas, "_outros_gabaritos", lambda prova: [tmp_path / "g2.pdf"])
    prova = {"formato": "certo_errado", "duas_linguas": True,
             "outros_gabaritos": [{"gabarito": "https://exemplo/g2.pdf"}]}
    provas._ler_cebraspe(tmp_path / "c.pdf", prova, tmp_path / "g.pdf")
    gabarito, opcoes = chamadas[0]
    assert gabarito == [tmp_path / "g.pdf", tmp_path / "g2.pdf"]
    assert opcoes["duas_linguas"] is True


def _multipla_escolha_lida(monkeypatch):
    """O leitor de multipla escolha do Cebraspe trocado por quatro questoes
    fixas: o teste e da faixa, nao do PDF."""
    from radar import questoes_cebraspe
    from radar.questoes import Questao

    lidas = [Questao(numero=n, enunciado=f"Questão {n}") for n in (1, 2, 3, 4)]
    monkeypatch.setattr(questoes_cebraspe, "ler_prova",
                        lambda caminho, gabarito, **opcoes: lidas)


def test_na_multipla_escolha_com_faixas_a_materia_vem_da_faixa_e_o_resto_sai(
        monkeypatch, tmp_path):
    from radar.servico import provas

    _multipla_escolha_lida(monkeypatch)
    prova = {"materias": {"1-2": "Língua Portuguesa", "4": "Informática"}}
    questoes = provas._ler_cebraspe(tmp_path / "c.pdf", prova, tmp_path / "g.pdf")
    assert [(q.numero, q.materia) for q in questoes] == [
        (1, "Língua Portuguesa"), (2, "Língua Portuguesa"), (4, "Informática")]


def test_na_multipla_escolha_sem_faixas_as_questoes_ficam_como_vieram(monkeypatch, tmp_path):
    from radar.servico import provas

    _multipla_escolha_lida(monkeypatch)
    questoes = provas._ler_cebraspe(tmp_path / "c.pdf", {}, tmp_path / "g.pdf")
    assert [(q.numero, q.materia) for q in questoes] == [(1, None), (2, None), (3, None),
                                                         (4, None)]

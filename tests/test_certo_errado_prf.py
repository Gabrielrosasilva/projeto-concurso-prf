"""O Certo/Errado como formato principal (Etapa 4 da PRF, PRF-28).

O que estes testes seguram:

  * o item de Certo/Errado pode ficar EM BRANCO: a resposta fica dada, sem
    acerto e sem chute; na multipla escolha o em branco e recusado;
  * a rodada com Certo/Errado tem a NOTA LIQUIDA (certa +1, errada -1, em
    branco 0), o acerto bruto ao lado e a multipla escolha a parte;
  * o chute (certo e errado) sai do acerto acumulado - desempenho por
    assunto, Minhas materias, evolucao - e aparece ao lado; o chute errado
    sai do caderno de erros (refazer, R+7, motivos) e a tela nao oferece o
    "Anotar"; na nota da rodada ele conta, como na prova;
  * o caderno de Certo/Errado do Cebraspe da lista treina e mede como
    complementar; o da AOCP e a prova do proprio cargo, nao;
  * a contagem Certo x Errado (uma vez por item, anulado a parte), a margem
    de 95% e a regra do chute;
  * a tela Analises > Certo/Errado e o `radar chute`.

Datas fixas e banco temporario: nada depende do dia nem da internet.
"""
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from typer.testing import CliRunner

from radar.cli import app as cli
from radar.db import sessao
from radar.models import RespostaDeSimulado, Simulado
from radar.questoes_certo_errado import ALTERNATIVAS, EM_BRANCO
from radar.servico import certo_errado, classificacoes, complementar, metricas
from radar.servico import desempenho_por_conteudo as por_conteudo
from radar.servico import simulado as rodadas
from radar.util import fuso_local
from radar.web.app import app
from tests.test_correcao_na_hora import _ids, _rodada
from tests.test_desempenho import (HOJE, NO_TEMPO, SEG, _questao as _de_penal,  # noqa: F401
                                   arvore, plano)
from tests.test_simulado import _questao


def _item(numero: int, resposta: str = "c", **mais):
    """Um item de Certo/Errado (do Cebraspe, salvo outra `banca`)."""
    base = dict(banca="CEBRASPE", alternativas=dict(ALTERNATIVAS), resposta=resposta,
                impressao=f"ce{numero}", enunciado=f"Item de Certo/Errado {numero}.")
    return _questao(numero, **{**base, **mais})


def _resposta(simulado_id: int, questao_id: int) -> RespostaDeSimulado:
    with sessao() as s:
        return s.scalar(select(RespostaDeSimulado)
                        .where(RespostaDeSimulado.simulado_id == simulado_id)
                        .where(RespostaDeSimulado.questao_id == questao_id))


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


# --- o em branco ------------------------------------------------------------------

def test_o_item_de_certo_errado_pode_ficar_em_branco(banco_temporario):
    rodada = _rodada(_item(1), _item(2))
    primeiro, segundo = _ids(rodada)

    # Em branco com o "vou no chute" marcado: em branco e nao chutar.
    assert rodada and rodadas.responder(rodada, primeiro, EM_BRANCO, chutou=True) is None
    gravada = _resposta(rodada, primeiro)
    assert gravada.escolhida == EM_BRANCO
    assert gravada.acertou is None and gravada.chutou is False
    # A rodada anda: a proxima e a segunda.
    assert rodadas.questao_atual(rodada)[0].questao_id == segundo


def test_a_multipla_escolha_recusa_o_em_branco(banco_temporario):
    rodada = _rodada(_questao(1))
    (primeira,) = _ids(rodada)

    assert rodadas.responder(rodada, primeira, EM_BRANCO) is None
    assert _resposta(rodada, primeira).escolhida is None


# --- a nota liquida da rodada -------------------------------------------------------

def test_a_rodada_de_certo_errado_tem_a_nota_liquida(banco_temporario):
    rodada = _rodada(_item(1, "c"), _item(2, "e"), _item(3, "c"), _item(4, "e"),
                     _questao(5, impressao="me5"))
    um, dois, tres, quatro, cinco = _ids(rodada)
    rodadas.responder(rodada, um, "c")                    # certa
    rodadas.responder(rodada, dois, "e", chutou=True)     # certa no chute
    rodadas.responder(rodada, tres, "e", chutou=True)     # errada no chute
    rodadas.responder(rodada, quatro, EM_BRANCO)          # em branco
    rodadas.responder(rodada, cinco, "c")                 # multipla escolha certa

    resumo = metricas.resumo_do_simulado(rodada)
    nota = resumo["nota"]
    assert (nota.certos, nota.errados, nota.em_branco) == (2, 1, 1)
    assert nota.nota == 1 and nota.itens == 4
    assert nota.porcentagem == 25 and nota.bruto == 50
    # O chute conta na nota, como na prova, e o saldo dele vem ao lado.
    assert (nota.chutes_certos, nota.chutes_errados, nota.saldo_dos_chutes) == (1, 1, 0)
    assert nota.frase() == ("Nota líquida: 1 em 4 itens (25%) = 2 certos − 1 errado, "
                            "1 em branco · acerto bruto 50%")
    # A multipla escolha fica a parte, nunca somada a nota.
    assert (resumo["multipla_escolha"].respondidas, resumo["multipla_escolha"].acertos) == (1, 1)
    # O em branco nao e erro nem acerto, e a rodada terminou.
    assert resumo["em_branco"] == 1 and resumo["erros"] == 1 and resumo["terminou"]
    assert metricas.andamento_da_rodada(rodada)["marcas"] == [
        "certa", "certa", "errada", "branco", "certa"]


def test_a_rodada_so_de_multipla_escolha_nao_tem_nota_liquida(banco_temporario):
    rodada = _rodada(_questao(1))
    (primeira,) = _ids(rodada)
    rodadas.responder(rodada, primeira, "c")
    resumo = metricas.resumo_do_simulado(rodada)
    assert resumo["nota"] is None and resumo["multipla_escolha"] is None


# --- o chute fora do acerto acumulado e do caderno de erros ------------------------------

def test_o_chute_errado_fica_fora_do_caderno_de_erros(banco_temporario):
    rodada = _rodada(_item(1, "c"), _item(2, "c"), _item(3, "c"))
    um, dois, tres = _ids(rodada)
    rodadas.responder(rodada, um, "e")                   # erro de verdade
    rodadas.responder(rodada, dois, "e", chutou=True)    # chute errado
    rodadas.responder(rodada, tres, EM_BRANCO)           # em branco

    assert rodadas.questoes_erradas() == [um]
    assert [r.questao_id for r in metricas.erros_das_rodadas([rodada])] == [um]
    no_radar = metricas.motivos_dos_erros()["fepese"]
    assert no_radar.erros == 1 and "chutei" not in no_radar.por_motivo

    itens = {i.questao_id: i for i in rodadas.revisao(rodada)}
    assert itens[um].vai_ao_caderno
    assert itens[dois].errou and not itens[dois].vai_ao_caderno
    assert itens[tres].em_branco and not itens[tres].errou


def test_o_chute_e_o_em_branco_saem_do_acerto_acumulado(banco_temporario):
    rodada = _rodada(_item(1, "c", materia="Direito Penal"),
                     _item(2, "c", materia="Direito Penal"),
                     _item(3, "c", materia="Direito Penal"),
                     _item(4, "c", materia="Direito Penal"))
    um, dois, tres, quatro = _ids(rodada)
    rodadas.responder(rodada, um, "c")                   # firme e certa
    rodadas.responder(rodada, dois, "e")                 # firme e errada
    rodadas.responder(rodada, tres, "c", chutou=True)    # chute certo: fora
    rodadas.responder(rodada, quatro, EM_BRANCO)         # em branco: fora

    numeros = metricas.acumulado_por(lambda q: ["todas"])["todas"]
    assert (numeros.acertos, numeros.erros, numeros.chutes, numeros.em_branco) == (1, 1, 1, 1)
    assert numeros.porcentagem == 50
    acumulado = metricas.acumulado()
    assert (acumulado.respondidas, acumulado.acertos) == (2, 1)
    assert (metricas.evolucao().respondidas, metricas.evolucao().acertos) == (2, 1)


def _responder_no_no(numero: int, acertou: bool, chutou: bool = False) -> None:
    """Uma resposta em 28/09, classificada em Lei penal no tempo."""
    with sessao() as s:
        questao = _de_penal(numero)
        s.add(questao)
        s.flush()
        simulado = Simulado(filtros={})
        s.add(simulado)
        s.flush()
        s.add(RespostaDeSimulado(
            simulado_id=simulado.id, questao_id=questao.id, ordem=1,
            escolhida="a" if acertou else "b", acertou=acertou, chutou=chutou,
            respondida_em=datetime.combine(SEG, datetime.min.time(),
                                           tzinfo=fuso_local()) + timedelta(hours=20)))
        chave = classificacoes.chave_de(questao)
    classificacoes.classificar(chave, NO_TEMPO, "teste")


def test_o_desempenho_por_assunto_conta_o_chute_ao_lado(plano):
    _responder_no_no(1, True)
    _responder_no_no(2, False)
    _responder_no_no(3, True, chutou=True)
    _responder_no_no(4, False, chutou=True)

    no = por_conteudo.por_no(plano=plano, hoje=HOJE)[NO_TEMPO]
    assert (no.radar.respostas, no.radar.acertos, no.radar.chutes) == (2, 1, 2)
    assert no.radar.volume == 4
    assert no.divisao() == "radar 50% em 2 (2 no chute, fora da conta) · anotado —"


# --- o Certo/Errado do Cebraspe treina e mede --------------------------------------------

def test_o_certo_errado_do_cebraspe_da_lista_entra_no_acervo(banco_temporario, monkeypatch):
    lista = [
        {"banca": "Cebraspe", "cargo": "Agente de Polícia Federal", "formato": "certo_errado",
         "caderno": "https://cdn.cebraspe.test/pf.pdf"},
        {"banca": "Instituto AOCP", "cargo": "Policial Penal", "formato": "certo_errado",
         "caderno": "https://aocp.test/ppdf.pdf"},
        {"banca": "Cebraspe", "cargo": "Delegado", "caderno": "https://cdn.cebraspe.test/me.pdf"},
    ]
    monkeypatch.setattr("radar.servico.provas.carregar_provas_de_outras_bancas", lambda: lista)
    monkeypatch.setattr(complementar.evidencia, "da_prova",
                        lambda cargo, banca, uf: "complementar")

    assert complementar.cadernos_de_certo_errado() == {"https://cdn.cebraspe.test/pf.pdf"}
    assert "https://cdn.cebraspe.test/pf.pdf" in complementar.provas_aceitas()
    assert "https://cdn.cebraspe.test/pf.pdf" in complementar.provas_dos_padroes()

    # A prova do proprio cargo e alvo, e nao complementar.
    monkeypatch.setattr(complementar.evidencia, "da_prova", lambda cargo, banca, uf: "alvo")
    assert complementar.cadernos_de_certo_errado() == set()


# --- a contagem e a regra do chute -------------------------------------------------------

def test_o_gabarito_conta_uma_vez_por_item_e_o_anulado_a_parte(banco_temporario):
    from tests.test_simulado import _semear

    _semear(
        _item(1, "c", evidencia="alvo", ano=2021),
        _item(2, "e", evidencia="alvo", ano=2021),
        _item(3, None, evidencia="alvo", ano=2021, anulada=True),
        _item(4, "e", evidencia="complementar"),
        # O mesmo item em outro caderno: conta uma vez.
        _item(4, "e", evidencia="complementar", prova_url="https://x.test/outro.pdf"),
        # Multipla escolha do Cebraspe e Certo/Errado de outra banca: fora.
        _questao(6, banca="CEBRASPE", evidencia="complementar", impressao="me6"),
        _item(7, "c", evidencia="complementar", banca="Instituto AOCP"),
    )
    linhas = {g.nome: g for g in certo_errado.gabarito_do_cebraspe()}

    assert list(linhas) == ["Prova da PRF de 2021", "Provas da PRF juntas",
                            "Acervo complementar do Cebraspe", "Tudo do Cebraspe no radar"]
    prf = linhas["Prova da PRF de 2021"]
    assert (prf.certo, prf.errado, prf.anulados) == (1, 1, 1)
    tudo = linhas["Tudo do Cebraspe no radar"]
    # Cada item do teste vem num caderno; a copia repetida nao soma caderno.
    assert (tudo.certo, tudo.errado, tudo.anulados, tudo.cadernos) == (1, 2, 1, 4)
    # Abaixo do minimo do amostra.yml (50), nao se fala de tendencia.
    assert tudo.veredito == "amostra_pequena"


def test_a_margem_de_95_decide_se_a_tendencia_e_sorteio():
    # 714 Errado em 1.395: 51,2% com margem de 2,6 -> cobre os 50%.
    equilibrado = certo_errado.Gabarito("todos", certo=681, errado=714, minimo=50)
    assert equilibrado.porcentagem_errado == 51.2 and equilibrado.margem == 2.6
    assert equilibrado.veredito == "equilibrado"
    assert equilibrado.chute_cego == 0.024 and equilibrado.lado_mais_comum == "Errado"
    # 60 Errado em 100: margem de 9,6 -> passa dos 50%.
    torto = certo_errado.Gabarito("torto", certo=40, errado=60, minimo=50)
    assert torto.veredito == "errado" and torto.chute_cego == 0.2


def test_os_meus_chutes_dizem_se_chutar_compensa():
    assert certo_errado.MeusChutes(certos=10, errados=5, minimo=30).veredito == "poucos"
    assert certo_errado.MeusChutes(certos=45, errados=15, minimo=30).veredito == "compensa"
    assert certo_errado.MeusChutes(certos=15, errados=45, minimo=30).veredito == "nao_compensa"
    empate = certo_errado.MeusChutes(certos=17, errados=15, minimo=30)
    assert empate.veredito == "empate" and empate.saldo == 2


def test_a_regra_do_chute_diz_os_numeros():
    gabarito = certo_errado.Gabarito("todos", certo=681, errado=714, minimo=50)
    passos = certo_errado.regra_do_chute(
        gabarito, certo_errado.MeusChutes(certos=15, errados=45, minimo=30))
    assert len(passos) == 3
    assert "deixe em branco" in passos[1] and "25%" in passos[1] and "perdeu 30" in passos[1]
    assert "51,2%" in passos[2] and "+0,024" in passos[2] and "em branco" in passos[2]


def test_a_nota_liquida_acumulada_traz_os_chutes(banco_temporario):
    rodada = _rodada(_item(1, "c"), _item(2, "c"))
    um, dois = _ids(rodada)
    rodadas.responder(rodada, um, "c", chutou=True)
    rodadas.responder(rodada, dois, "e", chutou=True)
    chutes = certo_errado.meus_chutes()
    assert (chutes.certos, chutes.errados, chutes.minimo) == (1, 1, 30)


# --- as telas e o terminal ---------------------------------------------------------------

def test_a_tela_da_questao_oferece_o_em_branco_so_no_certo_errado(cliente):
    rodada = _rodada(_item(1), _questao(2, impressao="me2"))
    um, dois = _ids(rodada)

    assert "Deixar em branco" in cliente.get(f"/simulado/{rodada}").text
    cliente.post(f"/simulado/{rodada}/responder", data={"questao_id": um, "letra": EM_BRANCO})
    corrigida = cliente.get(f"/simulado/{rodada}?ver={um}").text
    assert "Em branco: o gabarito é Certo" in corrigida
    assert "Anotar no caderno de erros" not in corrigida
    assert "Deixar em branco" not in cliente.get(f"/simulado/{rodada}").text


def test_o_chute_errado_nao_oferece_o_caderno_e_o_relatorio_tem_a_nota(cliente):
    rodada = _rodada(_item(1, "c"), _item(2, "c"))
    um, dois = _ids(rodada)
    cliente.post(f"/simulado/{rodada}/responder",
                 data={"questao_id": um, "letra": "e", "chutei": "1"})
    corrigida = cliente.get(f"/simulado/{rodada}?ver={um}").text
    assert "fica fora do caderno de erros" in corrigida
    assert "Anotar no caderno de erros" not in corrigida and "Por que errei?" not in corrigida

    cliente.post(f"/simulado/{rodada}/responder", data={"questao_id": dois, "letra": "c"})
    relatorio = cliente.get(f"/simulado/{rodada}").text
    assert "na nota líquida" in relatorio and "acerto bruto 50%" in relatorio
    assert "📓 Anotar erro" not in relatorio


def test_a_tela_do_certo_errado_abre(cliente):
    resposta = cliente.get("/analises/certo-errado")
    assert resposta.status_code == 200
    assert "A regra do chute" in resposta.text and "item 9.12.2" in resposta.text


def test_o_comando_chute_mostra_a_regra(banco_temporario):
    saida = CliRunner().invoke(cli, ["chute"])
    assert saida.exit_code == 0, saida.output
    assert "A regra do chute" in saida.output and "9.12.2" in saida.output

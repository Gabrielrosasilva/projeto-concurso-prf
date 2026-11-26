"""O cronograma da PRF, Ciclos 1 e 2 (PRF-35, dividido em duas metades na PRF-38): as
regras do metodo no arquivo.

O PRF/config/cronograma.yml foi gerado por script e pode ser editado a mao; este
teste diz se uma edicao quebrou o que o docs/metodo.md promete. Le o arquivo
versionado, a arvore versionada (data/conteudos.json, a do edital da PRF) e o
PRF/config/redacao.yml: nada de internet nem do dia de hoje.
"""
import shutil
from collections import Counter
from datetime import timedelta

import pytest
import yaml

from radar import config
from radar import cronograma as plano_de_estudo

ARQUIVO = config.RAIZ / "PRF" / "config" / "cronograma.yml"
REDACAO = config.RAIZ / "PRF" / "config" / "redacao.yml"
SABADO = 5
SEMANAS_DO_CICLO = 8
TRANSITO = "Legislação de Trânsito"
PORTUGUES = "Língua Portuguesa"
DIREITOS = {"Direito Constitucional", "Direito Administrativo", "Direito Penal",
            "Direito Processual Penal", "Legislação Especial", "Direitos Humanos"}
CICLO_1 = {TRANSITO, PORTUGUES} | DIREITOS
CICLO_2 = {"Língua Estrangeira (Inglês ou Espanhol)", "Informática", "Raciocínio Lógico-Matemático",
           "Física", "Ética e Cidadania", "Geopolítica", PORTUGUES}
RESOLUCOES = "Legislação de Trânsito > Resoluções do Conselho Nacional de Trânsito (CONTRAN) e suas alterações"


@pytest.fixture
def plano(tmp_path, monkeypatch):
    # O conftest troca a arvore pela antiga (PRF-9); este plano aponta para a da PRF.
    shutil.copy2(config.RAIZ / "data" / "conteudos.json", tmp_path / "conteudos.json")
    monkeypatch.setenv("RADAR_DATA_DIR", str(tmp_path))
    return plano_de_estudo.carregar(ARQUIVO)


def _uteis(plano, ciclo=None):
    dias = [d for d in plano.dias if d.data.weekday() < SABADO]
    if ciclo == 1:
        return [d for d in dias if d.semana <= SEMANAS_DO_CICLO]
    if ciclo == 2:
        return [d for d in dias if d.semana > SEMANAS_DO_CICLO]
    return dias


def _sabados(plano):
    return [d for d in plano.dias if d.data.weekday() == SABADO]


def _teorias(dias):
    return [f for d in dias for f in d.manha if f.tipo == "teoria"]


def test_dezesseis_semanas_de_segunda_a_sabado_de_4_de_janeiro_a_24_de_abril(plano):
    assert plano.inicio.isoformat() == "2027-01-04" and plano.fim.isoformat() == "2027-04-24"
    assert len(plano.dias) == 96 and len(_uteis(plano)) == 80 and len(_sabados(plano)) == 16
    assert [e.nome for e in plano.mapa[:2]] == ["Ciclo 1", "Ciclo 2"]
    assert plano.mapa[0].fim.isoformat() == "2027-02-27" and plano.mapa[1].inicio.isoformat() == "2027-03-01"


def test_os_feriados_estao_marcados(plano):
    feriados = {d.data.isoformat(): d.feriado for d in plano.dias if d.feriado}
    assert set(feriados) == {"2027-02-08", "2027-02-09", "2027-03-26", "2027-04-21"}


def test_a_prova_de_2021_e_as_metas(plano):
    # Os 120 itens da prova de 2021, e a meta e a soma das metas das materias.
    assert sum(m.questoes for m in plano.materias) == 120
    assert plano.meta_da_prova["acertos"] == sum(m.meta for m in plano.materias) == 96


def test_toda_manha_util_tem_duas_teorias_de_materias_diferentes_com_fixacao(plano):
    for dia in _uteis(plano):
        teorias = [f for f in dia.manha if f.tipo == "teoria"]
        assert len(teorias) == 2, dia.data
        assert teorias[0].materia != teorias[1].materia, dia.data
        fixacoes = [f for f in dia.manha if f.tipo == "questoes" and f.consulta]
        assert [f.materia for f in fixacoes] == [t.materia for t in teorias], dia.data


def test_cada_ciclo_estuda_a_sua_metade_das_materias(plano):
    # O pedido de 26/11/2026 (PRF-38): metade das materias em cada ciclo de 8 semanas.
    um, dois = _teorias(_uteis(plano, 1)), _teorias(_uteis(plano, 2))
    assert len(um) == len(dois) == 80
    assert {f.materia for f in um} == CICLO_1 and {f.materia for f in dois} == CICLO_2
    contagem = Counter(f.materia for f in um)
    assert max(contagem, key=contagem.get) == TRANSITO
    # Cada aula e um tema so: nenhum titulo de teoria se repete.
    titulos = [f.titulo for f in um + dois]
    assert len(titulos) == len(set(titulos))


def test_nenhuma_aula_junta_mais_de_tres_resolucoes_do_contran(plano):
    resolucoes = [f for f in _teorias(_uteis(plano)) if f.conteudo == RESOLUCOES]
    assert resolucoes and all(1 <= len(f.nos) <= 3 for f in resolucoes)


def test_o_ciclo_2_mantem_o_ciclo_1_toda_manha(plano):
    for dia in _uteis(plano, 2):
        manutencao = [f for f in dia.manha if f.titulo.startswith("Manutenção do Ciclo 1: ")]
        assert len(manutencao) == 1, dia.data
        assert manutencao[0].materia in CICLO_1 - {PORTUGUES} and not manutencao[0].consulta
    transito = [d for d in _uteis(plano, 2)
                if any(f.materia == TRANSITO and f.titulo.startswith("Manutenção") for f in d.manha)]
    assert len(transito) == 3 * SEMANAS_DO_CICLO       # segunda, quarta e sexta
    assert not any(f.titulo.startswith("Manutenção") for d in _uteis(plano, 1) for f in d.manha)


def test_a_aprendizagem_da_noite_e_sem_consulta_e_do_tema_da_manha(plano):
    for dia in _uteis(plano):
        temas = {f.titulo for f in dia.manha if f.tipo == "teoria"}
        aprendizagem = [f for f in dia.noite if f.titulo.startswith("Aprendizagem: ")]
        assert len(aprendizagem) == 2 and not any(f.consulta for f in aprendizagem), dia.data
        assert {f.titulo.removeprefix("Aprendizagem: ") for f in aprendizagem} == temas


def test_as_revisoes_voltam_ao_tema_daquele_dia(plano):
    # A origem e o compara_com sao texto AAAA-MM-DD, como no cronograma da PMSC. As
    # revisoes seguem de um ciclo para o outro: na semana 9 ainda sao do Ciclo 1.
    por_data = {d.data.isoformat(): d for d in plano.dias}
    revisoes = [(dia, f) for dia in _uteis(plano) for f in dia.noite if f.tipo == "revisao"]
    assert revisoes
    for dia, faixa in revisoes:
        semanas = {"R+7": 1, "R+30": 4}[faixa.rotulo]
        origem = por_data[faixa.origem]
        assert faixa.origem == (dia.data - timedelta(weeks=semanas)).isoformat()
        temas = {f.titulo for f in origem.manha if f.tipo == "teoria"}
        assert faixa.titulo.removeprefix(f"{faixa.rotulo}: ") in temas
    na_semana_9 = {f.materia for dia, f in revisoes if dia.semana == 9}
    assert na_semana_9 <= CICLO_1


def test_o_sabado_mede_na_semana_1_e_na_16_e_treina_no_meio(plano):
    sabados = _sabados(plano)
    rodadas = [next(f for f in s.manha if f.questoes) for s in sabados]
    assert rodadas[0].tipo == "diagnostico" and rodadas[0].questoes == 120
    assert rodadas[-1].tipo == "simulado" and not rodadas[-1].treino and rodadas[-1].questoes == 120
    assert rodadas[-1].compara_com == sabados[0].data.isoformat()
    assert all(r.treino for r in rodadas[1:-1])
    # No Ciclo 1 o simulado de treino so cobra as materias do Ciclo 1.
    assert all(set(r.materias_da_rodada) == CICLO_1 for r in rodadas[1:SEMANAS_DO_CICLO])
    assert all(len(r.materias_da_rodada) == 14 for r in rodadas[SEMANAS_DO_CICLO:])


def test_todo_sabado_tem_redacao_com_um_tema_do_redacao_yml(plano):
    temas = {t["tema"] for t in yaml.safe_load(REDACAO.read_text(encoding="utf-8"))["temas"]}
    for sabado in _sabados(plano):
        redacao = [f for f in sabado.manha if f.materia == "Redação"]
        assert len(redacao) == 1, sabado.data
        assert redacao[0].titulo.removeprefix("Redação da semana: ") in temas, sabado.data

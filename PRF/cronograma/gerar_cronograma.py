# Gera o PRF/config/cronograma.yml dos Ciclos 1 e 2 (PRF-38): 16 semanas a partir de
# 04/01/2027, com as materias divididas ao meio para cada assunto ter tempo.
#   - Ciclo 1 (semanas 1 a 8): Transito, Portugues e os Direitos do Bloco III - 83 dos 120
#     itens da prova de 2021, a metade que vale mais pontos.
#   - Ciclo 2 (semanas 9 a 16): Espanhol, Informatica, Raciocinio, Fisica, Etica e
#     Geopolitica (mais duas aulas de Portugues), e toda manha fecha com 15 itens de
#     manutencao do Ciclo 1.
# Duas teorias por dia util, revisoes R+7 e R+30 (4 semanas), Portugues toda noite, e
# sabado com simulado e redacao. A logica esta em docs/metodo.md; os numeros, aqui.
#
# Como rodar (da raiz do projeto, com o banco data/radar.db):
#   .venv\Scripts\python.exe PRF/cronograma/gerar_cronograma.py
# Grava o PRF/config/cronograma.yml por cima (o que foi editado a mao nele se perde) e
# imprime as aulas com a incidencia de cada uma, para conferir.
import json, sqlite3, sys, collections
from datetime import date, timedelta
from pathlib import Path
import yaml
sys.stdout.reconfigure(encoding="utf-8")
from radar import leis
from radar.questoes import chave_da_questao

RAIZ = Path(".")
SAIDA = RAIZ / "PRF/config/cronograma.yml"
INICIO = date(2027, 1, 4)
SEMANAS_DO_CICLO = 8
SEMANAS = 2 * SEMANAS_DO_CICLO
DIAS_UTEIS_DO_CICLO = SEMANAS_DO_CICLO * 5

# --- o peso: os itens de cada materia na prova de 2021 (docs/prioridade.md) -------------
ITENS_2021 = {
    "Legislação de Trânsito": 30, "Língua Portuguesa": 18, "Língua Estrangeira (Inglês ou Espanhol)": 8,
    "Informática": 7, "Direito Administrativo": 7, "Direito Constitucional": 7,
    "Raciocínio Lógico-Matemático": 6, "Legislação Especial": 6, "Ética e Cidadania": 6,
    "Física": 5, "Direito Penal": 5, "Direito Processual Penal": 5, "Direitos Humanos": 5, "Geopolítica": 5,
}
DIREITOS = ["Direito Constitucional", "Direito Administrativo", "Legislação Especial", "Direito Penal",
            "Direito Processual Penal", "Direitos Humanos"]
BLOCO = {m: "II" if m == "Legislação de Trânsito" else ("III" if m in DIREITOS else "I") for m in ITENS_2021}
# A meta de acertos: a mediana de certos de quem passou em 2019, por bloco (docs/aprovados_prf.md).
ACERTO_DO_BLOCO = {"I": 37 / 50, "II": 36 / 40, "III": 26 / 30}
MATERIAS_DO_CICLO_1 = ["Legislação de Trânsito", "Língua Portuguesa"] + DIREITOS
MATERIAS_DA_PROVA = list(ITENS_2021)
DO_ZERO = {"Física", "Geopolítica", "Língua Estrangeira (Inglês ou Espanhol)", "Raciocínio Lógico-Matemático"}

arvore = json.load(open("data/conteudos.json", encoding="utf-8"))
filhos = collections.defaultdict(list)
for n in arvore:
    if not n.get("fora_do_edital") and n.get("pai"):
        filhos[n["pai"]].append(n["caminho"])


def ultimo(caminho: str) -> str:
    return caminho.split(" > ")[-1]


def no(*partes: str) -> str:
    """O caminho de um no pelo comeco do nome de cada nivel, para nao copiar os nomes
    longos da arvore: no("Direito Penal", "Crimes", "Crimes contra a pessoa"). Para com
    erro se o comeco nao achar exatamente um no."""
    caminho = partes[0]
    for parte in partes[1:]:
        achados = [f for f in filhos[caminho] if ultimo(f).startswith(parte)]
        assert len(achados) == 1, (caminho, parte, achados)
        caminho = achados[0]
    return caminho


def aula(titulo: str, conteudo: str, *nos: str, parte: str | None = None) -> dict:
    """Uma teoria: o titulo (e o tema: a ficha e as revisoes acham o tema por ele), o no
    da arvore e, quando o tema junta mais de um no, a lista deles. `parte` diz que o
    tema e um pedaco de um capitulo maior."""
    a = {"titulo": titulo, "conteudo": conteudo}
    if nos:
        a["nos"] = list(nos)
    if parte:
        a["parte"] = parte
    return a


def so(caminho: str) -> dict:
    """A teoria de um no so, com o nome dele de titulo (como no Ciclo 1 antigo)."""
    return aula(ultimo(caminho), caminho)


# --- os nos que mais se repetem ------------------------------------------------------
T = "Legislação de Trânsito"
CTB = no(T, "Lei nº 9.503/1997")
RESOLUCOES = no(T, "Resoluções do Conselho")
cap = lambda nome: no(T, "Lei nº 9.503/1997", nome)
res = lambda *numeros: [no(T, "Resoluções do Conselho", n) for n in numeros]
P = "Língua Portuguesa"
COMPREENSAO = no(P, "Compreensão e interpretação")
MORFO = no(P, "Domínio da estrutura morfossintática")
COESAO = no(P, "Domínio dos mecanismos de coesão")
morfo = lambda nome: no(P, "Domínio da estrutura morfossintática", nome)
DC, DA, DP, PP, LE, DH = DIREITOS[0], DIREITOS[1], "Direito Penal", "Direito Processual Penal", "Legislação Especial", "Direitos Humanos"
DF = no(DC, "Fundamentos constitucionais")
DEFESA = no(DC, "Defesa do Estado")
CRIMES = no(DP, "Crimes")
PROVA = no(PP, "Prova")
PRISAO = no(PP, "Prisão")
ESPANHOL = no("Língua Estrangeira (Inglês ou Espanhol)", "Língua Espanhola")
ES_COMP, ES_GRAM = no(ESPANHOL, "Compreensão"), no(ESPANHOL, "Itens gramaticais")
I, R, F, E, G = "Informática", "Raciocínio Lógico-Matemático", "Física", "Ética e Cidadania", "Geopolítica"

# --- as aulas de cada ciclo, na ordem em que entram na materia ------------------------
# A ordem e a da incidencia (provas da PRF + 0,25 x as outras do Cebraspe), salvo onde a
# materia pede outra (Fisica e Raciocinio, do zero, vao na ordem do conteudo). O que
# tinha uma aula so no Ciclo 1 antigo e continua inteiro aqui manteve o titulo: a ficha
# dele (data/fichas.json) continua valendo.
CICLO_1 = {
    T: [
        aula("Resoluções do CONTRAN: cargas e passageiros (552/2015, 349/2010 e 508/2014)",
             RESOLUCOES, *res("552/2015", "349/2010", "508/2014")),
        aula("CTB, crimes de trânsito 1: disposições gerais (arts. 291 a 301)", cap("Capítulo XIX -"), parte="1 de 2"),
        aula("CTB, Sistema Nacional de Trânsito 1: composição, Contran, Cetran e JARI (arts. 5º a 19)",
             cap("Capítulo II -"), parte="1 de 2"),
        aula("CTB, infrações 1 (arts. 161 a 190)", cap("Capítulo XV -"), parte="1 de 3"),
        aula("Resoluções do CONTRAN: cronotacógrafo e tempo de direção (92/1998 e 525/2015)",
             RESOLUCOES, *res("92/1998", "525/2015")),
        aula("CTB, normas gerais de circulação e conduta 1 (arts. 26 a 45)", cap("Capítulo III -"), parte="1 de 2"),
        aula("CTB, crimes de trânsito 2: os crimes em espécie (arts. 302 a 312-B)", cap("Capítulo XIX -"), parte="2 de 2"),
        aula("CTB, Sistema Nacional de Trânsito 2: PRF, órgãos rodoviários, estados e municípios (arts. 20 a 25-A)",
             cap("Capítulo II -"), parte="2 de 2"),
        aula("Resoluções do CONTRAN: capacete, para-brisa e vidros (453/2013, 216/2006 e 254/2007)",
             RESOLUCOES, *res("453/2013", "216/2006", "254/2007")),
        aula("CTB, infrações 2 (arts. 191 a 220)", cap("Capítulo XV -"), parte="2 de 3"),
        aula("CTB, " + ultimo(cap("Capítulo III-A")), cap("Capítulo III-A")),
        aula("CTB, " + ultimo(cap("Capítulo XVI -")), cap("Capítulo XVI -")),
        aula("Resoluções do CONTRAN: fiscalização de velocidade e videomonitoramento (798/2020 e 471/2013)",
             RESOLUCOES, *res("798/2020", "471/2013")),
        aula("CTB, normas gerais de circulação e conduta 2 (arts. 46 a 67)", cap("Capítulo III -"), parte="2 de 2"),
        aula("CTB, infrações 3 (arts. 221 a 255)", cap("Capítulo XV -"), parte="3 de 3"),
        aula("Resoluções do CONTRAN: pesos e dimensões (210/2011)", RESOLUCOES, *res("210/2011")),
        aula("CTB, " + ultimo(cap("Capítulo XVII -")), cap("Capítulo XVII -")),
        aula("CTB, Capítulos XIII e XIII-A: escolares e moto-frete (arts. 136 a 139-B)", CTB,
             cap("Capítulo XIII -"), cap("Capítulo XIII-A")),
        aula("CTB, " + ultimo(cap("Capítulo IX -")), cap("Capítulo IX -")),
        aula("Resoluções do CONTRAN: multas, suspensão e cassação (619/2016 e 723/2018)",
             RESOLUCOES, *res("619/2016", "723/2018")),
        aula("CTB, Capítulos VII e VIII: sinalização, engenharia de tráfego, fiscalização e policiamento (arts. 80 a 95)",
             CTB, cap("Capítulo VII -"), cap("Capítulo VIII -")),
        aula("CTB, disposições finais (arts. 313 a 341) e a Lei nº 5.970/1973", cap("Capítulo XX -"),
             cap("Capítulo XX -"), no(T, "Lei nº 5.970/1973")),
        aula("CTB, " + ultimo(cap("Capítulo XIV -")), cap("Capítulo XIV -")),
        aula("Resoluções do CONTRAN: fiscalização (MBFT) e placas (561/2015 e 780/2019)",
             RESOLUCOES, *res("561/2015", "780/2019")),
        aula("CTB, " + ultimo(cap("Capítulo XVIII -")), cap("Capítulo XVIII -")),
        aula("CTB, Capítulos I, IV, V e VI: disposições preliminares, pedestres, cidadão e educação (arts. 1º a 4º e 68 a 79)",
             CTB, cap("Capítulo I -"), cap("Capítulo IV -"), cap("Capítulo V -"), cap("Capítulo VI -")),
        aula("Resoluções do CONTRAN 292/2008 e 809/2020", RESOLUCOES, *res("292/2008", "809/2020")),
        aula("CTB, Capítulos X, XI e XII: circulação internacional, registro e licenciamento (arts. 118 a 135)",
             CTB, cap("Capítulo X -"), cap("Capítulo XI -"), cap("Capítulo XII -")),
    ],
    P: [
        aula("Interpretação de texto 1: a ideia central e as inferências", COMPREENSAO),
        aula("Pontuação", morfo("Emprego dos sinais de pontuação")),
        aula("Interpretação de texto 2: o que o texto diz x o que não diz", COMPREENSAO),
        aula("Concordância verbal e nominal", morfo("Concordância")),
        aula("Reescrita de frases e parágrafos", no(P, "Reescrita")),
        aula("Regência e crase", MORFO, morfo("Regência"), morfo("Emprego do sinal indicativo de crase")),
        aula("Coesão: referência e conectores", COESAO),
        aula("Classes de palavras e emprego de tempos e modos verbais", MORFO,
             morfo("Emprego das classes"), no(P, "Domínio dos mecanismos de coesão", "Emprego de tempos")),
        aula("Coordenação, subordinação e colocação pronominal", MORFO,
             morfo("Relações de coordenação"), morfo("Relações de subordinação"), morfo("Colocação")),
        aula("Correspondência oficial (Manual de Redação da Presidência)", no(P, "Correspondência oficial")),
    ],
    DC: [
        aula("Direitos e deveres individuais e coletivos (art. 5º)", DF,
             no(DF, "Direitos e deveres individuais"), no(DF, "Direito à vida")),
        aula("Garantias e remédios constitucionais (art. 5º)", DF,
             no(DF, "Garantias constitucionais individuais"), no(DF, "Remédios"), no(DF, "Garantias dos direitos coletivos")),
        aula("Segurança pública e a PRF (art. 144 da CF)", DEFESA,
             no(DEFESA, "Segurança pública"), no(DEFESA, "Organização da segurança"), no(DEFESA, "Atribuições")),
        aula("Direitos sociais, nacionalidade e direitos políticos", no(DF, "Direitos sociais")),
        aula("Estado de defesa, estado de sítio e Forças Armadas", DEFESA,
             no(DEFESA, "Estado de defesa"), no(DEFESA, "Forças Armadas")),
        so(no(DC, "Poder Executivo")),
        so(no(DC, "Ordem social")),
        so(no(DC, "Poder constituinte")),
    ],
    DA: [so(no(DA, nome)) for nome in ("Agentes públicos", "Poderes administrativos", "Noções de organização",
                                       "Responsabilidade civil", "Licitação", "Ato administrativo",
                                       "Controle da Administração", "Regime jurídico")],
    DP: [
        so(no(DP, "Princípios básicos")),
        aula("Crimes contra a Administração Pública e contra a fé pública", CRIMES,
             no(CRIMES, "Crimes contra a Administração"), no(CRIMES, "Crimes contra a fé")),
        aula("Crimes contra a pessoa e contra a dignidade sexual", CRIMES,
             no(CRIMES, "Crimes contra a pessoa"), no(CRIMES, "Crimes contra a dignidade")),
        so(no(DP, "Aplicação da lei penal")),
        aula("Crimes contra o patrimônio e contra a incolumidade pública", CRIMES,
             no(CRIMES, "Crimes contra o patrimônio"), no(CRIMES, "Crimes contra a incolumidade")),
        so(no(DP, "Tipicidade")),
        aula("Ilicitude e culpabilidade", no(DP, "Ilicitude"), no(DP, "Ilicitude"), no(DP, "Culpabilidade")),
    ],
    PP: [
        aula("Prisão em flagrante", no(PRISAO, "Prisão em flagrante")),
        aula("Prova: meios de prova e busca e apreensão", PROVA, no(PROVA, "Meios de prova"), no(PROVA, "Busca e apreensão")),
        so(no(PP, "Ação penal")),
        aula("Prova: conceito, ônus, provas ilícitas e local de crime", PROVA,
             no(PROVA, "Conceito"), no(PROVA, "Preservação"), no(PROVA, "Requisitos"), no(PROVA, "Provas ilícitas"),
             no(PROVA, "Valoração")),
        aula("Prisão: espécies, formalidades e mandado", no(PRISAO, "Conceito")),
        aula("Diligências investigatórias, identificação criminal e termo circunstanciado", no(PP, "Diligências"),
             no(PP, "Diligências"), no(PP, "Identificação Criminal"), no(PP, "Termo Circunstanciado")),
    ],
    LE: [
        so(no(LE, "Lei nº 8.069/1990")),
        so(no(LE, "Lei nº 11.343/2006")),
        so(no(LE, "Lei nº 13.869/2019")),
        aula("Lei nº 9.455/1997 (tortura) e Lei nº 8.072/1990 (crimes hediondos)", no(LE, "Lei nº 9.455/1997"),
             no(LE, "Lei nº 9.455/1997"), no(LE, "Lei nº 8.072/1990")),
        so(no(LE, "Lei nº 10.826/2003")),
        so(no(LE, "Lei nº 5.553/1968")),
        so(no(LE, "Lei nº 9.605/1998")),
        so(no(LE, "Lei nº 12.850/2013")),
        so(no(LE, "Lei nº 9.099/1995")),
        aula("Lei nº 13.675/2018 (SUSP), Decreto nº 1.655/1995 e art. 47 do Decreto nº 9.662/2019",
             no(LE, "Lei nº 13.675/2018"), no(LE, "Lei nº 13.675/2018"), no(LE, "Decreto nº 1.655/1995")),
    ],
    DH: [so(no(DH, "Direitos humanos na Constituição")), so(no(DH, "Convenção Americana")),
         so(no(DH, "Declaração Universal"))],
}

INFO_FERRAMENTAS = no(I, "Conceitos e modos de utilização")
SEGURANCA = no(I, "Conceitos de proteção")
FUNCAO = no(R, "Noção de função")
SEQUENCIAS = no(R, "Regularidades")
CONTAGEM = no(R, "Noções básicas de contagem")
DADOS = no(R, "Descrição e análise de dados")
METRICA = no(R, "Métrica")
CINEMATICA = no(F, "Cinemática")
CIRCULAR = no(F, "Movimento circular")
NEWTON = no(F, "Leis de Newton")
SETOR_PUBLICO = no(E, "Ética no setor público")
CIDADANIA = no(E, "Ética e democracia")

CICLO_2 = {
    P: [
        aula("Interpretação de texto 3: tipos e gêneros textuais", COMPREENSAO, COMPREENSAO, no(P, "Reconhecimento de tipos")),
        aula("Ortografia oficial e acentuação gráfica", no(P, "Domínio da ortografia")),
    ],
    "Língua Estrangeira (Inglês ou Espanhol)": [
        aula(f"Espanhol {k}: " + ("compreensão de texto" if k % 2 else "itens gramaticais do texto"),
             ES_COMP if k % 2 else ES_GRAM) for k in range(1, 17)],
    I: [
        so(INFO_FERRAMENTAS),
        so(SEGURANCA),
        so(no(SEGURANCA, "Noções de vírus")),
        so(no(SEGURANCA, "Aplicativos para segurança")),
        so(no(I, "Transformação digital")),
        so(no(I, "Transformação digital", "Inteligência artificial")),
        so(no(I, "Computação na nuvem")),
        aula("Navegadores, correio eletrônico, grupos de discussão e busca", no(INFO_FERRAMENTAS, "Ferramentas")),
        so(no(INFO_FERRAMENTAS, "Noções de sistema operacional")),
        aula("Internet e intranet; acesso a distância e transferência de arquivos", no(I, "Conceito de internet"),
             no(I, "Conceito de internet"), no(INFO_FERRAMENTAS, "Acesso a distância")),
    ],
    R: [
        so(no(R, "Noções básicas de teoria dos conjuntos")),
        so(no(R, "Porcentagem")),
        so(no(R, "Taxas de variação")),
        so(no(R, "Modelagem")),
        so(FUNCAO),
        so(no(FUNCAO, "Funções afim")),
        so(SEQUENCIAS),
        so(no(SEQUENCIAS, "Progressão")),
        so(CONTAGEM),
        so(no(CONTAGEM, "Análise combinatória")),
        aula("Análise combinatória, parte 2", no(CONTAGEM, "Análise combinatória")),
        so(no(CONTAGEM, "Probabilidade")),
        aula("Probabilidade, parte 2", no(CONTAGEM, "Probabilidade")),
        so(no(DADOS, "Leitura e interpretação")),
        so(no(DADOS, "Cálculo de médias")),
        so(no(METRICA, "Áreas e volumes")),
        so(METRICA),
        so(no(R, "Análise e interpretação de diferentes")),
    ],
    F: [
        so(CINEMATICA),
        aula("Movimento uniformemente variado", CINEMATICA),
        so(no(CINEMATICA, "Queda livre")),
        aula("Cinemática vetorial", CINEMATICA),
        so(CIRCULAR),
        aula("Movimento circular, parte 2", CIRCULAR),
        so(NEWTON),
        so(no(NEWTON, "Segunda lei")),
        aula("Terceira lei de Newton e força elástica (lei de Hooke)", NEWTON,
             no(NEWTON, "Terceira lei"), no(NEWTON, "Força elástica")),
        aula("Leis de Newton, parte 2: atrito e plano inclinado", NEWTON),
        so(no(F, "Trabalho")),
        so(no(F, "Energia cinética")),
        so(no(F, "Potência")),
        so(no(F, "Conservação de energia")),
        so(no(F, "Quantidade de movimento")),
        so(no(F, "Colisões")),
    ],
    E: [
        so(SETOR_PUBLICO),
        aula("Regras de conduta e promoção da ética no serviço público", no(SETOR_PUBLICO, "Promoção da ética")),
        aula("Moralidade administrativa e governança pública", SETOR_PUBLICO,
             no(SETOR_PUBLICO, "Princípios da Administração"), no(SETOR_PUBLICO, "Deveres dos servidores"),
             no(SETOR_PUBLICO, "Política de governança")),
        so(CIDADANIA),
        so(no(CIDADANIA, "Promoção da transparência")),
        so(no(CIDADANIA, "Tratamento de conflitos")),
        so(no(E, "Ética e moral")),
        aula("Ética, princípios e valores; integridade na função pública", no(E, "Ética, princípios"),
             no(E, "Ética, princípios"), no(E, "Ética e função pública")),
    ],
    G: [so(no(G, nome)) for nome in (
        "Rede de transporte", "A integração do Brasil", "Geografia e gestão ambiental", "A estrutura urbana",
        "Integração entre indústria", "A divisão inter-regional", "Macrodivisão natural", "Distribuição espacial",
        "O Brasil político", "Organização do Estado")],
}
for ciclo in (CICLO_1, CICLO_2):
    assert sum(len(v) for v in ciclo.values()) == DIAS_UTEIS_DO_CICLO * 2, {m: len(v) for m, v in ciclo.items()}
titulos = [a["titulo"] for ciclo in (CICLO_1, CICLO_2) for v in ciclo.values() for a in v]
assert len(titulos) == len(set(titulos)), "titulo repetido: o tema e achado pelo titulo"

# --- a incidencia de cada aula (para o detalhe e para conferir) -----------------------
c = sqlite3.connect("file:data/radar.db?mode=ro", uri=True)
evid = {}
for enun, alts, ev, anul in c.execute("select enunciado, alternativas, evidencia, anulada from questoes where evidencia in ('alvo','complementar')"):
    a = json.loads(alts)
    if a == {"c": "Certo", "e": "Errado"} and not anul:
        k = chave_da_questao(enun, a)
        if evid.get(k) != "alvo":
            evid[k] = ev
CLASSIFICADAS = [(conteudo, evid[chave]) for chave, conteudo, status in
                 c.execute("select chave, conteudo, status from classificacoes where principal=1")
                 if chave in evid and status != "pendente"]


def contagem(nos: list[str]) -> tuple[int, int]:
    """(alvo, complementar): os itens C/E classificados num dos nos ou abaixo deles."""
    alvo = comp = 0
    for conteudo, ev in CLASSIFICADAS:
        if any(conteudo == n or conteudo.startswith(n + " > ") for n in nos):
            alvo, comp = (alvo + 1, comp) if ev == "alvo" else (alvo, comp + 1)
    return alvo, comp


# --- a ordem dos dias: cada materia espalhada pelo ciclo (intercalar) ------------------
def pares_do_ciclo(ciclo: dict) -> list:
    slots = []
    for materia, lista in ciclo.items():
        for k, e in enumerate(lista):
            # A posicao ideal da k-esima aula, espalhada pelo ciclo (docs/metodo.md).
            slots.append(((k + 0.5) / len(lista), materia, e))
    slots.sort(key=lambda s: (s[0], -ITENS_2021[s[1]]))
    sequencia = [(m, e) for _, m, e in slots]
    # Pares (A, B) do dia: duas materias diferentes. A aula A tem 50 min e mais itens: vai
    # para o Transito e os Direitos; entre as do Bloco I, para Fisica e Raciocinio (do zero,
    # exercicio pede tempo); depois, para a de mais itens na prova.
    def prioridade(materia):
        return (BLOCO[materia] != "I", materia in (F, R), ITENS_2021[materia])

    pares = []
    while sequencia:
        a = sequencia.pop(0)
        j = next((i for i, s in enumerate(sequencia) if s[0] != a[0]), 0)
        b = sequencia.pop(j)
        assert a[0] != b[0], ("duas aulas da mesma materia no mesmo dia", a, b)
        if prioridade(b[0]) > prioridade(a[0]):
            a, b = b, a
        pares.append((a, b))
    assert len(pares) == DIAS_UTEIS_DO_CICLO
    return pares


pares = pares_do_ciclo(CICLO_1) + pares_do_ciclo(CICLO_2)


# --- textos --------------------------------------------------------------------------
def link_da_lei(materia, conteudo):
    # Nas Resolucoes do CONTRAN o texto nao e o do CTB: sem link, em vez do link errado.
    if conteudo.startswith(RESOLUCOES):
        return None
    lei = leis.da_materia(materia)
    return lei.url if lei else None


def detalhe_da_teoria(materia, e, minutos):
    alvo, comp = contagem(e.get("nos") or [e["conteudo"]])
    partes = [f"Teto de {minutos} min, uma fonte só: a ficha do radar (aba Fichas) e, se não entender, uma "
              "videoaula gratuita curta. Não releia nem grife: entendeu, feche e vá para as questões - testar-se "
              "fixa mais que reler (docs/metodo.md)."]
    if materia in DO_ZERO:
        partes.append("Matéria do zero: comece pelo conceito e por um exemplo resolvido.")
    elif link_da_lei(materia, e["conteudo"]):
        partes.append("Leia o texto da lei (o link): o Cebraspe cobra a letra.")
    elif e["conteudo"].startswith(RESOLUCOES):
        partes.append("Leia o texto vigente de cada resolução: várias foram revogadas e trocadas por outra "
                      "(docs/resolucoes_contran.md diz qual ler). O Cebraspe cobra a letra: o número, o prazo, a exceção.")
    if e.get("parte"):
        partes.append(f"Parte {e['parte']} deste capítulo: os itens de questão vêm do capítulo inteiro (o radar "
                      "não separa por artigo).")
    na_prf = ("não caiu item deste assunto" if alvo == 0 else
              "caiu 1 item deste assunto" if alvo == 1 else f"caíram {alvo} itens deste assunto")
    partes.append(f"Nas provas da PRF {na_prf}; nas outras do Cebraspe do radar, {comp}.")
    return " ".join(partes)


def com_nos(e: dict) -> dict:
    return {"nos": e["nos"]} if e.get("nos") else {}


def faixa_teoria(materia, e, minutos):
    f = {"tipo": "teoria", "duracao": minutos, "materia": materia, "conteudo": e["conteudo"],
         "titulo": e["titulo"], "detalhe": detalhe_da_teoria(materia, e, minutos), "onde": "videoaula", **com_nos(e)}
    if link_da_lei(materia, e["conteudo"]):
        f["link"] = link_da_lei(materia, e["conteudo"])
    return f


def faixa_fixacao(materia, e, n):
    return {"tipo": "questoes", "questoes": n, "materia": materia, "conteudo": e["conteudo"],
            "titulo": f"Fixação: {e['titulo']}",
            "detalhe": (f"{n} itens de Certo/Errado do tema, com a ficha aberta: fixam, não medem. Leia o painel de "
                        "explicação de cada item, no acerto e no erro."),
            "consulta": True, "onde": "radar", **com_nos(e)}


def faixa_aprendizagem(materia, e, n, rampa=None):
    # A primeira Aprendizagem da noite e a faixa da rampa: o numero de itens sai do nivel.
    return {"tipo": "questoes", "questoes": n, **({"rampa": rampa} if rampa else {}),
            "materia": materia, "conteudo": e["conteudo"],
            "titulo": f"Aprendizagem: {e['titulo']}",
            "detalhe": ("Os itens do tema da manhã, SEM consulta, como na prova. O que não souber, deixe em branco "
                        "(a regra do chute, Análises > Certo/Errado). É aqui que se vê o que ficou."),
            "consulta": False, "onde": "radar", **com_nos(e)}


def faixa_revisao(rotulo, origem, materia, e, n):
    return {"tipo": "revisao", "rotulo": rotulo, "origem": origem.isoformat(), "questoes": n,
            "materia": materia, "conteudo": e["conteudo"], "titulo": f"{rotulo}: {e['titulo']}",
            "detalhe": (f"Revisão espaçada: {n} itens do tema estudado em {origem:%d/%m}, sem consulta e sem reler "
                        "antes - o teste é a revisão (docs/metodo.md)."),
            "onde": "radar", **com_nos(e)}


def faixa_manutencao(materia):
    return {"tipo": "questoes", "questoes": 15, "materia": materia, "materia_inteira": True,
            "titulo": f"Manutenção do Ciclo 1: {materia}",
            "detalhe": ("15 itens de toda a matéria, sem consulta: é o que segura o Ciclo 1 enquanto o Ciclo 2 anda. "
                        "O que errar vai para o caderno de erros e volta na revisão."),
            "consulta": False, "onde": "radar"}


# A manutencao do Ciclo 1, nas manhas do Ciclo 2: Transito na segunda, na quarta e na
# sexta (30 dos 83 itens do Ciclo 1), e um Direito na terca e na quinta, em rodizio.
def materia_da_manutencao(dia_da_semana: int, vez_do_direito: int) -> str:
    return T if dia_da_semana in (0, 2, 4) else DIREITOS[vez_do_direito % len(DIREITOS)]


PAUSA = {"tipo": "pausa", "duracao": 10, "titulo": "Pausa", "detalhe": "Levante, beba água, sem celular."}
PORTUGUES = {"tipo": "questoes", "questoes": 10, "materia": "Língua Portuguesa", "materia_inteira": True,
             "titulo": "Português Cebraspe: interpretação e gramática",
             "detalhe": ("10 itens de Português de toda a matéria, sem consulta. Todo dia: o Bloco I é o que separa os "
                         "aprovados (docs/aprovados_prf.md)."), "onde": "radar"}
CORRECAO = {"tipo": "correcao", "duracao": 25, "titulo": "Correção",
            "detalhe": ("Na Revisão de cada rodada, leia a explicação dos erros e dos chutes; diga por que a certa é "
                        "certa antes de ler. No caderno de erros, uma regra por tema que você errou hoje.")}

PADRAO_2019 = "https://cdn.cebraspe.org.br/concursos/PRF_18/arquivos/PRF_18___PADRO_DE_RESPOSTAS_DEFINITIVO.PDF"
PADRAO_2021 = "https://cdn.cebraspe.org.br/concursos/PRF_21/arquivos/PRF_21_PADRAO_DE_RESPOSTA_DEFINITIVO.PDF"
# Os temas da redacao de sabado: o titulo e IGUAL ao `tema` do PRF/config/redacao.yml
# (a aba acha o tema, os textos motivadores e os quesitos por ele; PRF-37).
TEMAS = [
    ("As infrações de trânsito nas rodovias federais: o papel da PRF, da sociedade e do indivíduo",
     "o tema da discursiva da PRF de 2019, com outras palavras", PADRAO_2019),
    ("O uso do celular ao volante e a segurança nas rodovias federais", "tema proposto pelo Claude", None),
    ("A fiscalização eletrônica de velocidade e a redução dos sinistros de trânsito", "tema proposto pelo Claude", None),
    ("O transporte rodoviário de cargas e a segurança viária", "tema proposto pelo Claude", None),
    ("A educação para o trânsito como política pública", "tema proposto pelo Claude", None),
    ("Os crimes de trânsito, a Lei Seca e os sinistros nas rodovias",
     "o tema da discursiva da PRF de 2021, com outras palavras", PADRAO_2021),
    ("A proteção de crianças e adolescentes nas rodovias federais", "tema proposto pelo Claude", None),
    ("A preservação do meio ambiente e o transporte nas rodovias federais", "tema proposto pelo Claude", None),
    ("Os direitos humanos e a atuação da Polícia Rodoviária Federal", "tema proposto pelo Claude", None),
    ("Pedestres, ciclistas e motociclistas: os mais vulneráveis nas rodovias", "tema proposto pelo Claude", None),
]
# Semanas 1 a 6: os temas 1 a 6. Semanas 7 a 12: a 2a versao deles (reescrever um tema
# depois da correcao e o "revisar e editar" do docs/metodo.md). Semanas 13 a 16: temas novos.
REESCRITA = range(7, 13)


def tema_da_semana(semana: int) -> int:
    """O indice em TEMAS: 1 a 6 -> 0 a 5; 7 a 12 -> 0 a 5 de novo; 13 a 16 -> 6 a 9."""
    return semana - 1 if semana <= 6 else semana - 7


def faixa_redacao(semana):
    tema, origem, padrao = TEMAS[tema_da_semana(semana)]
    if semana in REESCRITA:
        primeira = INICIO + timedelta(weeks=semana - 7, days=5)
        abertura = (f"2ª versão do tema de {primeira:%d/%m}: escreva de novo, sem olhar a primeira, usando o que a "
                    "correção apontou; depois compare as duas notas na aba Redação.")
    else:
        abertura = f"É {origem}: a proposta, os textos motivadores e os três aspectos estão na aba Redação."
    f = {"tipo": "portugues", "duracao": 60, "cronometrado": True, "materia": "Redação",
         "titulo": f"Redação da semana: {tema}",
         "detalhe": (abertura + " 10 min de roteiro (um parágrafo para cada aspecto), 40 min escrevendo à mão até 30 "
                     "linhas, 10 min revisando pontuação e acento. Correção: a foto da folha no Claude Code, com "
                     "\"corrige a redação\" (Cebraspe: NPD = NC - 4 x NE/TL; um conceito de 0 a 3 por aspecto; "
                     "abaixo de 10 elimina)."
                     + (" Depois, compare com o padrão de resposta definitivo (o link)." if padrao else ""))}
    if padrao:
        f["link"] = padrao
    return f


def faixa_sabado(semana, data_do_diagnostico):
    if semana == 1:
        return {"tipo": "diagnostico", "questoes": 120, "min_por_questao": 1.75, "cronometrado": True,
                "materias_da_rodada": MATERIAS_DA_PROVA, "onde": "radar",
                "titulo": "Diagnóstico: 120 itens, como a prova",
                "detalhe": ("O ponto de partida, sem consulta e sem estudar antes: 120 itens de todas as matérias, "
                            "divididos como a prova de 2021, cronometrado (3h30, e a redação depois: a prova teve 4h30 "
                            "para as duas). Deixe em branco o que não souber. As questões saem da regra das rodadas que "
                            "medem (as provas da PRF primeiro, pela incidência); o fechamento do Ciclo 2 usa a mesma "
                            "regra, sem repetir questão, para comparar. Faça às 14h se puder: a prova é à tarde.")}
    if semana == SEMANAS:
        return {"tipo": "simulado", "questoes": 120, "min_por_questao": 1.75, "cronometrado": True,
                "materias_da_rodada": MATERIAS_DA_PROVA, "onde": "radar", "compara_com": data_do_diagnostico,
                "titulo": "Fechamento dos Ciclos 1 e 2: 120 itens, comparado com o diagnóstico",
                "detalhe": ("A mesma regra do diagnóstico, sem repetir questão: a diferença entre os dois diz o que os "
                            "dois ciclos deram, bloco a bloco. Cronometrado, sem consulta, redação depois. Às 14h se "
                            "puder.")}
    if semana <= SEMANAS_DO_CICLO:
        anteriores = 40 if semana == SEMANAS_DO_CICLO else 20
        titulo = ("Simulado do fim do Ciclo 1: 60 itens" if semana == SEMANAS_DO_CICLO
                  else "Simulado da semana: 60 itens")
        return {"tipo": "simulado", "questoes": 60, "min_por_questao": 1.75, "cronometrado": True, "treino": True,
                "anteriores": anteriores, "materias_da_rodada": MATERIAS_DO_CICLO_1, "onde": "radar",
                "titulo": titulo,
                "detalhe": (f"{60 - anteriores} itens dos temas desta semana e {anteriores} das anteriores, só das "
                            "matérias do Ciclo 1, misturados, sem consulta e cronometrado. Treina, não mede: não entra "
                            "na comparação. Às 14h se puder.")}
    return {"tipo": "simulado", "questoes": 60, "min_por_questao": 1.75, "cronometrado": True, "treino": True,
            "anteriores": 30, "materias_da_rodada": MATERIAS_DA_PROVA, "onde": "radar",
            "titulo": "Simulado da semana: 60 itens",
            "detalhe": ("30 itens dos temas desta semana e 30 das anteriores (o Ciclo 1 entra aqui), misturados, sem "
                        "consulta e cronometrado. Treina, não mede: não entra na comparação. Às 14h se puder.")}


# --- os dias -------------------------------------------------------------------------
def pascoa(ano):
    a, b, cc = ano % 19, ano // 100, ano % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = cc // 4, cc % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return date(ano, mes, dia)


# A carga que sobe: a Aprendizagem A da noite tem 15 itens no nivel 1 (a semana 1) e 20 no
# nivel 2, e so sobe depois de uma semana cumprida (o gatilho).
RAMPA = {1: {"aprendizagem": 15}, 2: {"aprendizagem": 20}}

# Os feriados: neles a meta reduzida ja conta como dia cheio.
FERIADOS = {pascoa(2027) - timedelta(days=48): "Carnaval (segunda)",
            pascoa(2027) - timedelta(days=47): "Carnaval (terça)",
            pascoa(2027) - timedelta(days=2): "Sexta-feira Santa",
            date(2027, 4, 21): "Tiradentes"}

dias, por_indice = [], {}
indice = 0
vez_do_direito = 0
diagnostico = INICIO + timedelta(days=5)
for semana in range(1, SEMANAS + 1):
    segunda = INICIO + timedelta(weeks=semana - 1)
    ciclo = 1 if semana <= SEMANAS_DO_CICLO else 2
    for d in range(5):
        data = segunda + timedelta(days=d)
        (ma, ea), (mb, eb) = pares[indice]
        por_indice[indice] = ((ma, ea), (mb, eb), data)
        manha = [faixa_teoria(ma, ea, 50), faixa_fixacao(ma, ea, 15), PAUSA,
                 faixa_teoria(mb, eb, 40), faixa_fixacao(mb, eb, 12)]
        if ciclo == 2:
            materia = materia_da_manutencao(d, vez_do_direito)
            vez_do_direito += materia != T
            manha.append(faixa_manutencao(materia))
        # As revisoes seguem a conta dos dias uteis, de um ciclo para o outro: na semana 9,
        # o R+7 e o R+30 ainda sao de temas do Ciclo 1.
        noite = []
        if indice >= 5:
            (ra, rea), (rb, reb), rdata = por_indice[indice - 5]
            noite += [faixa_revisao("R+7", rdata, ra, rea, 10), faixa_revisao("R+7", rdata, rb, reb, 8)]
        if indice >= 20:
            (ra, rea), _, rdata = por_indice[indice - 20]
            noite.append(faixa_revisao("R+30", rdata, ra, rea, 10))
        noite += [faixa_aprendizagem(ma, ea, RAMPA[min(semana, 2)]["aprendizagem"], rampa="aprendizagem"), PAUSA,
                  faixa_aprendizagem(mb, eb, 10), PORTUGUES, CORRECAO]
        dia = {"data": data.isoformat(), "semana": semana,
               "reduzida": ("As duas teorias com a fixação e a Aprendizagem da noite." if ciclo == 2
                            else "A manhã inteira e a Aprendizagem da noite."),
               "minima": f"Só a teoria e a fixação de {ea['titulo']}."}
        if data in FERIADOS:
            dia["feriado"] = FERIADOS[data]
        dia.update({"manha": manha, "noite": noite})
        dias.append(dia)
        indice += 1
    sabado = segunda + timedelta(days=5)
    dias.append({"data": sabado.isoformat(), "semana": semana,
                 "manha": [faixa_sabado(semana, diagnostico.isoformat()), faixa_redacao(semana),
                           {**CORRECAO, "duracao": 30, "titulo": "Correção do sábado",
                            "detalhe": ("Na Revisão do simulado, passe pelos erros, chutes e em branco com a "
                                        "explicação aberta. A redação vai para o Claude Code.")}]})

fim_do_1 = INICIO + timedelta(weeks=SEMANAS_DO_CICLO - 1, days=5)
inicio_do_2 = fim_do_1 + timedelta(days=2)
fim = INICIO + timedelta(weeks=SEMANAS - 1, days=5)
plano = {
    "ciclo": 2,
    "titulo": "PRF — Ciclos 1 e 2 (16 semanas)",
    "inicio": INICIO.isoformat(),
    "fim": fim.isoformat(),
    "anki": "desativado",
    "meta_da_prova": {"acertos": sum(round(ITENS_2021[m] * ACERTO_DO_BLOCO[BLOCO[m]]) for m in ITENS_2021),
                      "nota_liquida": 83, "redacao": 17},
    "blocos": {"manha": {"nome": "Manhã — teoria e fixação", "inicio": "09:00"},
               "noite": {"nome": "Noite — revisão e questões", "inicio": "18:00"},
               "pos22": {"nome": "Depois das 22h", "inicio": "22:00"}},
    "minutos_por_questao": 2,
    "rampa": RAMPA,
    "gatilho": {"sobe_com_dias_na_ideal": 4, "semana_ruim_com_dias_abaixo": 3, "desce_apos_semanas_ruins": 2},
    "semanas": {
        1: "Começo do Ciclo 1 (Trânsito, Português e os Direitos): duas teorias por manhã, a Aprendizagem e o Português à noite. Sábado: o diagnóstico (120 itens de todas as matérias) e a 1ª redação.",
        2: "Entram as revisões R+7 à noite. Sábado: simulado de treino das matérias do Ciclo 1 e redação.",
        3: "Mesmo ritmo. Sábado: simulado de treino e redação.",
        4: "Mesmo ritmo. Sábado: simulado de treino e redação.",
        5: "Entra a revisão R+30 (4 semanas depois, no mesmo dia da semana) do que foi estudado na semana 1.",
        6: "Segunda e terça são de Carnaval (feriado: a meta reduzida conta como dia cheio). Sábado: simulado de treino e redação.",
        7: "Mesmo ritmo. No sábado, a redação passa a ser a 2ª versão de um tema já escrito.",
        8: "Última semana do Ciclo 1. Sábado: o simulado do fim do ciclo, com 40 dos 60 itens de semanas anteriores.",
        9: "Começa o Ciclo 2 (Espanhol, Informática, Raciocínio, Física, Ética e Geopolítica). Toda manhã fecha com 15 itens de manutenção do Ciclo 1, e as revisões do Ciclo 1 continuam à noite.",
        10: "Mesmo ritmo. Sábado: simulado de treino com metade dos itens de semanas anteriores (o Ciclo 1 junto) e redação.",
        11: "Mesmo ritmo. Sábado: simulado de treino e redação.",
        12: "Sexta é Sexta-feira Santa (feriado). Sábado: simulado de treino e a última 2ª versão de redação.",
        13: "A revisão R+30 passa a ser de temas do Ciclo 2. Sábado: tema novo de redação.",
        14: "Mesmo ritmo. Sábado: simulado de treino e tema novo de redação.",
        15: "Mesmo ritmo. Sábado: simulado de treino e tema novo de redação.",
        16: "Última semana (quarta é Tiradentes, feriado). Sábado: o fechamento, 120 itens de todas as matérias, comparado com o diagnóstico.",
    },
    "materias": [{"nome": m, "questoes": ITENS_2021[m], "meta": round(ITENS_2021[m] * ACERTO_DO_BLOCO[BLOCO[m]])}
                 for m in ITENS_2021],
    "materias_mistas": ["Redação"],
    "mapa": [
        {"nome": "Ciclo 1", "inicio": INICIO.isoformat(), "fim": fim_do_1.isoformat(),
         "foco": "Trânsito, Português e os Direitos do Bloco III: 83 dos 120 itens da prova de 2021, com tempo para cada assunto"},
        {"nome": "Ciclo 2", "inicio": inicio_do_2.isoformat(), "fim": fim.isoformat(),
         "foco": "Espanhol, Informática, Raciocínio, Física, Ética e Geopolítica, com a manutenção do Ciclo 1 toda manhã"},
        {"nome": "Depois do Ciclo 2, até o edital", "inicio": (fim + timedelta(days=2)).isoformat(),
         "foco": "Com o edital, o plano segue o edital; sem ele, um Ciclo 3 em cima dos erros e das revisões"},
        {"nome": "Reta final", "quando": "quando sair o edital (previsto para 2027)",
         "foco": "Com a data da prova: mais horas, domingo entra, simulado completo todo sábado"},
        {"nome": "Prova", "quando": "a data do edital", "foco": "120 itens e a discursiva"},
    ],
    "dias": dias,
}

CABECALHO = """# O cronograma da PRF, Ciclos 1 e 2, dia a dia, no formato do config/cronograma.yml do radar
# (lido pela tela Hoje e pelo `radar hoje`). Veja o comentario do topo de config/cronograma.yml
# para o que cada chave faz.
#
# PROCEDENCIA: gerado pelo Claude Code (claude-opus-5-5) em 26/11/2026 (PRF-38) por
# PRF/cronograma/gerar_cronograma.py, a partir de docs/prioridade.md (o peso: os itens de cada
# materia em 2021), da incidencia de cada assunto nas provas do radar (provas da PRF + 0,25 x
# as outras do Cebraspe), de docs/aprovados_prf.md (as metas) e de docs/metodo.md (o metodo).
# Pode editar a mao: e dado, nao codigo.
#
# A DIVISAO (PRF-38, pedido do Gabriel em 26/11/2026): as materias vao em duas metades de 8
# semanas, para cada assunto ter aula propria em vez de passar por todas por cima.
#   - Ciclo 1 (04/01 a 27/02): Transito, Portugues e os Direitos do Bloco III, 83 dos 120 itens;
#   - Ciclo 2 (01/03 a 24/04): Espanhol, Informatica, Raciocinio, Fisica, Etica e Geopolitica,
#     com 15 itens de manutencao do Ciclo 1 no fim de toda manha.
#
# A LOGICA (docs/metodo.md):
#   - manha: duas teorias curtas (50 e 40 min) de materias diferentes, cada uma seguida da
#     fixacao em itens de Certo/Errado com a ficha aberta - testar-se, e nao reler;
#   - noite: as revisoes espacadas (R+7 da semana 2 em diante, R+30 da semana 5: 4 semanas, o
#     rotulo que o radar conhece; seguem de um ciclo para o outro), a Aprendizagem sem consulta
#     dos temas da manha, o Portugues de todo dia e a correcao;
#   - sabado: o diagnostico (semana 1), o simulado de treino ou o fechamento (semana 16, comparado
#     com o diagnostico), cronometrados, e a redacao da semana; domingo e folga;
#   - a rampa: a primeira Aprendizagem da noite tem 15 itens no nivel 1 e 20 no nivel 2;
#     o gatilho sobe o nivel com 4 dias completos na semana e nenhum zerado.
#
# AS METAS: `meta` de cada materia = os itens dela x a mediana de CERTOS de quem passou
# em 2019, por bloco (37/50, 36/40 e 26/30: o unico edital que da os certos,
# docs/aprovados_prf.md); `meta_da_prova` traz tambem a nota liquida (83) e a
# discursiva (17,09) das 1.500 maiores notas de 2021.
"""


class SemAlias(yaml.SafeDumper):
    """Sem &id001/*id001 no arquivo: ele e para ler e editar a mao."""

    def ignore_aliases(self, data):
        return True


SAIDA.write_text(CABECALHO + "\n" + yaml.dump(plano, Dumper=SemAlias, allow_unicode=True, sort_keys=False,
                                               width=110), encoding="utf-8")
print("gravado", SAIDA, "| dias:", len(dias), "| fim do Ciclo 1:", fim_do_1, "| fim:", fim,
      "| feriados:", ", ".join(f"{d:%d/%m} {n}" for d, n in sorted(FERIADOS.items())))
for nome, ciclo in (("Ciclo 1", CICLO_1), ("Ciclo 2", CICLO_2)):
    print(f"\n{nome}: " + ", ".join(f"{m} {len(v)}" for m, v in ciclo.items()))
    for materia, lista in ciclo.items():
        for e in lista:
            alvo, comp = contagem(e.get("nos") or [e["conteudo"]])
            print(f"  {materia[:22]:22} PRF {alvo:2} outras {comp:3}  {e['titulo'][:90]}")

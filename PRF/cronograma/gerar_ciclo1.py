# Gera o PRF/config/cronograma.yml do Ciclo 1 (Etapa 5, PRF-35): 6 semanas a partir de
# 04/01/2027, duas teorias por dia util pela prioridade (peso da prova de 2021) e pela
# incidencia de cada assunto, revisoes R+7 e R+30 (4 semanas), Portugues todo dia, e sabado com
# simulado e redacao. A logica esta em docs/metodo.md; os numeros, no proprio arquivo.
#
# Como rodar (da raiz do projeto, com o banco data/radar.db):
#   .venv\Scripts\python.exe PRF/cronograma/filas_do_ciclo.py PRF/cronograma/filas.json
#   .venv\Scripts\python.exe PRF/cronograma/gerar_ciclo1.py PRF/cronograma/filas.json
# O primeiro conta a incidencia de cada assunto; o segundo monta o ciclo e grava o
# PRF/config/cronograma.yml por cima (o que foi editado a mao nele se perde). O filas.json
# e de passagem, fica fora do git. Para o Ciclo 2: copie este arquivo, troque INICIO,
# ENCONTROS e a escolha dos temas (os que ficaram para depois).
import json, sqlite3, sys, collections
from datetime import date, timedelta
from pathlib import Path
import yaml
sys.stdout.reconfigure(encoding="utf-8")
from radar import leis
from radar.questoes import chave_da_questao

RAIZ = Path(".")
filas = json.load(open(sys.argv[1], encoding="utf-8"))
SAIDA = RAIZ / "PRF/config/cronograma.yml"
INICIO = date(2027, 1, 4)
SEMANAS = 6
CTB = "Legislação de Trânsito > Lei nº 9.503/1997 (Código de Trânsito Brasileiro) e suas alterações, inclusive as da Lei nº 14.071/2020"
RESOLUCOES = "Legislação de Trânsito > Resoluções do Conselho Nacional de Trânsito (CONTRAN) e suas alterações"
ESPANHOL = "Língua Estrangeira (Inglês ou Espanhol) > Língua Espanhola"
MORFO = "Língua Portuguesa > Domínio da estrutura morfossintática do período"

# --- o peso: os itens de cada materia na prova de 2021 (docs/prioridade.md) -------------
ITENS_2021 = {
    "Legislação de Trânsito": 30, "Língua Portuguesa": 18, "Língua Estrangeira (Inglês ou Espanhol)": 8,
    "Informática": 7, "Direito Administrativo": 7, "Direito Constitucional": 7,
    "Raciocínio Lógico-Matemático": 6, "Legislação Especial": 6, "Ética e Cidadania": 6,
    "Física": 5, "Direito Penal": 5, "Direito Processual Penal": 5, "Direitos Humanos": 5, "Geopolítica": 5,
}
BLOCO = {m: "II" if m == "Legislação de Trânsito" else
         ("III" if m in ("Direito Administrativo", "Direito Constitucional", "Direito Penal",
                         "Direito Processual Penal", "Legislação Especial", "Direitos Humanos") else "I")
         for m in ITENS_2021}
# A meta de acertos: a mediana de certos de quem passou em 2019, por bloco (docs/aprovados_prf.md).
ACERTO_DO_BLOCO = {"I": 37 / 50, "II": 36 / 40, "III": 26 / 30}
# Os encontros de teoria do ciclo (60 = 2 por dia util): o peso da prova, mais um para
# quem comeca do zero (Fisica, Raciocinio) e um a menos onde ja houve estudo
# (docs/comparativo_pmsc_prf.md). Soma 60.
ENCONTROS = {
    "Legislação de Trânsito": 14, "Língua Portuguesa": 8, "Língua Estrangeira (Inglês ou Espanhol)": 4,
    "Física": 4, "Raciocínio Lógico-Matemático": 4, "Informática": 3, "Ética e Cidadania": 3,
    "Geopolítica": 3, "Direito Administrativo": 3, "Direito Constitucional": 3, "Direito Penal": 3,
    "Direito Processual Penal": 3, "Legislação Especial": 3, "Direitos Humanos": 2,
}
assert sum(ENCONTROS.values()) == SEMANAS * 5 * 2
DO_ZERO = {"Física", "Geopolítica", "Língua Estrangeira (Inglês ou Espanhol)", "Raciocínio Lógico-Matemático"}

arvore = json.load(open("data/conteudos.json", encoding="utf-8"))
filhos = collections.defaultdict(list)
for n in arvore:
    if not n.get("fora_do_edital") and n.get("pai"):
        filhos[n["pai"]].append(n["caminho"])


def ultimo(caminho: str) -> str:
    return caminho.split(" > ")[-1]


# --- a incidencia por resolucao do CONTRAN (para agrupar as tres manhas delas) ---------
c = sqlite3.connect("file:data/radar.db?mode=ro", uri=True)
evid = {}
for enun, alts, ev, anul in c.execute("select enunciado, alternativas, evidencia, anulada from questoes where evidencia in ('alvo','complementar')"):
    a = json.loads(alts)
    if a == {"c": "Certo", "e": "Errado"} and not anul:
        evid.setdefault(chave_da_questao(enun, a), ev)
CLASSIFICADAS = [(conteudo, evid[chave]) for chave, conteudo, status in
                 c.execute("select chave, conteudo, status from classificacoes where principal=1")
                 if chave in evid and status != "pendente"]


def contagem(nos: list[str]) -> tuple[int, int]:
    """(alvo, complementar): os itens classificados num dos nos ou abaixo deles."""
    alvo = comp = 0
    for conteudo, ev in CLASSIFICADAS:
        if any(conteudo == no or conteudo.startswith(no + " > ") for no in nos):
            alvo, comp = (alvo + 1, comp) if ev == "alvo" else (alvo, comp + 1)
    return alvo, comp


def incidencia(no: str) -> float:
    alvo, comp = contagem([no])
    return alvo + 0.25 * comp


resolucoes = sorted(filhos[RESOLUCOES], key=lambda r: -incidencia(r))


def nomes(grupo: list[str]) -> str:
    """"552/2015, 92/1998 e 349/2010": o numero de cada resolucao, sem o "exceto os anexos"."""
    curtos = [ultimo(r).replace(", exceto os anexos", "") for r in grupo]
    return ", ".join(curtos[:-1]) + " e " + curtos[-1]


# --- os encontros de cada materia: (titulo, conteudo, nos) -----------------------------
def encontros(materia: str) -> list[dict]:
    fila = [f["no"] for f in filas[materia]]
    n = ENCONTROS[materia]
    if materia == "Legislação de Trânsito":
        grupos = [resolucoes[0:5], resolucoes[5:10], resolucoes[10:15]]
        saida = [dict(titulo=f"Resoluções do CONTRAN {i + 1}: {nomes(g)}",
                      conteudo=RESOLUCOES, nos=g) for i, g in enumerate(grupos)]
        capitulos = [no for no in fila if no.startswith(CTB)]
        saida += [dict(titulo=f"CTB, {ultimo(no)}", conteudo=no) for no in capitulos[: n - 3]]
        return saida
    if materia == "Língua Portuguesa":
        comp = "Língua Portuguesa > Compreensão e interpretação de textos de gêneros variados"
        sub = {ultimo(s): s for s in filhos[MORFO]}
        return [
            dict(titulo="Interpretação de texto 1: a ideia central e as inferências", conteudo=comp),
            dict(titulo="Pontuação", conteudo=sub["Emprego dos sinais de pontuação"]),
            dict(titulo="Interpretação de texto 2: o que o texto diz x o que não diz", conteudo=comp),
            dict(titulo="Concordância verbal e nominal", conteudo=sub["Concordância verbal e nominal"]),
            dict(titulo="Reescrita de frases e parágrafos", conteudo="Língua Portuguesa > Reescrita de frases e parágrafos do texto"),
            dict(titulo="Regência e crase", conteudo=MORFO,
                 nos=[sub["Regência verbal e nominal"], sub["Emprego do sinal indicativo de crase"]]),
            dict(titulo="Coesão: referência e conectores", conteudo="Língua Portuguesa > Domínio dos mecanismos de coesão textual"),
            dict(titulo="Correspondência oficial (Manual de Redação da Presidência)",
                 conteudo="Língua Portuguesa > Correspondência oficial (conforme Manual de Redação da Presidência da República)"),
        ]
    if materia == "Língua Estrangeira (Inglês ou Espanhol)":
        comp, gram = filhos[ESPANHOL][0], filhos[ESPANHOL][1]
        return [dict(titulo=f"Espanhol {i + 1}: " + ("compreensão de texto" if no == comp else "itens gramaticais do texto"),
                     conteudo=no) for i, no in enumerate([comp, gram, comp, gram])]
    return [dict(titulo=ultimo(no), conteudo=no) for no in fila[:n]]


slots = []
for materia in ENCONTROS:
    lista = encontros(materia)
    assert len(lista) == ENCONTROS[materia], (materia, len(lista))
    for k, e in enumerate(lista):
        # A posicao ideal do k-esimo encontro, espalhado pelo ciclo (intercalar: docs/metodo.md).
        slots.append(((k + 0.5) / len(lista), materia, e))
slots.sort(key=lambda s: (s[0], -ITENS_2021[s[1]]))
sequencia = [(m, e) for _, m, e in slots]
# Pares (A, B) do dia: duas materias diferentes, e o tema de Direito ou de Transito primeiro.
pares = []
while sequencia:
    a = sequencia.pop(0)
    j = next((i for i, s in enumerate(sequencia) if s[0] != a[0]), 0)
    b = sequencia.pop(j)
    if BLOCO[a[0]] == "I" and BLOCO[b[0]] != "I":
        a, b = b, a
    pares.append((a, b))
assert len(pares) == SEMANAS * 5


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
        partes.append("Leia o texto de cada resolução: o Cebraspe cobra a letra (o número, o prazo, a exceção).")
    na_prf = ("não caiu item deste assunto" if alvo == 0 else
              "caiu 1 item deste assunto" if alvo == 1 else f"caíram {alvo} itens deste assunto")
    partes.append(f"Nas provas da PRF {na_prf}; nas outras do Cebraspe do radar, {comp}.")
    return " ".join(partes)


def faixa_teoria(materia, e, minutos):
    f = {"tipo": "teoria", "duracao": minutos, "materia": materia, "conteudo": e["conteudo"],
         "titulo": e["titulo"], "detalhe": detalhe_da_teoria(materia, e, minutos), "onde": "videoaula"}
    if e.get("nos"):
        f["nos"] = e["nos"]
    if link_da_lei(materia, e["conteudo"]):
        f["link"] = link_da_lei(materia, e["conteudo"])
    return f


def faixa_fixacao(materia, e, n):
    return {"tipo": "questoes", "questoes": n, "materia": materia, "conteudo": e["conteudo"],
            "titulo": f"Fixação: {e['titulo']}",
            "detalhe": (f"{n} itens de Certo/Errado do tema, com a ficha aberta: fixam, não medem. Leia o painel de "
                        "explicação de cada item, no acerto e no erro."),
            "consulta": True, "onde": "radar", **({"nos": e["nos"]} if e.get("nos") else {})}


def faixa_aprendizagem(materia, e, n, rampa=None):
    # A primeira Aprendizagem da noite e a faixa da rampa: o numero de itens sai do nivel.
    return {"tipo": "questoes", "questoes": n, **({"rampa": rampa} if rampa else {}),
            "materia": materia, "conteudo": e["conteudo"],
            "titulo": f"Aprendizagem: {e['titulo']}",
            "detalhe": ("Os itens do tema da manhã, SEM consulta, como na prova. O que não souber, deixe em branco "
                        "(a regra do chute, Análises > Certo/Errado). É aqui que se vê o que ficou."),
            "consulta": False, "onde": "radar", **({"nos": e["nos"]} if e.get("nos") else {})}


def faixa_revisao(rotulo, origem, materia, e, n):
    return {"tipo": "revisao", "rotulo": rotulo, "origem": origem.isoformat(), "questoes": n,
            "materia": materia, "conteudo": e["conteudo"], "titulo": f"{rotulo}: {e['titulo']}",
            "detalhe": (f"Revisão espaçada: {n} itens do tema estudado em {origem:%d/%m}, sem consulta e sem reler "
                        "antes - o teste é a revisão (docs/metodo.md)."),
            "onde": "radar", **({"nos": e["nos"]} if e.get("nos") else {})}


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
TEMAS = {
    1: ("As infrações de trânsito nas rodovias federais: o papel da PRF, da sociedade e do indivíduo",
        "o tema da discursiva da PRF de 2019, com outras palavras", PADRAO_2019),
    2: ("O uso do celular ao volante e a segurança nas rodovias federais", "tema proposto pelo Claude", None),
    3: ("A fiscalização eletrônica de velocidade e a redução dos sinistros de trânsito", "tema proposto pelo Claude",
        None),
    4: ("O transporte rodoviário de cargas e a segurança viária", "tema proposto pelo Claude", None),
    5: ("A educação para o trânsito como política pública", "tema proposto pelo Claude", None),
    6: ("Os crimes de trânsito, a Lei Seca e os sinistros nas rodovias",
        "o tema da discursiva da PRF de 2021, com outras palavras", PADRAO_2021),
}


def faixa_redacao(semana):
    tema, origem, padrao = TEMAS[semana]
    f = {"tipo": "portugues", "duracao": 60, "cronometrado": True, "materia": "Redação",
         "titulo": f"Redação da semana: {tema}",
         "detalhe": (f"É {origem}: a proposta, os textos motivadores e os três aspectos estão na aba Redação. "
                     "10 min de roteiro (um parágrafo para cada aspecto), 40 min escrevendo à mão até 30 linhas, "
                     "10 min revisando pontuação e acento. Correção: a foto da folha no Claude Code, com \"corrige "
                     "a redação\" (Cebraspe: NPD = NC - 4 x NE/TL; um conceito de 0 a 3 por aspecto; abaixo de 10 "
                     "elimina)."
                     + (" Depois, compare com o padrão de resposta definitivo (o link)." if padrao else ""))}
    if padrao:
        f["link"] = padrao
    return f


MATERIAS_DA_PROVA = list(ITENS_2021)


def faixa_sabado(semana, data_do_diagnostico):
    if semana == 1:
        return {"tipo": "diagnostico", "questoes": 120, "min_por_questao": 1.75, "cronometrado": True,
                "materias_da_rodada": MATERIAS_DA_PROVA, "onde": "radar",
                "titulo": "Diagnóstico: 120 itens, como a prova",
                "detalhe": ("O ponto de partida, sem consulta e sem estudar antes: 120 itens divididos como a prova de "
                            "2021, cronometrado (3h30, e a redação depois: a prova teve 4h30 para as duas). Deixe em "
                            "branco o que não souber. As questões saem da regra das rodadas que medem (as provas da PRF "
                            "primeiro, pela incidência); o fechamento da semana 6 usa a mesma regra, sem repetir "
                            "questão, para comparar. Faça às 14h se puder: a prova é à tarde.")}
    if semana == SEMANAS:
        return {"tipo": "simulado", "questoes": 120, "min_por_questao": 1.75, "cronometrado": True,
                "materias_da_rodada": MATERIAS_DA_PROVA, "onde": "radar", "compara_com": data_do_diagnostico,
                "titulo": "Fechamento do Ciclo 1: 120 itens, comparado com o diagnóstico",
                "detalhe": ("A mesma regra do diagnóstico, sem repetir questão: a diferença entre os dois diz o que o "
                            "ciclo deu, bloco a bloco. Cronometrado, sem consulta, redação depois. Às 14h se puder.")}
    return {"tipo": "simulado", "questoes": 60, "min_por_questao": 1.75, "cronometrado": True, "treino": True,
            "anteriores": 20, "materias_da_rodada": MATERIAS_DA_PROVA, "onde": "radar",
            "titulo": "Simulado da semana: 60 itens",
            "detalhe": ("40 itens dos temas desta semana e 20 das anteriores, misturados, sem consulta e cronometrado. "
                        "Treina, não mede: não entra na comparação do ciclo. Às 14h se puder.")}


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

CARNAVAL = {pascoa(2027) - timedelta(days=48): "Carnaval (segunda)", pascoa(2027) - timedelta(days=47): "Carnaval (terça)"}

dias, por_indice = [], {}
indice = 0
diagnostico = INICIO + timedelta(days=5)
for semana in range(1, SEMANAS + 1):
    segunda = INICIO + timedelta(weeks=semana - 1)
    for d in range(5):
        data = segunda + timedelta(days=d)
        (ma, ea), (mb, eb) = pares[indice]
        por_indice[indice] = ((ma, ea), (mb, eb), data)
        manha = [faixa_teoria(ma, ea, 50), faixa_fixacao(ma, ea, 15), PAUSA,
                 faixa_teoria(mb, eb, 40), faixa_fixacao(mb, eb, 12)]
        noite = []
        if indice >= 5:
            (ra, rea), (rb, reb), rdata = por_indice[indice - 5]
            noite += [faixa_revisao("R+7", rdata, ra, rea, 10), faixa_revisao("R+7", rdata, rb, reb, 8)]
        if indice >= 20:
            (ra, rea), _, rdata = por_indice[indice - 20]
            noite.append(faixa_revisao("R+30", rdata, ra, rea, 10))
        noite += [faixa_aprendizagem(ma, ea, RAMPA[min(semana, 2)]["aprendizagem"], rampa="aprendizagem"), PAUSA, faixa_aprendizagem(mb, eb, 10), PORTUGUES, CORRECAO]
        dia = {"data": data.isoformat(), "semana": semana,
               "reduzida": "A manhã inteira e a Aprendizagem da noite.",
               "minima": f"Só a teoria e a fixação de {ea['titulo']}."}
        if data in CARNAVAL:
            dia["feriado"] = CARNAVAL[data]
        dia.update({"manha": manha, "noite": noite})
        dias.append(dia)
        indice += 1
    sabado = segunda + timedelta(days=5)
    dias.append({"data": sabado.isoformat(), "semana": semana,
                 "manha": [faixa_sabado(semana, diagnostico.isoformat()), faixa_redacao(semana),
                           {**CORRECAO, "duracao": 30, "titulo": "Correção do sábado",
                            "detalhe": ("Na Revisão do simulado, passe pelos erros, chutes e em branco com a "
                                        "explicação aberta. A redação vai para o Claude Code.")}]})

fim = INICIO + timedelta(weeks=SEMANAS - 1, days=5)
plano = {
    "ciclo": 1,
    "titulo": "PRF — Ciclo 1 (6 semanas)",
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
        1: "Começo: duas teorias por manhã, a Aprendizagem e o Português à noite. Sábado: o diagnóstico (120 itens) e a 1ª redação.",
        2: "Entram as revisões R+7 à noite. Sábado: simulado de treino e redação.",
        3: "Mesmo ritmo. Sábado: simulado de treino e redação.",
        4: "Mesmo ritmo. Sábado: simulado de treino e redação.",
        5: "Entra a revisão R+30 (4 semanas depois, no mesmo dia da semana) do que foi estudado na semana 1.",
        6: "Última semana do Ciclo 1 (segunda e terça são de Carnaval). Sábado: o fechamento, comparado com o diagnóstico.",
    },
    "materias": [{"nome": m, "questoes": ITENS_2021[m], "meta": round(ITENS_2021[m] * ACERTO_DO_BLOCO[BLOCO[m]])}
                 for m in ITENS_2021],
    "materias_mistas": ["Redação"],
    "mapa": [
        {"nome": "Ciclo 1", "inicio": INICIO.isoformat(), "fim": fim.isoformat(),
         "foco": "Os assuntos que o Cebraspe mais cobra em cada matéria, com o peso da prova de 2021"},
        {"nome": "Ciclos seguintes, até o edital", "inicio": (fim + timedelta(days=2)).isoformat(),
         "foco": "Os assuntos que ficaram para depois e as revisões; o ciclo se repete até sair o edital"},
        {"nome": "Reta final", "quando": "quando sair o edital (previsto para 2027)",
         "foco": "Com a data da prova: mais horas, domingo entra, simulado completo todo sábado"},
        {"nome": "Prova", "quando": "a data do edital", "foco": "120 itens e a discursiva"},
    ],
    "dias": dias,
}

CABECALHO = """# O cronograma da PRF, Ciclo 1, dia a dia, no formato do config/cronograma.yml do radar
# (lido pela tela Hoje e pelo `radar hoje`). Veja o comentario do topo de config/cronograma.yml
# para o que cada chave faz.
#
# PROCEDENCIA: gerado pelo Claude Code (claude-opus-5-5) em 25/11/2026 (Etapa 5, PRF-35), a
# partir de docs/prioridade.md (o peso: os itens de cada materia em 2021), da incidencia de
# cada assunto nas provas do radar (provas da PRF + 0,25 x as outras do Cebraspe, o
# PRF/config/prioridade.yml), de docs/aprovados_prf.md (as metas) e de docs/metodo.md (o
# metodo). Pode editar a mao: e dado, nao codigo.
#
# A LOGICA (docs/metodo.md):
#   - manha: duas teorias curtas (50 e 40 min) de materias diferentes, cada uma seguida da
#     fixacao em itens de Certo/Errado com a ficha aberta - testar-se, e nao reler;
#   - noite: as revisoes espacadas (R+7 da semana 2 em diante, R+30 da semana 5: 4 semanas, o rotulo que o radar conhece), a
#     Aprendizagem sem consulta dos temas da manha, o Portugues de todo dia e a correcao;
#   - sabado: o diagnostico (semana 1), o simulado de treino (2 a 5) ou o fechamento (6),
#     cronometrados, e a redacao da semana; domingo e folga (o radar recusa domingo);
#   - a rampa: a primeira Aprendizagem da noite tem 15 itens no nivel 1 e 20 no nivel 2;
#     o gatilho sobe o nivel com 4 dias completos na semana e nenhum zerado;
#   - os 60 encontros de teoria do ciclo saem do peso da prova de 2021, espalhados para que
#     nenhuma materia fique semanas sem voltar (intercalar).
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
print("gravado", SAIDA, "| dias:", len(dias), "| fim:", fim, "| carnaval:", sorted(CARNAVAL))
for i, ((ma, ea), (mb, eb)) in enumerate(pares[:10]):
    print(f"  dia {i + 1}: A {ma[:22]:22} {ea['titulo'][:45]:45} | B {mb[:22]:22} {eb['titulo'][:40]}")

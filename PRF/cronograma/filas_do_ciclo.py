# As filas de assuntos de cada materia para o ciclo 1, em ordem de incidencia:
# questoes C/E do alvo (as provas da PRF) + 0,25 x as do complementar (o Cebraspe das
# outras provas), pela classificacao principal; tema que nunca caiu vale 0,5 (o piso do
# PRF/config/prioridade.yml). A unidade e o assunto (2o nivel); em Transito, o capitulo
# do CTB (3o nivel) e os outros assuntos da materia.
# Uso: python PRF/cronograma/filas_do_ciclo.py PRF/cronograma/filas.json (da raiz).
import json, sqlite3, sys, collections
sys.stdout.reconfigure(encoding="utf-8")
from radar.questoes import chave_da_questao

PESO_COMPLEMENTAR, PISO = 0.25, 0.5
CTB = "Legislação de Trânsito > Lei nº 9.503/1997 (Código de Trânsito Brasileiro) e suas alterações, inclusive as da Lei nº 14.071/2020"

arvore = json.load(open("data/conteudos.json", encoding="utf-8"))
do_edital = [n for n in arvore if not n.get("fora_do_edital")]
materias = [n["caminho"] for n in do_edital if n["nivel"] == "materia" and n["caminho"] != "História da PRF"]
unidades = {m: [] for m in materias}
for n in do_edital:
    partes = n["caminho"].split(" > ")
    if n["nivel"] == "assunto" and partes[0] in unidades and n["caminho"] != CTB:
        unidades[partes[0]].append(n["caminho"])
    if n["caminho"].startswith(CTB + " > ") and n["caminho"].count(" > ") == 2:
        unidades["Legislação de Trânsito"].append(n["caminho"])

c = sqlite3.connect("file:data/radar.db?mode=ro", uri=True)
evidencia_da_chave = {}
for enun, alts, ev, anul in c.execute("select enunciado, alternativas, evidencia, anulada from questoes where evidencia in ('alvo','complementar')"):
    a = json.loads(alts)
    if a == {"c": "Certo", "e": "Errado"} and not anul:
        k = chave_da_questao(enun, a)
        if evidencia_da_chave.get(k) != "alvo":
            evidencia_da_chave[k] = ev
conta = collections.defaultdict(lambda: [0, 0])
for chave, conteudo, status in c.execute("select chave, conteudo, status from classificacoes where principal=1"):
    ev = evidencia_da_chave.get(chave)
    if not ev or status == "pendente":
        continue
    for u in (unidade for lista in unidades.values() for unidade in lista):
        if conteudo == u or conteudo.startswith(u + " > "):
            conta[u][0 if ev == "alvo" else 1] += 1
            break

filas = {}
for m, lista in unidades.items():
    def nota(u):
        alvo, comp = conta[u]
        return (alvo + PESO_COMPLEMENTAR * comp) or PISO
    filas[m] = [{"no": u, "alvo": conta[u][0], "complementar": conta[u][1], "incidencia": nota(u)}
                for u in sorted(lista, key=lambda u: -nota(u))]
json.dump(filas, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for m, fila in filas.items():
    print(f"## {m} ({len(fila)})")
    for f in fila[:6]:
        print(f"   {f['incidencia']:5.2f}  alvo {f['alvo']:>2} comp {f['complementar']:>3}  {f['no'].split(' > ')[-1][:80]}")

"""As questoes de CERTO ou ERRADO, so para conferir o assunto (decisao PMSC-19).

A Policia Penal DF 2022 (Instituto AOCP) tem 150 itens de Certo/Errado, e o
caderno e escaneado: o texto embutido e de OCR, com numeros de item perdidos.
O Claude Code transcreveu os itens das materias da PMSC olhando as imagens das
paginas, para um JSON salvo em `data/provas/manual/` - fora do git, porque o
texto e de terceiros (decisao 132) -, e e dele que este leitor parte:

    {"prova": "...", "procedencia": "...", "itens": [{"numero": 1,
     "materia": "...", "comando": "...", "texto_base": "... ou null",
     "enunciado": "...", "gabarito": "C" | "E" | "X"}]}

O item vira uma questao de duas alternativas, "c" (Certo) e "e" (Errado), e o
X e a anulada. Na PMSC o Certo/Errado da AOCP ficava recusado no acervo
complementar (`complementar.validar`), so para conferir. Na PRF o Certo/Errado
do Cebraspe e o formato principal (Etapa 4, PRF-28): o caderno da lista com
`formato: certo_errado` treina e mede, e o item pode ficar EM BRANCO.

O caderno escaneado tambem nao tem o traco do sublinhado que o
`radar/destaques.py` le - ele achava letra solta. O termo destacado vem da
transcricao (`destaques`, a lista dos termos de cada item), pelo `marcas`.
"""
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from radar.questoes import Questao
from radar.questoes_selecon import materia_da_faixa

#: As duas alternativas de todo item de Certo/Errado.
ALTERNATIVAS = {"c": "Certo", "e": "Errado"}
LETRAS = tuple(sorted(ALTERNATIVAS))

#: A marca do item deixado EM BRANCO, na `escolhida` da resposta (PRF-28).
#: Nao e letra de alternativa nenhuma: a resposta em branco esta dada (a
#: rodada anda) e nao tem acerto (`acertou` fica nulo). No Cebraspe ela vale
#: 0, a certa +1 e a errada -1 (edital PRF 2021, item 9.12.2).
EM_BRANCO = "-"


def e_certo_errado(alternativas: dict | None) -> bool:
    """A questao e de Certo/Errado? Pelas alternativas, e nao pela banca: o
    mesmo caderno da AOCP pode ser de um formato ou do outro."""
    return tuple(sorted(alternativas or {})) == LETRAS


def _dentro(numero: int, ler: list[str] | None) -> bool:
    if not ler:
        return True
    for faixa in ler:
        inicio, _, fim = str(faixa).partition("-")
        if int(inicio) <= numero <= int(fim or inicio):
            return True
    return False


def ler_transcricao(caminho: Path, ler: list[str] | None = None,
                    materias: list[tuple[int, int, str]] | None = None) -> list[Questao]:
    """Os itens da transcricao, como questoes. A materia vem da faixa da lista
    (`materias`), como nos outros leitores, e o item fora de toda faixa fica
    de fora. ValueError quando um item nao tem gabarito C, E ou X."""
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    questoes = []
    for item in dados.get("itens") or []:
        numero = int(item["numero"])
        if not _dentro(numero, ler):
            continue
        materia = materia_da_faixa(numero, materias) if materias else item.get("materia")
        if not materia:
            continue
        gabarito = (item.get("gabarito") or "").strip().upper()
        if gabarito not in ("C", "E", "X"):
            raise ValueError(f"item {numero}: gabarito {gabarito!r}, e nao C, E ou X")
        # O comando do bloco ("Acerca de ..., julgue os itens") vai junto: o
        # item sozinho muitas vezes nao diz de que lei ou de que texto fala.
        enunciado = "\n\n".join(p.strip() for p in (item.get("comando"), item.get("enunciado"))
                                if p and p.strip())
        questoes.append(Questao(
            numero=numero, enunciado=enunciado, alternativas=dict(ALTERNATIVAS),
            resposta=None if gabarito == "X" else gabarito.lower(),
            materia=materia, anulada=gabarito == "X",
            texto_base=(item.get("texto_base") or "").strip() or None))
    return sorted(questoes, key=lambda q: q.numero)


def termos_da_transcricao(caminho: Path) -> dict[int, tuple[str, list[str]]]:
    """{numero: (afirmacao, termos)} dos itens com termo destacado."""
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    return {int(item["numero"]): ((item.get("enunciado") or "").strip(), list(item["destaques"]))
            for item in dados.get("itens") or [] if item.get("destaques")}


def marcas(enunciado: str, afirmacao: str, termos: list[str]) -> list[dict] | None:
    """O sublinhado de cada termo, no formato do `radar/destaques.py`. O termo
    e procurado so na afirmacao - o comando vem antes dela no enunciado -,
    como palavra inteira e depois do termo anterior: "mal" e "Mal" do item 11
    sao dois lugares. O termo que nao se acha fica sem marca."""
    from radar.destaques import ENUNCIADO, SUBLINHADO

    de = enunciado.rfind(afirmacao) if afirmacao else -1
    if de < 0:
        return None
    saida = []
    for termo in termos:
        achado = re.compile(r"(?<!\w)" + re.escape(termo) + r"(?!\w)").search(enunciado, de)
        if achado is None:
            continue
        saida.append({"tipo": SUBLINHADO, "campo": ENUNCIADO, "inicio": achado.start(),
                      "fim": achado.end(), "trecho": achado.group()})
        de = achado.end()
    return saida or None


# --- o caderno do Cebraspe, direto do PDF (Etapa 2 da PRF) ---------------------
#
# O caderno de Certo/Errado do Cebraspe tem texto de verdade (nao e escaneado):
# o radar le direto dele. A forma, conferida nas provas da PRF de 2019 e 2021:
#
#   - o item e o numero no comeco da linha, seguido do texto ("20 Infere-se...").
#     Os itens vem em sequencia, e e a sequencia que separa o item de um numero
#     qualquer no comeco da linha;
#   - antes dos itens de um grupo vem o cabecalho dele: o texto ("Texto
#     1A18-I") ou a situacao - o paragrafo abre com DOIS espacos - e o comando,
#     a frase com "julgue" ("Com relação ao texto, julgue os itens a seguir.");
#   - o cabecalho da pagina ("CEBRASPE – PRF – Edital: 2021"), o "BLOCO I" e o
#     "Espaço livre" das colunas vazias nao sao de item nenhum.
#
# O texto vem do pypdf, que poe o numero junto do item mas parte a palavra do
# texto justificado ("Siste ma"). O pdfminer escreve a palavra inteira, mas
# solta o numero do item: e dele que sai o vocabulario que conserta a palavra
# partida (`religar`).

# O que nao e de item nenhum: o cabecalho da pagina, e a linha so de palavras
# em caixa alta ("BLOCO II", e o "TEXTO" solto que a diagramacao deixa na
# prova de 2019) - linha de item sempre tem minuscula, numero ou pontuacao.
# Nos cadernos de outros concursos (FUB e SEE/DF de 2016, SEE/PE de 2022) o
# cabecalho comeca pelo codigo de barras do caderno ("||281FUB_012_01N369409||
# CESPE | CEBRASPE – FUB" e "714005_01N167818 CEBRASPE – SEE/PE"): sem
# reconhece-lo, o cabecalho grudava no item do fim da pagina. Nos de 2022 e
# 2023 (Policia Cientifica e PC de AL, Petrobras) o codigo tem 14 caracteres
# ("701CB201597439 CEBRASPE – POLC/AL"), e o comando do grupo seguinte grudava
# junto: os itens dele ficavam com o comando do grupo de antes (PRF-32).
# PRF-45: o cabecalho da PF de 2018 traz o nome do arquivo ("Matriz_408_DGPPF014_
# Pag 9N784737 CESPE | CEBRASPE – DGP/PF"), o do MJSP a sigla entre barra e
# travessao ("CEBRASPE | MJSP – Edital: 2021"), e o titulo da parte vem entre
# tracos ("-- CONHECIMENTOS ESPECÍFICOS --", DEPEN e MJSP): grudavam no item.
MOBILIA_DO_CADERNO = re.compile(
    r"^\s*(?:(?:\|\|\S+\|\|\s*|\d+_\d+N\d+\s+|\d{3}[A-Z\d]{2}\d{9}\s+|Matriz_\S+\s+Pag\s*\S+\s+)?"
    r"(?:CESPE\s*\|\s*)?CEBRASPE\s*(?:\|\s*[^–\-|]{1,30}?\s*)?[–-]"
    r"|Bloco\s+[IVX]+\s*$"
    r"|[A-ZÁÉÍÓÚÂÊÔÃÕÇ]+(?: [A-ZÁÉÍÓÚÂÊÔÃÕÇ]+)*\s*$)")
# O titulo da parte nao so sai: ele fecha o item de antes. Depois de "-- PROVA
# DISCURSIVA --" vem a instrucao da redacao, que grudava no ultimo item.
TITULO_DA_PARTE = re.compile(r"^\s*-{2,}\s*[^-]+?\s*-{2,}\s*$")
# O nome da materia sozinho na linha, abrindo a secao ("Língua Portuguesa",
# "Matemática" no CBM/AL 2021): entre uma frase fechada e o paragrafo, e titulo.
TITULO_DA_MATERIA = re.compile(
    r"^\s*(?:Língua (?:Portuguesa|Inglesa|Espanhola)|Matemática|Raciocínio Lógico[\w\s-]*|"
    r"Noções de [\w\s]+|Informática|Atualidades|Física|Ética[\w\s]*|"
    r"(?:Direito|Legislação) [\w\s]+)\s*$")
ESPACO_LIVRE = re.compile(r"\s*Espa[çc]o\s+livre\s*")
# O rotulo do texto, com o codigo ("Texto 1A18-I") ou sem ("Texto", na Policia
# Civil de Sergipe de 2018): sem o codigo, o texto so nao se cita pelo nome.
# PRF-46: e o rotulo em ingles, com o codigo ("Text CB3A5AAA"): sem ele, o texto
# ingles grudava no ultimo item de espanhol do caderno de duas linguas (ABIN).
ROTULO_DO_TEXTO = re.compile(
    r"^\s*(?:Texto(?:\s+([0-9A-Z]+(?:-[IVX]+)?))?|Text\s+([0-9A-Z]+(?:-[IVX]+)?))\s*$")
# O grupo que so cita o texto pelo codigo ("julgue ... do texto 1A18-I"). PRF-57:
# o codigo da PF de 2018 nao tem hifen ("texto 12A1AAA", "texto 14A15AAA") e as
# vezes vem partido ("texto 12A 1AAA"); sem isto, o segundo grupo do mesmo texto
# ficava sem ele. O codigo tem algarismo: "texto apresentado" nao e citacao.
CITACAO_DO_TEXTO = re.compile(
    r"\b(?i:texto)\s+([A-Z]{0,3}\d+[A-Z]\s?\d+[A-Z]*(?:-[IVX]+)?)(?![\w-])")
# A numeracao de linha na margem do texto (1, 4, 7, 10...): o pypdf a solta
# numero por numero, uma linha cada, as vezes com um lixo antes do 1 ("\t/1").
# Na prova da PRF de 2019 o "10" dela virou o item 10, e o item 10 de verdade
# foi parar no comando do grupo seguinte.
NUMERO_DA_MARGEM = re.compile(r"^\s*(?:\\t/)?(\d{1,3})\s*$")
# As instrucoes numeradas da capa (1 a 7). Nos cadernos da Policia Federal de
# 2021 elas vem antes do item 1 e viraram os itens 1 a 7. A frase de abertura
# de cada uma e a da capa do Cebraspe, e item nenhum comeca assim.
INSTRUCAO_DA_CAPA = re.compile(
    r"^\d{1,2}\s+(?:Ao receber este caderno|Durante a realização das provas|"
    r"Não serão fornecidas folhas|Na duração das provas|Ao terminar as provas|"
    r"Nenhuma folha deste caderno|A desobediência a qualquer)")
# A legenda da figura ("Figura 1A9-I"): como o rotulo do texto, abre o
# cabecalho do grupo - e nao e frase do comando.
ROTULO_DA_FIGURA = re.compile(r"^\s*Figura\s+[0-9A-Z]+(?:-[IVX]+)?\s*$")
NUMERO_DO_ITEM = re.compile(r"^(\d{1,3})(?:\s+(\S.*))?$")
# O comando: "julgue os itens" - e, no caderno de lingua estrangeira, "judge
# the following items" (ingles) ou "juzgue los ítems" (espanhol).
# PRF-45: e o comando sem "julgue" ("Em cada um dos itens a seguir, é
# apresentada uma situação hipotética, seguida de uma assertiva a ser julgada"),
# da PM/AL 2018 e do DEPEN: o grupo novo grudava no fim do item de antes. So
# "a ser julgada": "julgado" sozinho e da lei ("trânsito em julgado").
JULGUE = re.compile(r"\b(?:julgue|judge|juzgue|a\s+ser(?:em)?\s+julgad[ao]s?)\b", re.IGNORECASE)
FIM_DE_FRASE = re.compile(r"[.!?:)”\"]\s*$")
# O recuo do paragrafo que o pypdf guarda: dois espacos e ja o texto (letra,
# aspa, travessao ou o sinal invertido do espanhol), sem mais espaco.
RECUO_DE_PARAGRAFO = re.compile(r"^ {2}(?=[^\W\d_]|[“\"'—–¿¡«(])")
PALAVRA = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*")
#: A letra do gabarito definitivo e a resposta da questao (X: anulado).
RESPOSTA_DA_LETRA = {"C": "c", "E": "e", "X": None}


@dataclass
class ItemDoCaderno:
    numero: int
    afirmacao: str             # o texto do item, sem o numero
    comando: str | None        # "Com relação ao texto, julgue os itens a seguir."
    texto_base: str | None     # o texto ou a situacao do grupo


def _texto_do_pdfminer(caminho: Path) -> str:
    from pdfminer.high_level import extract_text

    # O pdfminer avisa de fonte fora do padrao em quase todo PDF, sem mudar
    # nada no texto: sao dezenas de linhas poluindo a saida do comando.
    logging.getLogger("pdfminer").setLevel(logging.ERROR)
    return extract_text(str(caminho))


def _chave_da_linha(linha: str) -> str:
    """O comeco da linha sem espaco nenhum: o pypdf parte a palavra ("activi
    dad") e o pdfminer dobra o espaco do texto justificado ("Em  um"), e assim
    a mesma linha dos dois casa. O numero no fim sai: no texto com a
    numeracao de linha na margem, o pypdf o cola na linha ("corazón? 1") e o
    pdfminer o solta."""
    return re.sub(r"\d+$", "", re.sub(r"\s+", "", linha))[:30]


def inicios_de_paragrafo(texto_do_pdfminer: str) -> set[str]:
    """As linhas que abrem paragrafo, pela chave (`_chave_da_linha`).

    Nos cadernos da FUB e da SEE/DF de 2016 o pypdf perde o recuo do
    paragrafo, e a situacao do grupo seguinte grudava no ultimo item do grupo
    anterior. O pdfminer separa o texto em blocos (linha vazia entre eles), e
    abre paragrafo o bloco que comeca com maiuscula - menos o que continua o
    item: no caderno da FUB a primeira linha do item ("56 A velocidade
    média do automóvel, na primeira fase do teste,") e um bloco so dela, e o
    resto do item vem no bloco seguinte. O item de uma linha que fecha frase
    fica com o risco: se a segunda frase dele comecar na linha de baixo, ela
    passa por paragrafo (o `_marcar_paragrafos` so a separa quando um comando
    vem depois)."""
    inicios: set[str] = set()
    continua_o_item = False
    for bloco in re.split(r"\n\s*\n", texto_do_pdfminer):
        linhas = [linha.strip() for linha in bloco.splitlines() if linha.strip()]
        if not linhas or MOBILIA_DO_CADERNO.match(linhas[0]) or ESPACO_LIVRE.fullmatch(linhas[0]):
            continue
        # O numero sozinho e a numeracao da margem do texto, nao item.
        if len(linhas) == 1 and NUMERO_DA_MARGEM.match(linhas[0]):
            continue
        # A pergunta e a exclamacao do espanhol abrem com o sinal invertido
        # ("¿Qué hora son, mi corazón?"): a maiuscula vem depois dele.
        if linhas[0].lstrip("¿¡«“\"")[:1].isupper() and not continua_o_item:
            inicios.add(_chave_da_linha(linhas[0]))
        continua_o_item = bool(len(linhas) == 1 and NUMERO_DO_ITEM.match(linhas[0])
                               and not FIM_DE_FRASE.search(linhas[0]))
    return inicios


def _marcar_paragrafos(linhas: list[str], inicios: set[str]) -> list[str]:
    """Poe os dois espacos do recuo que o pypdf perdeu, na linha que abre
    paragrafo pelo pdfminer. So marca quando um comando ("julgue") vem depois,
    antes do proximo item: o item de duas frases, com a segunda no comeco da
    linha, nao pode perder a segunda para o grupo seguinte."""
    saida = list(linhas)
    for indice, linha in enumerate(linhas):
        if linha.startswith("  ") or _chave_da_linha(linha) not in inicios:
            continue
        # PRF-57: paragrafo so abre depois de frase fechada (ou do numero
        # sozinho do item de figura). Na PF de 2018 o pdfminer partiu o fim do
        # item ("autorização do Poder" / "Judiciário.") em dois blocos, e o
        # pedaco de baixo virava o texto do grupo seguinte.
        anterior = linhas[indice - 1].strip() if indice else ""
        if anterior and not (FIM_DE_FRASE.search(anterior) or anterior.isdigit()):
            continue
        for distancia, seguinte in enumerate(linhas[indice:]):
            if distancia and NUMERO_DO_ITEM.match(seguinte):
                break
            if JULGUE.search(seguinte):
                saida[indice] = "  " + linha
                break
    return saida


def vocabulario(texto: str) -> set[str]:
    """As palavras do texto, em minuscula - com hifen, quando tem."""
    return {palavra.lower() for palavra in PALAVRA.findall(texto)}


def _deve_juntar(antes: str, depois: str, palavras: set[str]) -> bool:
    """O fim de `antes` e o comeco de `depois` sao a mesma palavra partida?
    So quando a juncao e palavra do vocabulario e um dos pedacos nao e: "de
    vida" fica separado, porque "de" e "vida" sao palavras. O pedaco que acaba
    em hifen ("norte- americano", "causando- lhe") emenda quando a palavra
    composta existe."""
    if antes.endswith("-"):
        fim = re.search(r"[^\W\d_]+(?:-[^\W\d_]+)*-$", antes)
        comeco = re.match(r"^[^\W\d_]+(?:-[^\W\d_]+)*", depois)
        return bool(fim and comeco and (fim.group() + comeco.group()).lower() in palavras)
    fim = re.search(r"[^\W\d_]+$", antes)
    comeco = re.match(r"^-?[^\W\d_]+(?:-[^\W\d_]+)*", depois)
    if not fim or not comeco:
        return False
    junto = (fim.group() + comeco.group()).lower()
    pedacos = (fim.group().lower(), comeco.group().lstrip("-").lower())
    return junto in palavras and any(p not in palavras for p in pedacos)


def religar(texto: str, palavras: set[str]) -> str:
    """O texto do pypdf com a palavra partida de volta ("Siste ma" vira
    "Sistema", "infere -se" vira "infere-se")."""
    saida: list[str] = []
    for pedaco in texto.split(" "):
        if saida and pedaco and _deve_juntar(saida[-1], pedaco, palavras):
            saida[-1] += pedaco
        else:
            saida.append(pedaco)
    return " ".join(saida)


def _juntar_linhas(linhas: list[str], palavras: set[str]) -> str:
    """As linhas viram um paragrafo. A linha que acaba em hifen emenda na de
    baixo: sem o hifen quando a palavra inteira existe ("muni-" + "cípio"), e
    com ele quando o hifen e da palavra ("inter-" + "regional")."""
    texto = ""
    for linha in (l.strip() for l in linhas):
        if not linha:
            continue
        if texto.endswith("-") and linha[:1].islower():
            fim = re.search(r"[^\W\d_]+-$", texto)
            comeco = re.match(r"[^\W\d_]+", linha)
            sem_hifen = (fim.group()[:-1] + comeco.group()).lower() if fim and comeco else ""
            texto = texto[:-1] + linha if sem_hifen in palavras else texto + linha
        else:
            texto = f"{texto} {linha}" if texto else linha
    return " ".join(texto.split())


def _comeco_do_comando(linhas: list[str]) -> int | None:
    """Onde comeca o comando: a ULTIMA frase que tem "julgue" e vai ate o fim
    das linhas. Frase comeca em linha que abre com maiuscula, depois de linha
    que fecha frase. A instrucao do caderno ("caso julgue o item CERTO") vem
    antes, e por isso fica de fora."""
    for indice in range(len(linhas) - 1, -1, -1):
        linha = linhas[indice].strip()
        anterior = linhas[indice - 1] if indice else ""
        fecha = (indice == 0 or FIM_DE_FRASE.search(anterior) or ROTULO_DO_TEXTO.match(anterior)
                 or ROTULO_DA_FIGURA.match(anterior))
        if linha[:1].isupper() and fecha and not ROTULO_DA_FIGURA.match(linha) \
                and JULGUE.search(" ".join(linhas[indice:])):
            return indice
    return None


def _comeco_da_ultima_frase(linhas: list[str]) -> int | None:
    """A linha em que comeca a ultima frase: maiuscula depois de linha que
    fecha frase (ou de rotulo)."""
    for indice in range(len(linhas) - 1, -1, -1):
        anterior = linhas[indice - 1] if indice else ""
        fecha = (indice == 0 or FIM_DE_FRASE.search(anterior) or ROTULO_DO_TEXTO.match(anterior)
                 or ROTULO_DA_FIGURA.match(anterior))
        if linhas[indice].strip()[:1].isupper() and fecha:
            return indice
    return None


def _sem_numeracao_da_margem(linhas: list[str]) -> list[str]:
    """Tira a numeracao de linha da margem: tres ou mais linhas seguidas so com
    numero, crescendo sempre do mesmo passo, maior que um (1, 4, 7...). O item
    de figura - o numero sozinho - cresce de um em um, e fica."""
    saida: list[str] = []
    indice = 0
    while indice < len(linhas):
        numeros = []
        while indice + len(numeros) < len(linhas):
            achado = NUMERO_DA_MARGEM.match(linhas[indice + len(numeros)])
            if not achado:
                break
            numeros.append(int(achado.group(1)))
        if not numeros:
            saida.append(linhas[indice])
            indice += 1
            continue
        # Dentro da sequencia de numeros, a progressao mais longa que comeca no
        # primeiro sai; o que sobra (um item de figura logo depois) fica.
        passo = numeros[1] - numeros[0] if len(numeros) > 1 else 0
        tamanho = 1
        while tamanho < len(numeros) and numeros[tamanho] - numeros[tamanho - 1] == passo:
            tamanho += 1
        if passo >= 2 and tamanho >= 3:
            indice += tamanho
        else:
            saida.append(linhas[indice])
            indice += 1
    return saida


def _fim_do_item(linhas: list[str]) -> int:
    """Quantas linhas do trecho sao do item; o resto e o cabecalho do grupo
    seguinte. O item acaba no paragrafo de dois espacos (texto ou situacao),
    no rotulo "Texto ..." ou no comando que vem logo depois dele."""
    for indice in range(1, len(linhas)):
        if (linhas[indice].startswith("  ") or ROTULO_DO_TEXTO.match(linhas[indice])
                or ROTULO_DA_FIGURA.match(linhas[indice])):
            return _sem_o_que_e_do_grupo_seguinte(linhas, indice)
    comando = _comeco_do_comando(linhas[1:])
    return len(linhas) if comando is None else comando + 1


#: A linha curta que nao fecha frase: o titulo da parte ("Matemática") e a
#: tabela do texto do grupo seguinte ("unidade de", "ABC 17", "Total").
LINHA_CURTA = 25


def _sem_o_que_e_do_grupo_seguinte(linhas: list[str], corte: int) -> int:
    """O corte antes das linhas curtas, sem fim de frase, que ficam entre o item
    (que ja fechou a frase) e o paragrafo do grupo seguinte (PRF-45: no CBM/AL
    2021 o titulo "Matemática" e a tabela do problema grudavam no item 25). O
    item do Cebraspe acaba em ponto: sem a frase fechada antes, nada muda."""
    inicio = corte
    while (inicio > 1 and len(linhas[inicio - 1].strip()) <= LINHA_CURTA
           and not FIM_DE_FRASE.search(linhas[inicio - 1])):
        inicio -= 1
    if inicio < corte and FIM_DE_FRASE.search(linhas[inicio - 1]):
        return inicio
    return corte


def _sem_titulo_da_parte(linhas: list[str]) -> list[str]:
    """Tira o titulo da parte ("-- CONHECIMENTOS ESPECÍFICOS --") e poe o recuo
    de paragrafo na linha de baixo: o item de antes acaba ali (PRF-45)."""
    saida: list[str] = []
    fecha = False
    ja_tem_item = False
    for indice, linha in enumerate(linhas):
        seguinte = linhas[indice + 1] if indice + 1 < len(linhas) else ""
        anterior = saida[-1] if saida else ""
        if (TITULO_DA_MATERIA.match(linha) and (not anterior or FIM_DE_FRASE.search(anterior))
                and (seguinte.startswith("  ") or ROTULO_DO_TEXTO.match(seguinte))):
            # O titulo da materia so sai: o paragrafo de baixo ja fecha o item.
            continue
        if TITULO_DA_PARTE.match(linha):
            # Antes do primeiro item nao ha item a fechar: o titulo so sai ("--
            # PROVA OBJETIVA --" da PRF 2019; com o recuo, o rotulo embaralhado
            # de baixo virava o comeco do texto).
            fecha = ja_tem_item
            continue
        if fecha and not linha.startswith("  ") and not NUMERO_DO_ITEM.match(linha):
            linha = "  " + linha
        fecha = False
        achado = NUMERO_DO_ITEM.match(linha)
        ja_tem_item = ja_tem_item or bool(achado and achado.group(2))
        saida.append(linha)
    return saida


def _lixo_da_capa(linha: str) -> bool:
    """A linha da capa (antes do primeiro item) que nao e texto: a da fonte sem
    mapa ('!" #$$%& "', '0 / , )1 . , 23'), sem palavra nenhuma de tres letras,
    e a instrucao da capa com o marcador "•" (PRF-45: no CBM/AL 2021, na PC/AL,
    na SERIS/AL e na SESAU/AL elas viravam o texto-base do primeiro grupo). So
    se aplica a capa: o item de conta tambem nao tem palavra."""
    texto = linha.strip()
    return bool(texto) and (not re.search(r"[^\W\d_]{3}", texto) or texto.startswith("•"))


def _ler_cabecalho(linhas: list[str], textos: dict[str, str],
                   palavras: set[str]) -> tuple[str | None, str | None]:
    """(comando, texto do grupo) de um cabecalho. O texto comeca no rotulo ou
    no primeiro paragrafo de dois espacos (a instrucao do caderno, antes, fica
    de fora); o texto com rotulo e guardado em `textos`, para o grupo que so o
    cita ("Considerando ... o texto 1A18-I, julgue")."""
    inicio_do_comando = _comeco_do_comando(linhas)
    if inicio_do_comando is not None and not FIM_DE_FRASE.search(linhas[-1]):
        # O comando que o item completa nao tem "julgue" ("A correcao do texto
        # seria preservada se" / "1 o trecho ... fosse reescrito"): e a ultima
        # frase, aberta ate o item. Sem isto, o comando era a instrucao da capa
        # ("caso julgue o item CERTO"), a ultima frase com "julgue". Sem
        # "julgue" nenhum no trecho (o cabecalho da pagina entre dois itens do
        # mesmo grupo), nao ha comando novo: o grupo continua.
        inicio_do_comando = _comeco_da_ultima_frase(linhas)
    if inicio_do_comando is None:
        return None, None
    comando = religar(_juntar_linhas(linhas[inicio_do_comando:], palavras), palavras)
    # A legenda da figura nao e texto: a figura e imagem, e o radar nao a tem.
    antes = [linha for linha in linhas[:inicio_do_comando] if not ROTULO_DA_FIGURA.match(linha)]
    rotulo = None
    inicio = None
    for indice, linha in enumerate(antes):
        achado = ROTULO_DO_TEXTO.match(linha)
        if achado or linha.startswith("  "):
            rotulo = (achado.group(1) or achado.group(2)) if achado else None
            inicio = indice + 1 if achado else indice
            break
    texto = None
    if inicio is not None:
        texto = religar(_juntar_linhas(antes[inicio:], palavras), palavras) or None
        if texto and rotulo:
            textos[rotulo.upper()] = texto
    if texto is None:
        citado = CITACAO_DO_TEXTO.search(comando)
        texto = textos.get(re.sub(r"\s+", "", citado.group(1)).upper()) if citado else None
    return comando, texto


def itens_do_caderno(texto: str, palavras: set[str], primeiro: int = 1,
                     paragrafos: set[str] | None = None) -> list[ItemDoCaderno]:
    """Os itens do caderno, cada um com o comando e o texto do grupo dele.

    A linha vazia sai antes de tudo: ela vem do "Espaço livre" e da quebra de
    pagina, e no meio do caminho escondia que a linha de cima fechava frase.
    `paragrafos`: as linhas que abrem paragrafo pelo pdfminer
    (`inicios_de_paragrafo`), para o caderno em que o pypdf perde o recuo."""
    linhas = [ESPACO_LIVRE.sub(" ", linha).rstrip() for linha in texto.splitlines()
              if not MOBILIA_DO_CADERNO.match(linha)]
    linhas = _sem_numeracao_da_margem([linha for linha in linhas if linha.strip()])
    linhas = _sem_titulo_da_parte(linhas)
    if paragrafos:
        linhas = _marcar_paragrafos(linhas, paragrafos)
    inicios = []
    esperado = primeiro
    for indice, linha in enumerate(linhas):
        achado = NUMERO_DO_ITEM.match(linha)
        if achado and int(achado.group(1)) == esperado and not INSTRUCAO_DA_CAPA.match(linha):
            inicios.append(indice)
            esperado += 1
    if not inicios:
        return []

    textos: dict[str, str] = {}
    # A capa vem antes do primeiro item: a linha embaralhada dela virava o
    # texto-base do primeiro grupo (PRF-45).
    capa = [linha for linha in linhas[:inicios[0]] if not _lixo_da_capa(linha)]
    comando, texto_base = _ler_cabecalho(capa, textos, palavras)
    itens = []
    for posicao, inicio in enumerate(inicios):
        fim = inicios[posicao + 1] if posicao + 1 < len(inicios) else len(linhas)
        trecho = linhas[inicio:fim]
        corte = _fim_do_item(trecho)
        numero, resto = NUMERO_DO_ITEM.match(trecho[0]).groups()
        afirmacao = religar(_juntar_linhas([resto or ""] + trecho[1:corte], palavras), palavras)
        itens.append(ItemDoCaderno(int(numero), afirmacao, comando, texto_base))
        if corte < len(trecho):
            novo_comando, novo_texto = _ler_cabecalho(trecho[corte:], textos, palavras)
            if novo_comando:
                comando, texto_base = novo_comando, novo_texto
    return itens


def _pares_do_gabarito(texto: str) -> list[tuple[int, str]]:
    """Os pares (item, letra) da grade, na ordem do texto do pdfminer.

    O asterisco colado na letra ("120 *C") marca o item cujo gabarito
    preliminar foi alterado; a letra e a definitiva. Sem tirar o asterisco,
    o item sumia: o 120 da PM/AL 2017 e o 1 do caderno de basicos (PRF-32).
    """
    pedacos = texto.split()
    return [(int(numero), letra.lstrip("*")) for numero, letra in zip(pedacos, pedacos[1:])
            if numero.isdigit() and letra.lstrip("*") in RESPOSTA_DA_LETRA]


def itens_em_duas_grades(texto: str) -> set[int]:
    """Os itens que o gabarito traz duas vezes.

    No caderno com espanhol e ingles (CBM/AL 2017, ABIN 2017) cada lingua tem
    a sua grade, e os itens de lingua estrangeira (1 a 5, ou 1 a 10) aparecem
    nas duas, as vezes com letras diferentes. Pelo texto nao se sabe qual
    grade e de qual lingua, e o leitor do caderno so le os itens da primeira.
    """
    vezes: dict[int, int] = {}
    for item, _ in _pares_do_gabarito(texto):
        vezes[item] = vezes.get(item, 0) + 1
    return {item for item, quantas in vezes.items() if quantas > 1}


def _celulas_e_cores(caminho: Path) -> tuple[list, list]:
    """As linhas de texto ([x0, y0, texto]) e os retangulos pintados ([x0, y0,
    x1, y1, cor]) da primeira pagina do gabarito, pelo pdfminer."""
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTCurve, LTTextLine

    logging.getLogger("pdfminer").setLevel(logging.ERROR)
    textos, pintados = [], []

    def andar(elemento):
        if isinstance(elemento, LTTextLine):
            texto = elemento.get_text().strip()
            if texto:
                textos.append((elemento.x0, elemento.y0, texto))
            return
        if isinstance(elemento, LTCurve) and getattr(elemento, "fill", False):
            pintados.append((elemento.x0, elemento.y0, elemento.x1, elemento.y1,
                             str(elemento.non_stroking_color)))
            return
        if hasattr(elemento, "__iter__"):
            for filho in elemento:
                andar(filho)

    for pagina in extract_pages(str(caminho), maxpages=1):
        andar(pagina)
    return textos, pintados


def grade_do_espanhol(caminho: Path) -> dict[int, str]:
    """{item: letra} da grade de espanhol do gabarito de duas linguas (PRF-46).

    No gabarito do CBM/AL 2017 e da ABIN 2017 os itens de lingua vem duas
    vezes, cada grade pintada de uma cor, e a legenda embaixo diz a cor de cada
    lingua (o quadrado vermelho ao lado de "Língua Espanhola", o azul ao lado
    de "Língua Inglesa"). A letra e a celula logo abaixo do numero. Sem a
    legenda, sem a cor ou sem celula, {}: o item de lingua continua fora."""
    textos, pintados = _celulas_e_cores(caminho)
    rotulo = next((t for t in textos if "Língua Espanhola" in t[2]), None)
    if rotulo is None:
        return {}
    # O quadrado da legenda: a esquerda do rotulo, na altura dele.
    # Os quadrados da legenda se encostam: vale o de centro mais perto do rotulo.
    candidatos = [p for p in pintados if p[2] <= rotulo[0] + 2 and p[1] - 4 <= rotulo[1] <= p[3] + 4
                  and p[2] - p[0] < 60]
    if not candidatos:
        return {}
    legenda = min(candidatos, key=lambda p: abs((p[1] + p[3]) / 2 - (rotulo[1] + 3)))
    cor = legenda[4]
    faixas = [p for p in pintados if p[4] == cor and p is not legenda]
    grade: dict[int, str] = {}
    for x0, y0, x1, y1, _ in faixas:
        for nx, ny, numero in textos:
            if not numero.isdigit() or not (x0 - 2 <= nx <= x1 and y0 - 2 <= ny <= y1):
                continue
            letras = [t for t in textos if t[2] in RESPOSTA_DA_LETRA and abs(t[0] - nx) < 6
                      and 0 < ny - t[1] < 15]
            if len(letras) == 1:
                grade[int(numero)] = letras[0][2]
    return grade


def em_espanhol(texto: str) -> bool:
    """O texto e espanhol, e nao ingles? Pelas palavras curtas de cada uma."""
    palavras = re.findall(r"[^\W\d_]+", (texto or "").lower())
    espanhol = sum(p in {"el", "los", "las", "del", "es", "una", "por", "con", "se", "y"}
                   for p in palavras)
    ingles = sum(p in {"the", "of", "and", "to", "is", "that", "it", "be", "from"} for p in palavras)
    return espanhol > ingles


# As palavras que dizem a lingua de uma frase. So para o caderno com espanhol e
# ingles (`duas_linguas`): o texto da segunda lingua gruda no texto-base do
# primeiro grupo em portugues, e e la que ele e cortado.
PALAVRAS_DO_PORTUGUES = {"não", "são", "uma", "dos", "das", "ao", "à", "é", "com", "para",
                         "em", "do", "da", "os", "as", "que", "se", "no", "na", "pelo", "pela"}
PALAVRAS_DE_FORA = {"the", "of", "and", "to", "is", "that", "in", "are", "for", "with",
                    "el", "los", "las", "del", "y", "es", "una", "por", "con", "lo", "su"}
FIM_DA_FRASE = re.compile(r"(?<=[.!?”\"])\s+")


def sem_a_outra_lingua(texto: str) -> str:
    """O texto-base sem as frases em ingles ou espanhol do COMECO: corta ate a
    primeira frase em que o portugues ganha, mas devolve as frases neutras
    logo antes dela (o titulo "O açúcar arrasou o Nordeste." nao tem palavra
    de lingua nenhuma). Sem frase em portugues, devolve o texto como veio."""
    frases = FIM_DA_FRASE.split(texto)

    def lingua(frase: str) -> int:
        """+1 portugues, -1 ingles ou espanhol, 0 sem sinal."""
        # O endereco da fonte ("<www.nytimes.com>") nao conta: o "com" dele
        # parecia portugues.
        sem_endereco = re.sub(r"<[^>]*>|\S*www\.\S*", " ", frase)
        palavras = re.findall(r"[^\W\d_]+", sem_endereco.lower())
        portugues = sum(p in PALAVRAS_DO_PORTUGUES for p in palavras)
        de_fora = sum(p in PALAVRAS_DE_FORA for p in palavras)
        return (portugues > de_fora) - (de_fora > portugues)

    sinais = [lingua(frase) for frase in frases]
    if 1 not in sinais:
        return texto
    comeco = sinais.index(1)
    while comeco > 0 and sinais[comeco - 1] == 0:
        comeco -= 1
    if -1 not in sinais[:comeco]:
        return texto
    return " ".join(frases[comeco:])


def ler_gabarito_do_cebraspe(texto: str, fora: set[int] | None = None) -> dict[int, str]:
    """{item: "C", "E" ou "X"} do gabarito definitivo de Certo/Errado.

    No texto do pdfminer a grade sai em pares, numero e letra ("9 C 29 E 49 E
    69 X"). ValueError quando o mesmo item tem duas letras, quando nao ha item
    nenhum ou quando falta item no meio: gabarito pela metade nunca entra.
    `fora`: os itens que nao entram (os de lingua das duas grades).
    """
    gabarito: dict[int, str] = {}
    for item, letra in _pares_do_gabarito(texto):
        if item not in (fora or set()):
            if gabarito.get(item, letra) != letra:
                raise ValueError(f"item {item} com duas letras no gabarito")
            gabarito[item] = letra
    if not gabarito:
        raise ValueError("o gabarito nao tem item de Certo/Errado")
    faltam = sorted(set(range(min(gabarito), max(gabarito) + 1)) - set(gabarito))
    if faltam:
        raise ValueError(f"faltam itens no gabarito: {faltam[:5]}")
    return gabarito


def ler_caderno(caminho: Path, caminho_do_gabarito: Path | list[Path] | None,
                ler: list[str] | None = None,
                materias: list[tuple[int, int, str]] | None = None,
                texto: str | None = None, texto_do_gabarito: str | None = None,
                palavras: set[str] | None = None,
                duas_linguas: bool = False,
                espanhol: dict[int, str] | None = None) -> list[Questao]:
    """Os itens do caderno de Certo/Errado do Cebraspe, como questoes, com a
    resposta do gabarito DEFINITIVO.

    O item de figura (o numero sem texto nenhum) fica de fora: sem a figura
    ele nao se responde. ValueError quando os itens lidos nao sao os do
    gabarito. `texto`, `texto_do_gabarito` e `palavras` sao para o teste, que
    nao le PDF.

    `caminho_do_gabarito` pode ser uma lista: o DEPEN 2020 tem um caderno so
    e um gabarito por parte (basicos, especificos e complementares), e as
    grades se juntam. `duas_linguas`: o caderno traz espanhol e ingles com os
    mesmos numeros, e os itens de lingua ficam de fora (`itens_em_duas_grades`).
    `espanhol`: a grade do espanhol ({item: letra}); sem ela, sai do PDF do
    gabarito (`grade_do_espanhol`), e os itens de espanhol voltam (PRF-46).
    """
    from radar.questoes import extrair_texto

    if texto_do_gabarito is None:
        if not caminho_do_gabarito:
            raise ValueError("falta o gabarito definitivo")
        caminhos = (caminho_do_gabarito if isinstance(caminho_do_gabarito, list)
                    else [caminho_do_gabarito])
        texto_do_gabarito = "\n".join(_texto_do_pdfminer(c) for c in caminhos)
    fora: set[int] = set()
    if duas_linguas:
        fora = itens_em_duas_grades(texto_do_gabarito)
        if not fora:
            raise ValueError("o gabarito nao tem as duas grades de lingua")
        if espanhol is None and caminho_do_gabarito:
            primeiro = (caminho_do_gabarito[0] if isinstance(caminho_do_gabarito, list)
                        else caminho_do_gabarito)
            espanhol = grade_do_espanhol(Path(primeiro))
    gabarito = ler_gabarito_do_cebraspe(texto_do_gabarito, fora=fora)
    # PRF-46: com a grade do espanhol (pela cor da legenda), os itens de lingua
    # voltam - o espanhol vem primeiro no caderno, e e ele que o leitor le.
    de_espanhol = set(espanhol or {}) if duas_linguas and set(espanhol or {}) == fora else set()
    for item in de_espanhol:
        gabarito[item] = espanhol[item]
    if texto is None:
        texto = extrair_texto(caminho)
    paragrafos = None
    if palavras is None:
        texto_do_pdfminer = _texto_do_pdfminer(caminho)
        palavras = vocabulario(texto_do_pdfminer)
        # So no caderno em que o pypdf perdeu TODO recuo (FUB e SEE/DF de
        # 2016). Onde ele o tem (a PRF, a SEE/PE de 2022), o pdfminer parte o
        # texto linha a linha, e a marca dele separava a segunda frase do item.
        # PRF-57: recuo de paragrafo e o de dois espacos antes de letra, aspa
        # ou travessao; o do codigo de programa ("    print(x)", "  {") nao
        # conta - na PF de 2018 (Agente) era o unico recuo do caderno, e o
        # texto do primeiro grupo (o do Nudetective) ficava sem ser lido.
        if not any(RECUO_DE_PARAGRAFO.match(linha) for linha in texto.splitlines()):
            paragrafos = inicios_de_paragrafo(texto_do_pdfminer)

    itens = itens_do_caderno(texto, palavras, primeiro=min(set(gabarito) | fora),
                             paragrafos=paragrafos)
    # O item de lingua sai inteiro, a menos que seja do espanhol com a grade
    # dele: o leitor so le a primeira lingua, e o texto da segunda gruda no
    # ultimo item dela. Se o primeiro bloco nao for espanhol, sai tambem.
    if de_espanhol and not em_espanhol(
            " ".join(i.afirmacao for i in itens if i.numero in de_espanhol)):
        for item in de_espanhol:
            gabarito.pop(item, None)
        de_espanhol = set()
    itens = [item for item in itens if item.numero not in fora or item.numero in de_espanhol]
    if duas_linguas:
        # O texto da segunda lingua grudou no texto-base do primeiro grupo em
        # portugues: sai, e fica so o texto do grupo. O item de espanhol fica
        # com o texto dele, que e em espanhol.
        for item in itens:
            if item.texto_base and item.numero not in de_espanhol:
                item.texto_base = sem_a_outra_lingua(item.texto_base)
    lidos = [item.numero for item in itens]
    if set(lidos) != set(gabarito):
        raise ValueError(f"o caderno tem os itens {lidos[:1]}..{lidos[-1:]} ({len(lidos)}) "
                         f"e o gabarito {min(gabarito)}..{max(gabarito)} ({len(gabarito)})")
    questoes = []
    for item in itens:
        if not _dentro(item.numero, ler) or not item.afirmacao:
            continue
        materia = materia_da_faixa(item.numero, materias) if materias else None
        if materias and not materia:
            continue
        letra = gabarito[item.numero]
        enunciado = "\n\n".join(p for p in (item.comando, item.afirmacao) if p)
        questoes.append(Questao(
            numero=item.numero, enunciado=enunciado, alternativas=dict(ALTERNATIVAS),
            resposta=RESPOSTA_DA_LETRA[letra], materia=materia, anulada=letra == "X",
            texto_base=item.texto_base))
    return questoes

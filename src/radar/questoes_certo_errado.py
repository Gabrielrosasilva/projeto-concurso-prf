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
# reconhece-lo, o cabecalho grudava no item do fim da pagina.
MOBILIA_DO_CADERNO = re.compile(
    r"^\s*(?:(?:\|\|\S+\|\|\s*|\d+_\d+N\d+\s+)?(?:CESPE\s*\|\s*)?CEBRASPE\s*[–-]"
    r"|[A-ZÁÉÍÓÚÂÊÔÃÕÇ]+(?: [A-ZÁÉÍÓÚÂÊÔÃÕÇ]+)*\s*$)")
ESPACO_LIVRE = re.compile(r"\s*Espa[çc]o\s+livre\s*")
# O rotulo do texto, com o codigo ("Texto 1A18-I") ou sem ("Texto", na Policia
# Civil de Sergipe de 2018): sem o codigo, o texto so nao se cita pelo nome.
ROTULO_DO_TEXTO = re.compile(r"^\s*Texto(?:\s+([0-9A-Z]+(?:-[IVX]+)?))?\s*$")
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
JULGUE = re.compile(r"\b(?:julgue|judge|juzgue)\b", re.IGNORECASE)
FIM_DE_FRASE = re.compile(r"[.!?:)”\"]\s*$")
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
            return indice
    comando = _comeco_do_comando(linhas[1:])
    return len(linhas) if comando is None else comando + 1


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
            rotulo = achado.group(1) if achado else None
            inicio = indice + 1 if achado else indice
            break
    texto = None
    if inicio is not None:
        texto = religar(_juntar_linhas(antes[inicio:], palavras), palavras) or None
        if texto and rotulo:
            textos[rotulo.upper()] = texto
    if texto is None:
        citado = re.search(r"\btexto\s+([0-9A-Z]+-[IVX]+)", comando, re.IGNORECASE)
        texto = textos.get(citado.group(1).upper()) if citado else None
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
    comando, texto_base = _ler_cabecalho(linhas[:inicios[0]], textos, palavras)
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


def ler_gabarito_do_cebraspe(texto: str) -> dict[int, str]:
    """{item: "C", "E" ou "X"} do gabarito definitivo de Certo/Errado.

    No texto do pdfminer a grade sai em pares, numero e letra ("9 C 29 E 49 E
    69 X"). ValueError quando o mesmo item tem duas letras, quando nao ha item
    nenhum ou quando falta item no meio: gabarito pela metade nunca entra.
    """
    pedacos = texto.split()
    gabarito: dict[int, str] = {}
    for numero, letra in zip(pedacos, pedacos[1:]):
        if numero.isdigit() and letra in RESPOSTA_DA_LETRA:
            item = int(numero)
            if gabarito.get(item, letra) != letra:
                raise ValueError(f"item {item} com duas letras no gabarito")
            gabarito[item] = letra
    if not gabarito:
        raise ValueError("o gabarito nao tem item de Certo/Errado")
    faltam = sorted(set(range(min(gabarito), max(gabarito) + 1)) - set(gabarito))
    if faltam:
        raise ValueError(f"faltam itens no gabarito: {faltam[:5]}")
    return gabarito


def ler_caderno(caminho: Path, caminho_do_gabarito: Path | None, ler: list[str] | None = None,
                materias: list[tuple[int, int, str]] | None = None,
                texto: str | None = None, texto_do_gabarito: str | None = None,
                palavras: set[str] | None = None) -> list[Questao]:
    """Os itens do caderno de Certo/Errado do Cebraspe, como questoes, com a
    resposta do gabarito DEFINITIVO.

    O item de figura (o numero sem texto nenhum) fica de fora: sem a figura
    ele nao se responde. ValueError quando os itens lidos nao sao os do
    gabarito. `texto`, `texto_do_gabarito` e `palavras` sao para o teste, que
    nao le PDF.
    """
    from radar.questoes import extrair_texto

    if texto_do_gabarito is None:
        if caminho_do_gabarito is None:
            raise ValueError("falta o gabarito definitivo")
        texto_do_gabarito = _texto_do_pdfminer(caminho_do_gabarito)
    gabarito = ler_gabarito_do_cebraspe(texto_do_gabarito)
    if texto is None:
        texto = extrair_texto(caminho)
    paragrafos = None
    if palavras is None:
        texto_do_pdfminer = _texto_do_pdfminer(caminho)
        palavras = vocabulario(texto_do_pdfminer)
        # So no caderno em que o pypdf perdeu TODO recuo (FUB e SEE/DF de
        # 2016). Onde ele o tem (a PRF, a SEE/PE de 2022), o pdfminer parte o
        # texto linha a linha, e a marca dele separava a segunda frase do item.
        if not any(linha.startswith("  ") for linha in texto.splitlines()):
            paragrafos = inicios_de_paragrafo(texto_do_pdfminer)

    itens = itens_do_caderno(texto, palavras, primeiro=min(gabarito), paragrafos=paragrafos)
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

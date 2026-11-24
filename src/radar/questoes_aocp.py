"""Separa em questoes o caderno do Instituto AOCP, a banca da PMSC 2026
(Etapa 3 do pedido da PMSC, decisao PMSC-6).

O caderno da AOCP e igual em todos os concursos de policia que ela fez (PM-ES,
PM-GO, PM-PE, PM-DF, PC-PA, PC-GO, SAP-SP, SEJUSP-MG):

  - **a questao** e o numero sozinho na linha, e **a alternativa** "(A)" a
    "(E)" - ou a "(D)", na SAP-SP;
  - **toda pagina** tem "CARGO  Tipo  01 – Pagina 2" no cabecalho. O PDF da
    PM-ES e o da PM-GO juntam os 4 tipos, um depois do outro, e so entram as
    paginas do tipo da lista: a letra certa da questao 30 no Tipo 1 nao e a do
    Tipo 2 (a regra da decisao 172);
  - **o texto de Portugues** vem antes das questoes dele, aberto por "O texto
    a seguir refere-se as questoes 1 a 12.", e vai para o `texto_base` de
    cada uma (so no banco, decisao 132).

O texto sai do `pdfminer`, e nao do `pypdf` dos outros leitores: no texto
justificado da AOCP o `pypdf` poe espaco no meio da palavra ("o utros",
"Y an", "contra ir", "conclus ao"), e o `pdfminer`, com a margem entre letras
maior, devolve a linha inteira e na ordem. Com a margem padrao ele partia a
linha justificada em pedacos e os embaralhava.

O gabarito tem dois formatos:

  - **o pos-recursos da AOCP**: um bloco por cargo e tipo, "SOLDADO
    COMBATENTE (QPMP-C) - PROVA  1", com a fileira dos numeros e, embaixo, a
    das letras; o X e a anulada. O PDF pode trazer outros cargos (o da PM-GO
    comeca pelo Soldado Musico), e so vale o bloco do cargo da lista;
  - **a lista do pciconcursos** (PM-PE): "1 D 2 A 3 B ...", de um tipo so.
    Numero repetido (o 2o Tenente da PM-PE tem duas respostas da 11 a 15, as
    das duas linguas estrangeiras) sai do gabarito, e a questao fica sem
    resposta.

A questao lida que o gabarito nao tem faz o caderno inteiro ser recusado: a
lista tem de deixa-la de fora pelo `ler`.
"""
import re
import unicodedata
from pathlib import Path

from radar.gabarito_por_versao import SO_LETRAS, SO_NUMEROS
from radar.questoes import Questao, _limpar, _tirar_simbolo_sem_desenho
from radar.questoes_por_rodada import (MARCAS_DA_QUESTAO, PADRAO_TITULO,
                                       _titulos_antes_das_marcas, dividir_em_questoes,
                                       sem_cabecalho)

# "Tipo  01 – Pagina 2" no cabecalho de toda pagina.
PADRAO_TIPO = re.compile(r"\bTipo\s+0?([1-9])\b")
# O mesmo cabecalho com o numero em branco ("Tipo   – Pagina 2").
PADRAO_TIPO_EM_BRANCO = re.compile(r"\bTipo\s+[–-]\s+P[áa]gina\b")

# "SOLDADO COMBATENTE (QPMP-C) - PROVA  1": o cargo e tudo antes do ultimo
# " - PROVA", porque o nome do cargo tambem tem hifen ("Soldado de 2a Classe
# QPPM - Combatente").
PADRAO_BLOCO = re.compile(r"^\s*(?P<cargo>.+?)\s*[-–]\s*PROVA\s+0?(?P<tipo>[1-9])\s*$")

# "O texto a seguir refere-se às questões 1 a 12." (PM-ES, PM-GO), "Leia o
# texto a seguir para responder às questões de 1 a 10." (SAP-SP), que quebra
# em duas linhas, ou "Responda as questões de 1 a 8 de acordo com o texto a
# seguir." (PM-DF).
PADRAO_TEXTO_BASE = re.compile(
    r"(?:O\s+texto\s+a\s+seguir\s+refere-se\s+[àa]s|Leia\s+o\s+texto\s+a\s+seguir\s+para\s+responder"
    r"\s+[àa]s|Responda\s+[àa]s?)"
    r"\s+quest[õo]es\s+(?:de\s+)?(\d{1,3})\s+a\s+(\d{1,3})"
    r"(?:\s+de\s+acordo\s+com\s+o\s+texto\s+a\s+seguir)?\.")

# O hifen no fim da linha. A AOCP nunca parte palavra por silaba: o hifen ali
# e da palavra ("mantê-|la", "recém-|completos"), e a limpeza comum, que junta
# a silaba partida, o apagaria - numa questao de colocacao pronominal.
HIFEN_NO_FIM_DA_LINHA = re.compile(r"(\w)-\n(\w)")

# A PM-PE e a PC-PA nao tem o aviso: o texto vem logo depois do titulo da
# materia, e vale para as questoes ate o titulo seguinte.
PADRAO_TITULO_DE_PORTUGUES = re.compile(r"(?m)^[ \t]*L[íi]ngua Portuguesa[ \t]*$")

# Um texto de verdade, e nao o titulo de materia que caiu antes da questao.
TAMANHO_MINIMO_DO_TEXTO = 400

# A redacao (ou a discursiva) fica no fim do caderno, e o que vem depois dela
# nao e questao objetiva: sem o corte, as instrucoes grudavam na ultima
# alternativa (a "(E)" da 80 da PM-ES levava 2.400 letras delas).
PADRAO_REDACAO = re.compile(
    r"(?m)^[ \t]*(?:Instru[cç][oõ]es\s+para\s+(?:a\s+)?(?:Prova\s+)?(?:de\s+)?"
    r"(?:Reda[cç][aã]o|Discursiva)|Prova\s+Discursiva|Discursiva)[ \t]*$")

# O que abre a materia seguinte e o leitor por rodada nao reconhece como
# titulo: o de Goias (tres linhas, a primeira em minuscula depois da 1a
# palavra) e a instrucao da lingua estrangeira do 2o Tenente da PM-PE.
PADRAO_FIM_DO_BLOCO = re.compile(
    r"Realidade [eé]tnica, social|Responda somente [àa] L[íi]ngua Estrangeira")

# A marca d'agua do pciconcursos no topo de toda pagina do gabarito, que cai
# entre o numero da questao e a letra dela na virada da pagina.
PADRAO_MARCA_DAGUA = re.compile(r"(?m)^.*(?:pcimark|pciconcursos).*$")

# A margem entre letras que mantem a linha justificada inteira. Com a padrao
# (2.0), "informacoes incorretas, afirma Guido Zuccon," saia partida em tres
# linhas, fora de ordem.
MARGEM_ENTRE_LETRAS = 8

# A altura, em pontos, do cabecalho ("POLICIA MILITAR DO ESPIRITO SANTO" e
# "INSTITUTO AOCP") e do rodape ("SOLDADO COMBATENTE" e "Tipo 01 – Pagina 5"),
# que ficam fora das colunas.
FAIXA_DAS_PONTAS = 60

# Quantas linhas com letra em cima do meio da pagina fazem dela uma pagina de
# uma coluna so. Nos 11 cadernos de 23/10, a de duas colunas tem 0, e a de
# uma coluna, 12 ou mais.
LINHAS_DE_UMA_COLUNA = 3


def nome_da_versao(tipo: int | str) -> str:
    """"TIPO 1", do jeito que a lista escreve."""
    return f"TIPO {int(tipo)}"


def _linhas(objeto, saida: list) -> None:
    """As linhas de texto da pagina, tambem as de dentro das figuras."""
    from pdfminer.layout import LTFigure, LTTextBox, LTTextLine

    for filho in objeto:
        if isinstance(filho, LTTextLine):
            saida.append(filho)
        elif isinstance(filho, (LTTextBox, LTFigure)):
            _linhas(filho, saida)


def _pedacos_por_coluna(linha, meio: float) -> list[tuple[int, float, str]]:
    """A linha partida onde ela cruza o meio da pagina: [(coluna, x0, texto)].
    Com a margem larga, o `pdfminer` as vezes junta numa linha so a linha da
    coluna da esquerda e a da direita na mesma altura ("(D) Os subsidios do
    Governador, do" + "perda do cargo, devera obter licenca", na PM-PE).

    A letra e o item com posicao (`x0`); o espaco que o `pdfminer` poe entre
    as palavras (`LTAnno`) nao tem, e fica no pedaco em que caiu."""
    pedacos: list[list] = []
    for item in linha:
        if hasattr(item, "x0"):
            coluna = 0 if (item.x0 + item.x1) / 2 < meio else 1
            if not pedacos or pedacos[-1][0] != coluna:
                pedacos.append([coluna, item.x0, ""])
        elif not pedacos:
            continue
        pedacos[-1][2] += item.get_text()
    return [(coluna, x0, texto.rstrip("\n")) for coluna, x0, texto in pedacos]


def _ordem_de_leitura(linha, coluna: int, x0: float, altura: float) -> tuple:
    """O cabecalho, a coluna da esquerda de cima para baixo, a da direita, e
    o rodape. O `pdfminer` sozinho punha a coluna da direita antes da
    esquerda, e a alternativa longe da questao dela."""
    if linha.y0 > altura - FAIXA_DAS_PONTAS:
        return (0, 0, -linha.y1, x0)
    if linha.y1 < FAIXA_DAS_PONTAS:
        return (2, 0, -linha.y1, x0)
    return (1, coluna, -linha.y1, x0)


def _sem_marca_dagua(linhas: list) -> list:
    """Sem a linha da marca d'agua do pciconcursos (PM-PE): ela cruza a
    pagina - partida no meio, metade ia para cada coluna - e traz o endereco
    de quem baixou. Sai inteira, antes de tudo."""
    return [linha for linha in linhas if not PADRAO_MARCA_DAGUA.search(linha.get_text())]


def _uma_coluna(linhas: list, largura: float, altura: float) -> bool:
    """A pagina e de uma coluna so quando varias linhas do corpo tem letra em
    cima do meio da pagina, onde a de duas colunas tem o vao entre elas. A
    11 da SAP-SP (a questao com a tabela do Excel) e a 5 do 2o Tenente da
    PM-PE sao assim; a capa e a redacao tambem."""
    meio = largura / 2
    cruzam = sum(
        1 for linha in linhas
        if FAIXA_DAS_PONTAS < linha.y1 and linha.y0 < altura - FAIXA_DAS_PONTAS
        and any(hasattr(c, "x0") and c.get_text().strip() and c.x0 < meio < c.x1
                for c in linha))
    return cruzam >= LINHAS_DE_UMA_COLUNA


def paginas_do_caderno(caminho: Path) -> list[str]:
    """O texto de cada pagina, pelo `pdfminer`, linha a linha e coluna por
    coluna. O texto da AOCP fica dentro de uma figura por pagina, e o
    `all_texts` faz o `pdfminer` analisar as linhas dela."""
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LAParams

    from radar.destaques import _pdf_que_o_pdfminer_le

    paginas = []
    parametros = LAParams(all_texts=True, char_margin=MARGEM_ENTRE_LETRAS)
    for pagina in extract_pages(_pdf_que_o_pdfminer_le(caminho), laparams=parametros):
        linhas: list = []
        _linhas(pagina, linhas)
        linhas = _sem_marca_dagua(linhas)
        # Na de uma coluna, o "meio" fica alem da pagina: nada e partido.
        meio = (pagina.width * 2 if _uma_coluna(linhas, pagina.width, pagina.height)
                else pagina.width / 2)
        pedacos = [(_ordem_de_leitura(linha, coluna, x0, pagina.height), texto)
                   for linha in linhas
                   for coluna, x0, texto in _pedacos_por_coluna(linha, meio)]
        pedacos.sort(key=lambda p: p[0])
        texto = "".join(t + "\n" for _, t in pedacos if t.strip())
        paginas.append(_tirar_simbolo_sem_desenho(texto))
    return paginas


def paginas_da_versao(paginas: list[str], versao: str) -> list[str]:
    """So as paginas do tipo da lista. A capa ("PROVA 01", sem o "Tipo") e
    a pagina da redacao ficam com o tipo da pagina anterior, e nao tem
    questao objetiva. O caderno com o numero do tipo em branco ("Tipo   –
    Pagina 2", a Policia Penal PR 2024) so tem uma versao: valem todas."""
    if (not any(PADRAO_TIPO.search(p) for p in paginas)
            and any(PADRAO_TIPO_EM_BRANCO.search(p) for p in paginas)):
        return list(paginas)
    saida, atual = [], None
    for pagina in paginas:
        achado = PADRAO_TIPO.search(pagina)
        if achado:
            atual = nome_da_versao(achado.group(1))
        if atual == versao:
            saida.append(pagina)
    return saida


def _normal(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


def blocos_do_gabarito(texto: str) -> dict[tuple[str, str], dict[int, str | None]]:
    """{(cargo, "TIPO 1"): {numero: letra, ou None na anulada}} do gabarito
    pos-recursos da AOCP. O cargo vai normalizado (sem acento, minusculo)."""
    saida: dict[tuple[str, str], dict[int, str | None]] = {}
    atual: dict[int, str | None] | None = None
    numeros: list[int] = []
    for linha in texto.splitlines():
        cabecalho = PADRAO_BLOCO.match(linha)
        if cabecalho:
            chave = (_normal(cabecalho.group("cargo")), nome_da_versao(cabecalho.group("tipo")))
            if chave in saida:
                raise ValueError(f"o gabarito tem dois blocos de {chave[0]} - {chave[1]}")
            atual = saida[chave] = {}
            numeros = []
        elif atual is not None and SO_NUMEROS.match(linha):
            numeros = [int(n) for n in linha.split()]
        elif atual is not None and numeros and SO_LETRAS.match(linha):
            letras = linha.split()
            if len(letras) != len(numeros):
                raise ValueError(f"a fileira {numeros[0]}-{numeros[-1]} tem "
                                 f"{len(letras)} letras para {len(numeros)} questoes")
            for numero, letra in zip(numeros, letras):
                atual[numero] = None if letra.upper() == "X" else letra.lower()
            numeros = []
    return saida


def gabarito_da_lista(texto: str) -> tuple[dict[int, str | None], set[int]]:
    """({numero: letra}, numeros repetidos) da lista do pciconcursos: depois
    de "Gabarito", pares de numero e letra (X e a anulada). O numero que vem
    duas vezes sai do gabarito."""
    depois = texto.split("Gabarito", 1)[-1]
    pares = re.findall(r"(?<![\w])(\d{1,3})\s+([A-EX])(?![\w])", depois)
    respostas: dict[int, str | None] = {}
    repetidas: set[int] = set()
    for numero, letra in pares:
        numero = int(numero)
        if numero in respostas or numero in repetidas:
            repetidas.add(numero)
            respostas.pop(numero, None)
            continue
        respostas[numero] = None if letra == "X" else letra.lower()
    return respostas, repetidas


def ler_gabarito(caminho: Path, versao: str, cargo: str | None) -> dict[int, str | None]:
    """O gabarito da versao e do cargo, do PDF (`respostas_do_gabarito`).

    O gabarito que so existe em imagem (a PM-DF 2023 e a SEJUSP-MG 2026: uma
    tabela sem texto) vem transcrito num .txt, na forma da lista ("1 C"), com
    quem transcreveu escrito antes da palavra "Gabarito".
    """
    if caminho.suffix.lower() == ".txt":
        return respostas_do_gabarito(caminho.read_text(encoding="utf-8"), versao, cargo)
    from pypdf import PdfReader

    texto = "\n".join((p.extract_text() or "") for p in PdfReader(str(caminho)).pages)
    return respostas_do_gabarito(texto, versao, cargo)


def respostas_do_gabarito(texto: str, versao: str, cargo: str | None) -> dict[int, str | None]:
    """Com bloco "CARGO - PROVA N", so o do cargo e da versao da lista; sem
    bloco nenhum, a lista do pciconcursos. ValueError quando o texto tem
    blocos e nenhum e o do cargo e da versao."""
    texto = PADRAO_MARCA_DAGUA.sub("", texto)
    blocos = blocos_do_gabarito(texto)
    if blocos:
        chave = (_normal(cargo or ""), versao)
        if chave not in blocos:
            raise ValueError(f"o gabarito nao tem o bloco de {cargo} - {versao}; tem "
                             + "; ".join(f"{c} - {v}" for c, v in blocos))
        return blocos[chave]
    respostas, _repetidas = gabarito_da_lista(texto)
    if not respostas:
        raise ValueError("o gabarito nao tem bloco nem lista de respostas")
    return respostas


def textos_base(texto: str) -> dict[int, str]:
    """{numero da questao: texto de Portugues que ela usa}.

    Com o aviso ("refere-se as questoes 1 a 12"), o texto vai dele ate o
    numero da primeira questao sozinho na linha, e vale para as do aviso. Sem
    aviso nenhum (PM-PE, PC-PA), o texto e o que fica entre o titulo "Lingua
    Portuguesa" e a primeira questao, e vale ate a questao antes do titulo da
    materia seguinte."""
    saida: dict[int, str] = {}
    for aviso in PADRAO_TEXTO_BASE.finditer(texto):
        primeira, ultima = int(aviso.group(1)), int(aviso.group(2))
        marca = _marca_da_questao(primeira).search(texto, aviso.end())
        if marca:
            corpo = _paragrafos(texto[aviso.end():marca.start()])
            for numero in range(primeira, ultima + 1):
                saida[numero] = corpo
    if saida:
        return saida

    titulo = PADRAO_TITULO_DE_PORTUGUES.search(texto)
    marcas = list(MARCAS_DA_QUESTAO["numero"].finditer(texto))
    depois = [m for m in marcas if titulo and m.start() > titulo.end()]
    if not depois or depois[0].start() - titulo.end() < TAMANHO_MINIMO_DO_TEXTO:
        return saida
    corpo = _paragrafos(texto[titulo.end():depois[0].start()])
    titulos = sorted(set(_titulos_antes_das_marcas(texto, marcas))
                     | {t.start() for t in PADRAO_TITULO.finditer(texto)})
    seguinte = next((t for t in titulos if t > depois[0].end()), len(texto))
    for marca in depois:
        if marca.start() >= seguinte:
            break
        saida[int(marca.group(1))] = corpo
    return saida


def _marca_da_questao(numero: int) -> re.Pattern:
    return re.compile(rf"(?m)^[ \t]*{numero}[ \t]*$")


def _paragrafos(trecho: str) -> str:
    """O texto com os paragrafos, para a tela mostrar como no caderno: o
    paragrafo abre numa linha em branco ou numa linha com recuo."""
    paragrafos = re.split(r"\n[ \t]*\n|\n(?=[ \t]+\S)", trecho)
    return "\n\n".join(_limpar(p) for p in paragrafos if p.strip())


def questoes_do_texto(texto: str, respostas: dict[int, str | None],
                      ler: list[str] | None = None, letras: str = "ABCDE",
                      materias: list[tuple[int, int, str]] | None = None) -> list[Questao]:
    """As questoes do texto das paginas do tipo (ja sem o cabecalho), com a
    resposta do gabarito e a materia da faixa da lista (`materias`, de
    `questoes_selecon.faixas_do_config`). ValueError quando uma questao lida
    nao tem resposta no gabarito."""
    texto = HIFEN_NO_FIM_DA_LINHA.sub(r"\1-\2", texto)
    redacao = PADRAO_REDACAO.search(texto)
    if redacao:
        texto = texto[:redacao.start()]
    questoes = dividir_em_questoes(texto, respostas, marca="numero",
                                   alternativa="parenteses", letras=letras, ler=ler)
    sem_resposta = [q.numero for q in questoes if q.numero not in respostas]
    if sem_resposta:
        raise ValueError(f"o gabarito nao tem as questoes {sem_resposta}: "
                         "deixe-as de fora pelo `ler`")
    base = textos_base(texto)
    for questao in questoes:
        questao.texto_base = base.get(questao.numero)
        questao.materia = next((nome for inicio, fim, nome in materias or []
                                if inicio <= questao.numero <= fim), None)
        _sem_o_aviso_do_texto(questao)
    return questoes


def ler_prova(caminho: Path, gabarito: Path, versao: str = "TIPO 1",
              cargo_no_gabarito: str | None = None, ler: list[str] | None = None,
              letras: str = "ABCDE",
              materias: list[tuple[int, int, str]] | None = None) -> list[Questao]:
    """As questoes do tipo da lista, com a resposta do gabarito do mesmo tipo
    e cargo. ValueError quando nenhuma pagina e do tipo, ou quando uma
    questao lida nao tem resposta no gabarito."""
    paginas = paginas_da_versao(paginas_do_caderno(caminho), versao)
    if not paginas:
        raise ValueError(f"nenhuma pagina do caderno e do {versao}")
    respostas = ler_gabarito(gabarito, versao, cargo_no_gabarito)
    return questoes_do_texto(sem_cabecalho(paginas, tirar_numeros=False), respostas,
                             ler=ler, letras=letras, materias=materias)


def _sem_o_aviso_do_texto(questao: Questao) -> None:
    """O aviso do texto seguinte, ou o bloco que abre a materia seguinte,
    gruda no fim da ultima alternativa antes dele: a "(E) hiperonimia." da 12
    da PM-ES levava "O texto a seguir refere-se as questoes 13 a 20.", e a
    10 da PM-GO, o titulo "Realidade etnica... do Estado de Goias". Sai o
    aviso e o que vier depois."""
    for letra, conteudo in questao.alternativas.items():
        achado = PADRAO_TEXTO_BASE.search(conteudo) or PADRAO_FIM_DO_BLOCO.search(conteudo)
        if achado:
            questao.alternativas[letra] = conteudo[:achado.start()].strip()


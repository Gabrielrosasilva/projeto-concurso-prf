"""A prova comentada por professor de cursinho (FCC DETRAN/SP 2019, PRF-70).

Nem sempre o caderno oficial esta ao alcance: o robots.txt da FCC proibe robo,
e o Gabriel baixou a prova comentada que a Estrategia publicou no blog (o
professor transcreve cada questao, comenta e da a letra). O formato:

    21. [FCC – AGENTE ESTADUAL DE TRÂNSITO – DETRAN/SP - 2019]
    Quanto ao curso preventivo de reciclagem, considere: ...
    (A) I e III.
    ...
    (E) I.
    Comentário:
    ... o comentario do professor, com artigo de lei ...
    Gabarito: E

e, no fim, o quadro "GABARITO" (fileira de numeros, fileira de letras; "E**"
e o item que o professor acha "anulável").

Por que leitor proprio, e nao o `questoes_por_rodada`: o comentario cita
incisos e alineas que se parecem com alternativas, e a letra mora em dois
lugares. Aqui so entra o texto ANTES de "Comentário:", e a letra do quadro
final tem que bater com a do "Gabarito:" da propria questao - se nao bate, a
questao fica de fora (melhor faltar do que medir errado).

A letra e a do PROFESSOR, nao a da banca: a lista diz isso em
`gabarito_a_conferir`, e a questao treina e nao mede (`metricas.QUE_MEDE`).
O comentario nao e guardado (texto de terceiro, e o radar tem a ficha dele).
"""
import re
from pathlib import Path

from radar.questoes import Questao
from radar.questoes_selecon import materia_da_faixa

#: "21. [FCC – AGENTE ESTADUAL DE TRÂNSITO – DETRAN/SP - 2019]" abre a questao.
CABECALHO = re.compile(r"^\s*(\d{1,3})\.\s*\[[^\]]+\]\s*$", re.MULTILINE)
#: "(A) texto" no comeco da linha.
ALTERNATIVA = re.compile(r"^\s*\(([A-E])\)\s*", re.MULTILINE)
COMENTARIO = re.compile(r"^\s*Coment[áa]rio\s*:", re.MULTILINE)
GABARITO_DA_QUESTAO = re.compile(r"Gabarito\s*:\s*([A-E])\b")
#: O quadro final: "GABARITO" sozinho na linha, depois as fileiras.
QUADRO = re.compile(r"^\s*GABARITO\s*$", re.MULTILINE)
SO_NUMEROS = re.compile(r"^\s*\d{1,3}(?:\s+\d{1,3})+\s*$")
SO_LETRAS = re.compile(r"^\s*[A-E]\**(?:\s+[A-E]\**)+\s*$")
#: As linhas de cima de toda pagina: em branco, o numero da pagina e o total.
SO_NUMERO_DA_PAGINA = re.compile(r"^\s*\d*\s*$")


def _uma_linha(texto: str) -> str:
    return " ".join(texto.split())


def sem_numero_da_pagina(pagina: str) -> str:
    """Tira as linhas do topo que so tem o numero da pagina ("2" e "29")."""
    linhas = pagina.splitlines()
    while linhas and SO_NUMERO_DA_PAGINA.match(linhas[0]):
        linhas.pop(0)
    return "\n".join(linhas)


def ler_quadro(texto: str) -> dict[int, str | None]:
    """{questao: letra} do quadro final. "E**" (anulável para o professor)
    vira None: nao entra."""
    achado = QUADRO.search(texto)
    if not achado:
        return {}
    respostas: dict[int, str | None] = {}
    numeros = None
    for linha in texto[achado.end():].splitlines():
        if SO_NUMEROS.match(linha):
            numeros = [int(n) for n in linha.split()]
        elif SO_LETRAS.match(linha) and numeros:
            letras = linha.split()
            if len(letras) != len(numeros):
                raise ValueError(f"quadro: {len(numeros)} numeros e {len(letras)} letras")
            for n, letra in zip(numeros, letras):
                respostas[n] = None if letra.endswith("*") else letra.lower()
            numeros = None
    return respostas


def dividir(texto: str, quadro: dict[int, str | None]) -> list[Questao]:
    """As questoes do texto. Fica de fora a que nao tem as cinco alternativas
    em texto (vinham em imagem), a anulavel e a de letra que nao bate."""
    cabecalhos = list(CABECALHO.finditer(texto))
    saida = []
    for i, cabecalho in enumerate(cabecalhos):
        numero = int(cabecalho.group(1))
        fim = cabecalhos[i + 1].start() if i + 1 < len(cabecalhos) else len(texto)
        bloco = texto[cabecalho.end():fim]
        corte = COMENTARIO.search(bloco)
        if not corte:
            continue
        da_questao = GABARITO_DA_QUESTAO.search(bloco[corte.end():])
        letra = quadro.get(numero)
        if letra is None or not da_questao or da_questao.group(1).lower() != letra:
            continue
        enunciado_e_alternativas = bloco[:corte.start()]
        marcas = list(ALTERNATIVA.finditer(enunciado_e_alternativas))
        if [m.group(1) for m in marcas] != list("ABCDE"):
            continue
        alternativas = {}
        for j, marca in enumerate(marcas):
            ate = marcas[j + 1].start() if j + 1 < len(marcas) else len(enunciado_e_alternativas)
            alternativas[marca.group(1).lower()] = _uma_linha(enunciado_e_alternativas[marca.end():ate])
        enunciado = _uma_linha(enunciado_e_alternativas[:marcas[0].start()])
        if not enunciado:
            continue
        saida.append(Questao(numero=numero, enunciado=enunciado,
                             alternativas=alternativas, resposta=letra))
    return saida


def ler_prova(caminho: Path, faixas: list[tuple[int, int, str]],
              a_conferir: str | None = None) -> list[Questao]:
    """As questoes das faixas, com a letra do professor."""
    from pypdf import PdfReader

    paginas = [sem_numero_da_pagina(p.extract_text() or "") for p in PdfReader(str(caminho)).pages]
    texto = "\n".join(paginas)
    quadro = ler_quadro(texto)
    if not quadro:
        raise ValueError("a prova comentada nao tem o quadro GABARITO no fim")
    saida = []
    for questao in dividir(texto, quadro):
        questao.materia = materia_da_faixa(questao.numero, faixas)
        if questao.materia is None:
            continue
        questao.gabarito_a_conferir = a_conferir
        saida.append(questao)
    return saida

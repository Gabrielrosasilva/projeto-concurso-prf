"""O caderno de multipla escolha da UECE-CEV (DETRAN/CE 2018, PRF-68).

A CEV/UECE publica o caderno e o gabarito no site dela (cev.uece.br, que
libera robo no robots.txt). Tres coisas o leitor generico
(`questoes_por_rodada`) nao resolvia sozinho:

- **o texto sai picado no modo comum do pypdf** (o caderno veio do Word: cada
  palavra numa linha). No modo `layout` as linhas ficam inteiras, mas a pagina
  vem em DUAS COLUNAS lado a lado - entao aqui a pagina e cortada na coluna e
  a da esquerda vem antes da da direita;
- **a versao se chama "gabarito"**: "O número do gabarito deste caderno de
  prova é 1", e o PDF do gabarito tem um bloco "GABARITO 1" a "GABARITO 4",
  cada um com a fileira de numeros e, embaixo, a de letras. A letra de outro
  bloco mediria errado: o caderno que nao diz o numero e recusado;
- **so o gabarito preliminar esta no ar**: o definitivo do Vistoriador
  (Comunicado 11/2018) aponta para um link que da 404. A lista diz isso em
  `gabarito_a_conferir`, e a questao treina e nao mede (`metricas.QUE_MEDE`).

Depois disso, a divisao em questoes e a do leitor generico: "52." abre a
questao e "A)" a "D)" sao as alternativas. A materia vem das faixas da lista;
o item fora das faixas nao entra (decisao PRF-16).
"""
import re
from collections import Counter
from pathlib import Path

from radar import questoes_por_rodada
from radar.questoes import Questao
from radar.questoes_selecon import materia_da_faixa

#: "O número do gabarito deste caderno de prova é 1."
NUMERO_DO_GABARITO = re.compile(r"n[úu]mero\s+do\s+gabarito\s+deste\s+caderno\s+de\s+prova\s+[ée]\s+(\d)",
                                re.IGNORECASE)
#: "GABARITO 1" sozinho na linha, abrindo o bloco no PDF do gabarito.
BLOCO = re.compile(r"^\s*GABARITO\s+(\d)\s*$", re.IGNORECASE)
SO_NUMEROS = re.compile(r"^\s*\d{1,2}(?:\s+\d{1,2})+\s*$")
SO_LETRAS = re.compile(r"^\s*[A-EX*](?:\s+[A-EX*])+\s*$")
#: O cabecalho de toda pagina de questao: as tres linhas do concurso, e a do
#: numero do gabarito com a pagina. No modo `layout` ele vem de ponta a ponta,
#: e sem tira-lo a frase grudava na ultima alternativa da coluna.
CABECALHO = re.compile(
    r"GOVERNO\s+DO\s+ESTADO\s+DO\s+CEAR|CONCURSO\s+P[ÚU]BLICO\s+DE\s+PROVAS|LOCALIZADAS\s+EM\s+FORTALEZA",
    re.IGNORECASE)
INSTRUCOES = re.compile(r"candidato\s+dever[áa]\s+verificar\s+se\s+seu\s+caderno", re.IGNORECASE)
NUMERO_E_PAGINA = re.compile(
    r"O\s+n[úu]mero\s+do\s+gabarito\s+deste\s+caderno\s+de\s+prova\s+[ée]\s+\d\.?|P\s?[áa]gina\s+\d+")


def corte_da_coluna(linhas: list[str]) -> int | None:
    """A posicao do corredor entre as colunas: a coluna do meio da pagina que
    fica em branco no maior numero de linhas (a da direita nem sempre comeca
    no mesmo lugar - a alternativa vem recuada). None na pagina de uma coluna
    so (a capa), em que nenhuma coluna fica em branco quase sempre."""
    cheias = [linha for linha in linhas if linha.strip()]
    largura = max((len(linha) for linha in cheias), default=0)
    if largura < 60 or len(cheias) < 10:
        return None
    melhor, em_branco = None, 0
    for x in range(int(largura * 0.35), int(largura * 0.65)):
        vazias = sum(1 for linha in cheias if len(linha) <= x or linha[x] == " ")
        if vazias > em_branco:
            melhor, em_branco = x, vazias
    # O cabecalho corrido atravessa o corredor: ele pode, o resto nao.
    return melhor if em_branco >= len(cheias) * 0.85 else None


def em_uma_coluna(pagina: str) -> str:
    """A pagina de duas colunas como uma so: a esquerda inteira e depois a
    direita. A linha do cabecalho, de ponta a ponta, fica na esquerda."""
    linhas = pagina.splitlines()
    corte = corte_da_coluna(linhas)
    if corte is None:
        return pagina
    esquerda, direita = [], []
    for linha in linhas:
        # Cortar no meio de uma palavra (o cabecalho corrido) estragaria a
        # linha: so corta onde o corredor esta em branco.
        if len(linha) > corte and linha[corte] == " ":
            esquerda.append(linha[:corte].rstrip())
            direita.append(linha[corte:].strip())
        else:
            esquerda.append(linha.rstrip())
    return "\n".join(esquerda + direita)


def limpar(pagina: str) -> str:
    """A pagina sem o cabecalho: a linha do concurso sai inteira; o numero do
    gabarito e a pagina saem do meio da linha (o resto dela fica)."""
    linhas = []
    for linha in pagina.splitlines():
        if CABECALHO.search(linha):
            continue
        linhas.append(NUMERO_E_PAGINA.sub(lambda m: " " * len(m.group(0)), linha))
    return "\n".join(linhas)


def numero_do_gabarito(texto: str) -> int | None:
    achados = Counter(int(n) for n in NUMERO_DO_GABARITO.findall(texto))
    return achados.most_common(1)[0][0] if achados else None


def ler_gabarito(texto: str, numero: int) -> dict[int, str | None]:
    """{questao: letra} do bloco "GABARITO <numero>"; X ou * e anulada (None)."""
    respostas: dict[int, str | None] = {}
    bloco_atual, numeros = None, None
    for linha in texto.splitlines():
        achado = BLOCO.match(linha)
        if achado:
            bloco_atual, numeros = int(achado.group(1)), None
            continue
        if bloco_atual != numero:
            continue
        if SO_NUMEROS.match(linha):
            numeros = [int(n) for n in linha.split()]
        elif SO_LETRAS.match(linha) and numeros:
            letras = linha.split()
            if len(letras) != len(numeros):
                raise ValueError(f"gabarito {numero}: {len(numeros)} numeros e {len(letras)} letras")
            for n, letra in zip(numeros, letras):
                respostas[n] = None if letra in ("X", "*") else letra.lower()
            numeros = None
    return respostas


def _texto_do_pdf(caminho: Path, layout: bool) -> list[str]:
    from pypdf import PdfReader

    modo = {"extraction_mode": "layout"} if layout else {}
    return [pagina.extract_text(**modo) or "" for pagina in PdfReader(str(caminho)).pages]


def ler_prova(caminho: Path, gabarito: Path, faixas: list[tuple[int, int, str]],
              a_conferir: str | None = None) -> list[Questao]:
    """As questoes das faixas, com a letra do bloco do gabarito do caderno."""
    paginas = _texto_do_pdf(caminho, layout=True)
    numero = numero_do_gabarito(" ".join(" ".join(p.split()) for p in paginas))
    if numero is None:
        raise ValueError("o caderno nao diz o numero do gabarito")
    respostas = ler_gabarito("\n".join(_texto_do_pdf(gabarito, layout=False)), numero)
    if not respostas:
        raise ValueError(f"o gabarito nao tem o bloco GABARITO {numero}")
    # A capa nao diz o numero do gabarito; a pagina das instrucoes diz, mas as
    # instrucoes numeradas ("1. O candidato devera verificar...") virariam a
    # questao 1. So entra a pagina de questao.
    de_questao = [p for p in paginas if NUMERO_DO_GABARITO.search(" ".join(p.split()))
                  and not INSTRUCOES.search(" ".join(p.split()))]
    texto = questoes_por_rodada.sem_cabecalho([em_uma_coluna(limpar(p)) for p in de_questao])
    lidas = questoes_por_rodada.dividir_em_questoes(
        texto, respostas, marca="ponto", alternativa="fecha", letras="ABCD")
    saida = []
    for questao in lidas:
        questao.materia = materia_da_faixa(questao.numero, faixas)
        if questao.materia is None:
            continue
        if a_conferir:
            questao.gabarito_a_conferir = a_conferir
        saida.append(questao)
    return saida

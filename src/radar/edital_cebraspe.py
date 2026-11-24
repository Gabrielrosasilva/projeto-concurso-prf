"""O programa do edital do Cebraspe: o que cada materia pode cobrar (Etapa 1 da PRF).

O edital da PRF de 2021 (item 24, "objetos de avaliacao") escreve o programa
assim, uma materia por paragrafo, dentro de cada bloco da prova:

    BLOCO I
    LÍNGUA PORTUGUESA: 1 Compreensão e interpretação de textos. 2 Reconhecimento
    de tipos e gêneros textuais. 4 Domínio dos mecanismos de coesão textual.
    4.1 Emprego de elementos de referenciação. 4.2 Emprego de tempos verbais.

Este arquivo le esse texto e devolve as materias com os topicos numerados; e
monta com eles os nos da arvore do radar: materia > assunto (1, 2, 3...) >
subassunto (4.1, 4.2...). O terceiro nivel do edital (3.1.1) nao vira no: fica
no texto do edital do subassunto de cima. O quarto nivel da arvore, o elemento,
e o da classificacao e precisa de tipo - e o edital nao da tipo nenhum.

A regra de sempre (a do `edital_programa`): o texto e o do edital. Tres coisas
sao do radar, e estao ditas aqui:
  - o nome da materia sai da caixa alta ("RACIOCÍNIO LÓGICO-MATEMÁTICO" vira
    "Raciocínio Lógico-Matemático"); o texto do edital guarda o original;
  - o ponto final do topico sai do nome do no (fica no texto do edital);
  - a lista separada por ";" depois de dois-pontos ("Resoluções do CONTRAN e
    suas alterações: 04/1998; 14/1998; ...") vira um filho por item. E assim
    que a questao de uma resolucao acha o no dela.

O texto vem do pdfminer, e nao do pypdf: o pypdf parte a palavra do texto
justificado ("Domí nio", "pr incípios"), e palavra partida no nome do no nao
casa com nada.
"""
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from radar import conteudos as arvore
from radar.regioes import normalizar

# O titulo do item do programa: "24 DOS OBJETOS DE AVALIAÇÃO (HABILIDADES E
# CONHECIMENTOS)". Em caixa alta e no comeco da linha de proposito: o corpo do
# edital cita "os objetos de avaliação constantes do item 24" em minuscula
# (subitem 9.1), e comecar por ali pegaria o edital inteiro.
INICIO = re.compile(r"(?m)^\s*(\d+)\s+DOS\s+OBJETOS\s+DE\s+AVALIA")
FIM = re.compile(r"(?m)^\s*ANEXO\s+I\b")
BLOCO = re.compile(r"^\s*(BLOCO\s+[IVX]+)\s*$")
# A identificacao do edital, para a procedencia de cada no: "EDITAL CONCURSO
# PRF Nº 1, DE 18 DE JANEIRO DE 2021".
IDENTIFICACAO = re.compile(r"EDITAL[^\n]{0,60}?N[º°]\s*\d+[^\n]*?\d{4}")
# A procedencia cabe em 120 caracteres no banco (models.Conteudo).
TAMANHO_DA_PROCEDENCIA = 120

MAIUSCULA = "A-ZÁÉÍÓÚÂÊÔÃÕÇÜ"
# O nome da materia: palavras em caixa alta (com hifen e parenteses) e o
# dois-pontos. So vale no comeco do bloco ou depois do fim de uma frase.
MATERIA = re.compile(
    rf"(?:^|(?<=[.;)] ))([{MAIUSCULA}(][{MAIUSCULA}()\-– ]*[{MAIUSCULA})]) ?: "
)
# A secao com numero romano dentro de uma materia: "I LÍNGUA INGLESA:".
ROMANOS = ("I", "II", "III", "IV", "V")
ROMANO = re.compile(r"^(I|II|III|IV|V)\s")
# O numero do topico: "4", "4.1", "4.4.1." seguido de palavra que comeca em
# maiuscula - e isso que separa o topico "47 Lei..." do "art. 47 do Decreto".
# Quem decide se o numero e topico e o `_topicos`, pelo que vem antes dele.
TOPICO = re.compile(rf"(?:^|(?<= ))(\d+(?:\.\d+)*)\.? (?=[{MAIUSCULA}“\"(])")
# Topico com lista depois do dois-pontos, separada por ";" (duas ou mais).
LISTA = re.compile(r"^(?P<cabeca>[^:]+?):\s*(?P<lista>[^:]+;[^:]+)$")
# As palavras que ficam em minuscula no nome da materia.
LIGACOES = {"e", "ou", "de", "da", "do", "das", "dos", "a", "o", "em", "na", "no"}


@dataclass
class Topico:
    numero: str              # "4.1"; vazio no item de lista (o edital nao numera)
    texto: str               # o texto do edital, sem o numero
    filhos: list["Topico"] = field(default_factory=list)


@dataclass
class Materia:
    nome_no_edital: str      # "RACIOCÍNIO LÓGICO-MATEMÁTICO"
    nome: str                # "Raciocínio Lógico-Matemático"
    bloco: str | None        # "BLOCO I"
    topicos: list[Topico] = field(default_factory=list)


# --- ler o PDF --------------------------------------------------------------

def texto_do_pdf(caminho: Path) -> str:
    """O texto do edital inteiro, pelo pdfminer (o porque esta no topo)."""
    from pdfminer.high_level import extract_text

    # O pdfminer avisa de fonte fora do padrao em quase todo PDF, e nao muda
    # nada no texto - sao dezenas de linhas poluindo a saida do comando.
    logging.getLogger("pdfminer").setLevel(logging.ERROR)
    return extract_text(str(caminho))


def procedencia(texto: str) -> str:
    """De onde vem o no: a identificacao do edital e o numero do item."""
    achado = IDENTIFICACAO.search(texto)
    edital = " ".join(achado.group(0).split()) if achado else "edital do Cebraspe"
    item = INICIO.search(texto)
    texto_da_procedencia = f"{edital}, item {item.group(1)}" if item else edital
    return texto_da_procedencia[:TAMANHO_DA_PROCEDENCIA]


# --- ler o programa ---------------------------------------------------------

def nome_da_materia(no_edital: str) -> str:
    """O nome em caixa alta do edital, escrito como nome de materia.

    Cada palavra com a primeira letra maiuscula, menos as de ligacao ("e",
    "ou", "de"...) que nao abrem o nome. Palavra e sequencia de letras: o
    hifen e o parentese separam, e por isso "LÓGICO-MATEMÁTICO" vira
    "Lógico-Matemático", e nao "Lógico-matemático".
    """
    texto = " ".join(no_edital.split()).lower()

    def palavra(achado: re.Match) -> str:
        if achado.group(0) in LIGACOES and achado.start() > 0:
            return achado.group(0)
        return achado.group(0).capitalize()

    return re.sub(r"[^\W\d_]+", palavra, texto)


def _linhas_do_programa(texto: str) -> list[str]:
    """As linhas entre o titulo do item e o primeiro anexo, sem o que nao e
    programa: o numero da pagina (linha so com numero) e a assinatura do
    diretor-geral (a linha com "DIRETOR" e a do nome logo acima dela)."""
    inicio = INICIO.search(texto)
    if not inicio:
        return []
    fim = FIM.search(texto, inicio.end())
    trecho = texto[inicio.end():fim.start() if fim else len(texto)]
    linhas = [linha for linha in trecho.splitlines()
              if linha.strip() and not linha.strip().isdigit()]
    for posicao, linha in enumerate(linhas):
        if "DIRETOR" in linha and not re.search(r"[a-z]", linha):
            corte = posicao
            if posicao and not re.search(r"[a-z:]", linhas[posicao - 1]):
                corte = posicao - 1
            return linhas[:corte]
    return linhas


def _por_bloco(linhas: list[str]) -> list[tuple[str | None, str]]:
    """[(bloco, texto corrido do bloco)]. O que vem antes do primeiro bloco
    ("24.1 HABILIDADES...") nao e programa e fica de fora."""
    blocos: list[tuple[str | None, list[str]]] = []
    for linha in linhas:
        marca = BLOCO.match(linha)
        if marca:
            blocos.append((" ".join(marca.group(1).split()), []))
        elif blocos:
            blocos[-1][1].append(linha)
    return [(nome, _corrido("\n".join(partes))) for nome, partes in blocos]


def _corrido(texto: str) -> str:
    """O texto do bloco numa linha so, com um espaco entre as palavras.

    A linha que acaba em hifen emenda na de baixo sem espaco e com o hifen:
    no edital ele e da palavra ("inter-\\nregional" e "inter-regional"). E o
    numero "2 .1" volta a "2.1" - o espaco antes do ponto e defeito de
    extracao, nunca do edital.
    """
    texto = re.sub(r"-[ \t]*\n[ \t]*", "-", texto)
    texto = " ".join(texto.split())
    return re.sub(r"(\d) \.(\d)", r"\1.\2", texto)


def _vem_depois(novo: tuple[int, ...], anterior: tuple[int, ...] | None) -> bool:
    """O numero `novo` pode vir depois do `anterior` no programa?

    Filho (4 -> 4.1), irmao (4.1 -> 4.2) ou irmao de um dos pais (4.2 -> 5).
    Pular numero vale: o edital de 2021 vai do 2 direto ao 2.2 em Direito
    Penal, e o texto e o do edital. O que nao vale e voltar - e isso que
    impede um numero solto no meio da frase de virar topico.
    """
    if anterior is None:
        return len(novo) == 1
    if len(novo) == len(anterior) + 1 and novo[:-1] == anterior:
        return True
    for nivel in range(len(anterior), 0, -1):
        if (len(novo) == nivel and novo[:-1] == anterior[:nivel - 1]
                and novo[-1] > anterior[nivel - 1]):
            return True
    return False


def _o_proximo(novo: tuple[int, ...], anterior: tuple[int, ...] | None) -> bool:
    """O `novo` e EXATAMENTE o numero seguinte: o primeiro filho (4 -> 4.1) ou
    o irmao seguinte do anterior ou de um dos pais dele (4.2 -> 4.3, 4.2 -> 5)."""
    if anterior is None:
        return novo == (1,)
    if novo == anterior + (1,):
        return True
    return any(novo == anterior[:nivel - 1] + (anterior[nivel - 1] + 1,)
               for nivel in range(len(anterior), 0, -1))


def _topicos(corpo: str) -> list[Topico]:
    """Os topicos numerados de uma materia (ou de uma secao dela), em arvore.

    O numero que vem depois de ponto, dois-pontos ou ponto e virgula e topico
    se couber na sequencia (`_vem_depois`, que aceita pular numero). O que vem
    sem pontuacao antes so e topico se for exatamente o proximo: o edital de
    2021 esqueceu o ponto em Geopolitica ("principais infraestruturas 8 A
    integração do Brasil..."), e sem isso o 8 sumia dentro do 7.
    """
    marcas = []
    anterior = None
    for achado in TOPICO.finditer(corpo):
        numero = tuple(int(n) for n in achado.group(1).split("."))
        depois_de_pontuacao = achado.start() == 0 or corpo[achado.start() - 2] in ".:;"
        if _vem_depois(numero, anterior) if depois_de_pontuacao else _o_proximo(numero, anterior):
            marcas.append((achado, numero))
            anterior = numero

    raiz: list[Topico] = []
    pilha: list[tuple[tuple[int, ...], Topico]] = []
    for posicao, (achado, numero) in enumerate(marcas):
        fim = marcas[posicao + 1][0].start() if posicao + 1 < len(marcas) else len(corpo)
        topico = Topico(numero=achado.group(1), texto=corpo[achado.end():fim].strip())
        while pilha and pilha[-1][0] != numero[:len(pilha[-1][0])]:
            pilha.pop()
        (pilha[-1][1].filhos if pilha else raiz).append(topico)
        pilha.append((numero, topico))

    for topico in _todos(raiz):
        _abrir_lista(topico)
    return raiz


def _todos(topicos: list[Topico]):
    for topico in topicos:
        yield topico
        yield from _todos(topico.filhos)


def _abrir_lista(topico: Topico) -> None:
    """A lista depois do dois-pontos vira um filho por item (sem numero)."""
    lista = LISTA.match(topico.texto)
    if topico.filhos or not lista:
        return
    for item in lista.group("lista").split(";"):
        item = item.strip().rstrip(".").strip()
        if item:
            topico.filhos.append(Topico(numero="", texto=item))


def _secoes(corpo: str) -> list[Topico]:
    """A materia com secoes em numero romano ("I LÍNGUA INGLESA: 1 ...
    II LÍNGUA ESPANHOLA: 1 ..."): cada secao e um topico com os dela dentro.
    Sem secao, devolve os topicos da materia direto."""
    cabecas = [achado for achado in MATERIA.finditer(corpo)
               if ROMANO.match(achado.group(1))]
    if not cabecas:
        return _topicos(corpo)
    secoes = []
    for posicao, achado in enumerate(cabecas):
        fim = cabecas[posicao + 1].start() if posicao + 1 < len(cabecas) else len(corpo)
        romano, nome = achado.group(1).split(maxsplit=1)
        secoes.append(Topico(numero=romano, texto=nome,
                             filhos=_topicos(corpo[achado.end():fim])))
    return secoes


def ler_programa(texto: str) -> list[Materia]:
    """As materias do programa, na ordem do edital, com os topicos.

    Devolve [] quando o texto nao tem o item dos objetos de avaliacao ou nao
    tem bloco: quem chama diz que nao achou, em vez de semear arvore vazia.
    """
    materias = []
    for bloco, corrido in _por_bloco(_linhas_do_programa(texto)):
        cabecas = [achado for achado in MATERIA.finditer(corrido)
                   if not ROMANO.match(achado.group(1))]
        for posicao, achado in enumerate(cabecas):
            fim = cabecas[posicao + 1].start() if posicao + 1 < len(cabecas) else len(corrido)
            no_edital = " ".join(achado.group(1).split())
            materias.append(Materia(nome_no_edital=no_edital,
                                    nome=nome_da_materia(no_edital), bloco=bloco,
                                    topicos=_secoes(corrido[achado.end():fim])))
    return materias


# --- os nos da arvore -------------------------------------------------------

def _nome_do_no(topico: Topico) -> str:
    """O nome do no: o texto do edital sem o ponto final.

    Duas excecoes: a secao em numero romano ("LÍNGUA INGLESA") sai da caixa
    alta, como o nome da materia; e o topico cuja lista virou filhos fica so
    com a cabeca ("Resoluções do CONTRAN e suas alterações") - a lista esta
    nos filhos. O ">" vira "-": ele e o separador do caminho.
    """
    texto = topico.texto
    if topico.numero in ROMANOS:
        texto = nome_da_materia(texto)
    lista = LISTA.match(texto)
    if lista and topico.filhos and all(not filho.numero for filho in topico.filhos):
        texto = lista.group("cabeca")
    return texto.strip().rstrip(".").strip().replace(arvore.SEPARADOR.strip(), "-")


def _texto_do_edital(topico: Topico) -> str:
    """O texto como esta no edital, com o numero - e, no subassunto, os
    topicos de terceiro nivel dele (que nao viram no)."""
    partes = [f"{topico.numero} {topico.texto}".strip()]
    for neto in _todos(topico.filhos):
        partes.append(f"{neto.numero} {neto.texto}".strip())
    return " ".join(partes)


def nos_da_arvore(materias: list[Materia], procedencia_do_edital: str,
                  taxonomia: arvore.Taxonomia | None = None) -> list[arvore.No]:
    """Os nos que o edital da: materia, assunto e subassunto, pai antes de filho.

    Mais as materias que cairam numa prova do alvo e nao estao neste edital
    (`materias_fora_do_edital` do taxonomia.yml), marcadas assim - como a
    `conteudos.semente` faz com o edital da FEPESE.
    """
    nos: list[arvore.No] = []
    for ordem, materia in enumerate(materias):
        de_onde = (f"{procedencia_do_edital}, {materia.bloco}"
                   if materia.bloco else procedencia_do_edital)[:TAMANHO_DA_PROCEDENCIA]
        raiz = arvore.caminho(None, materia.nome)
        nos.append(arvore.No(caminho=raiz, pai=None, nivel="materia", nome=materia.nome,
                             ordem=ordem, texto_do_edital=materia.nome_no_edital,
                             procedencia=de_onde))
        vistos = {raiz}
        for posicao, assunto in enumerate(materia.topicos):
            caminho_do_assunto = arvore.caminho(raiz, _nome_do_no(assunto))
            if caminho_do_assunto in vistos:
                continue
            vistos.add(caminho_do_assunto)
            # O texto do assunto e so o dele: os subassuntos tem no proprio.
            nos.append(arvore.No(caminho=caminho_do_assunto, pai=raiz, nivel="assunto",
                                 nome=arvore.partes(caminho_do_assunto)[-1], ordem=posicao,
                                 texto_do_edital=f"{assunto.numero} {assunto.texto}".strip(),
                                 procedencia=de_onde))
            for posicao_do_filho, sub in enumerate(assunto.filhos):
                caminho_do_sub = arvore.caminho(caminho_do_assunto, _nome_do_no(sub))
                if caminho_do_sub in vistos:
                    continue
                vistos.add(caminho_do_sub)
                nos.append(arvore.No(caminho=caminho_do_sub, pai=caminho_do_assunto,
                                     nivel="subassunto",
                                     nome=arvore.partes(caminho_do_sub)[-1],
                                     ordem=posicao_do_filho,
                                     texto_do_edital=_texto_do_edital(sub),
                                     procedencia=de_onde))

    ja_tem = {normalizar(no.nome) for no in nos if no.nivel == "materia"}
    for posicao, fora in enumerate((taxonomia.materias_fora_do_edital if taxonomia else [])):
        nome = str(fora.get("nome") or "").strip()
        if not nome or normalizar(nome) in ja_tem:
            continue
        nos.append(arvore.No(caminho=arvore.caminho(None, nome), pai=None, nivel="materia",
                             nome=nome, ordem=len(materias) + posicao, origem="manual",
                             fora_do_edital=True,
                             procedencia=str(fora.get("procedencia") or "") or None))
    return nos

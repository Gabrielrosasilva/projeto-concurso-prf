"""O texto da lei que vai no pedido de geracao (Etapa 4 da PMSC, decisao PMSC-8).

As questoes de Legislacao Institucional, Penal Militar e Transito quase nao tem
questao real - a Institucional nao tem nenhuma, e lei de SC -, e saem do zero.
O pedido da Etapa 4 manda gerar com o texto da lei NO pedido, para a IA
escrever so pelo texto vigente e citar o artigo dele, e nao de memoria.

- **qual texto**: a lista `textos_de_lei.yml` do config diz o arquivo de
  `pmsc/leis/` de cada no; vale o mais especifico (o Estatuto antes da
  Legislacao Institucional inteira). Os arquivos nao vao para o git (sao
  copias locais da Camara e da ALESC, decisao PMSC-4): sem o arquivo, o pedido
  sai sem texto, como antes;
- **sem o riscado**: a ALESC deixa o texto revogado na pagina, riscado com
  `<s>` ou com "text-decoration: line-through" (o Estatuto tem 208 trechos), e
  a IA nao pode escrever pela redacao antiga. O `<s>` que envolve so o "º" de
  "§ 2º" (a LC 587 faz isso 29 vezes) nao e revogacao, e fica;
- **so os artigos do no**: o intervalo sai do nome do no ou de um ancestral -
  "(arts. 1º a 28)", "arts. 256 a 279-A", "art. 23", "arts. 53 e 54". Sem
  intervalo, a lei inteira;
- **com teto**: o trecho maior que `LIMITE` nao vai (a Parte Especial inteira
  do CPM, o CTB inteiro): gere pelo no de baixo, que tem o intervalo.
"""
import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

import yaml

from radar import cache, config
from radar import conteudos as arvore

#: Quantas letras o trecho pode ter. O Decreto 1.601/2021 inteiro (o maior
#: texto de no sem intervalo, cerca de 140 mil) cabe; o CTB inteiro, nao.
LIMITE = 150_000

# O cabecalho do artigo, no comeco da linha: "Art. 3º", "Art. 10.", "Art. 279-A".
# So "Art." com maiuscula: a remissao dentro do texto e "art." minusculo.
PADRAO_ARTIGO = re.compile(r"(?m)^[ \t]*Art\.\s*(\d+)\s*[º°o]?\s*(?:-\s*([A-Z])\b)?")

# O intervalo no nome do no: "arts. 1º a 28", "arts. 256 a 279-A", "art. 23",
# "arts. 53 e 54".
PADRAO_INTERVALO = re.compile(
    r"\barts?\.\s*(\d+)\s*[º°o]?(?:-([A-Z]))?(?:\s*(?:a|e)\s*(\d+)\s*[º°o]?(?:-([A-Z]))?)?",
    re.IGNORECASE)

# O que abre uma linha nova no texto: o paragrafo, a quebra, a celula.
QUEBRAM_A_LINHA = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
                   "table", "blockquote"}
SEM_FIM = {"br", "img", "meta", "link", "hr", "input", "col", "area", "base", "wbr"}
ORDINAIS = {"º", "°", "ª"}


@dataclass
class TextoDaLei:
    fonte: str          # o nome da lei, como a lista escreve
    url: str | None     # onde conferir
    arquivo: str        # a copia local, relativa a pasta do projeto
    artigos: str        # "arts. 1º a 28", ou "a lei inteira"
    texto: str


class _SemRiscado(HTMLParser):
    """O texto do HTML, sem o que esta riscado e sem estilo nem script."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.pedacos: list[str] = []
        self.pilha: list[tuple[str, bool]] = []
        self.riscado = 0
        self.escondido = 0
        self.guardado: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in QUEBRAM_A_LINHA:
            self.pedacos.append("\n")
        if tag in SEM_FIM:
            return
        estilo = (dict(attrs).get("style") or "").replace(" ", "").lower()
        risca = tag in ("s", "strike", "del") or "text-decoration:line-through" in estilo
        if tag in ("script", "style"):
            self.escondido += 1
        if risca:
            self.riscado += 1
            if self.riscado == 1:
                self.guardado = []
        self.pilha.append((tag, risca))

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in SEM_FIM or not any(t == tag for t, _ in self.pilha):
            return
        while self.pilha:
            aberto, risca = self.pilha.pop()
            if aberto in ("script", "style"):
                self.escondido -= 1
            if risca:
                self.riscado -= 1
                if self.riscado == 0:
                    # O riscado que e so o ordinal ("§ 2" + "º") fica.
                    dentro = "".join(self.guardado or []).strip()
                    if dentro and dentro in ORDINAIS:
                        self.pedacos.append(dentro)
                    self.guardado = None
            if aberto == tag:
                break
        if tag in QUEBRAM_A_LINHA:
            self.pedacos.append("\n")

    def handle_data(self, data):
        # A quebra de linha DENTRO do paragrafo e do codigo-fonte do HTML (o
        # da Lei 14.751 poe "Art." numa linha e "1º" na outra): vira espaco.
        # A linha nova so vem do bloco (p, div, br).
        self._texto(re.sub(r"\s+", " ", data))

    def _texto(self, data):
        if self.escondido:
            return
        if self.riscado:
            if self.guardado is not None:
                self.guardado.append(data)
            return
        self.pedacos.append(data)


def texto_plano(html: str) -> str:
    """O texto da pagina, uma linha por paragrafo, sem o riscado."""
    leitor = _SemRiscado()
    leitor.feed(html)
    leitor.close()
    texto = unescape("".join(leitor.pedacos)).replace("\xa0", " ")
    linhas = (re.sub(r"[ \t\r\f\v]+", " ", linha).strip() for linha in texto.split("\n"))
    return "\n".join(linha for linha in linhas if linha)


def _sem_titulos_no_fim(texto: str) -> str:
    """Sem o titulo da secao SEGUINTE, que fica entre o ultimo artigo do
    trecho e o primeiro do proximo ("Relacao de causalidade" no fim do Titulo
    I do CPM): a linha curta que nao termina como frase."""
    linhas = texto.splitlines()
    while len(linhas) > 1 and len(linhas[-1]) < 120 and not re.search(r"[.;:)\]”\"]\s*$", linhas[-1]):
        linhas.pop()
    return "\n".join(linhas)


def _ler_html(caminho: Path) -> str:
    bruto = caminho.read_bytes()
    for codificacao in ("utf-8", "cp1252"):
        try:
            return bruto.decode(codificacao)
        except UnicodeDecodeError:
            continue
    return bruto.decode("latin-1")


def texto_do_arquivo(caminho: Path) -> str:
    return cache.do_arquivo(caminho, lambda: texto_plano(_ler_html(caminho)),
                            nome="textos_de_lei.texto")


def _chave(numero: str, letra: str | None) -> tuple[int, str]:
    return (int(numero), (letra or "").upper())


def intervalo(nome: str) -> tuple[tuple[int, str], tuple[int, str]] | None:
    """((inicio), (fim)) do intervalo de artigos do nome, ou None."""
    achado = PADRAO_INTERVALO.search(nome or "")
    if not achado:
        return None
    inicio = _chave(achado.group(1), achado.group(2))
    fim = _chave(achado.group(3), achado.group(4)) if achado.group(3) else inicio
    return inicio, fim


def trecho(texto: str, inicio: tuple[int, str], fim: tuple[int, str]) -> str | None:
    """Os artigos de `inicio` ate `fim`, inteiros. None quando o texto nao tem
    o artigo de inicio."""
    cabecalhos = [(_chave(m.group(1), m.group(2)), m.start()) for m in PADRAO_ARTIGO.finditer(texto)]
    comeco = next((i for i, (chave, _) in enumerate(cabecalhos) if chave == inicio), None)
    if comeco is None:
        return None
    ate = next((pos for chave, pos in cabecalhos[comeco + 1:] if chave > fim), len(texto))
    return _sem_titulos_no_fim(texto[cabecalhos[comeco][1]:ate].strip())


def _lista(caminho: Path | None = None) -> list[dict]:
    arquivo = caminho or (config.diretorio_config() / "textos_de_lei.yml")
    if not Path(arquivo).exists():
        return []

    def ler():
        return (yaml.safe_load(Path(arquivo).read_text(encoding="utf-8")) or {}).get("textos") or []

    return cache.do_arquivo(Path(arquivo), ler, nome="textos_de_lei.lista")


def do_no(caminho_do_no: str, lista: Path | None = None,
          raiz: Path | None = None) -> TextoDaLei | None:
    """O texto da lei daquele no, ou None: sem item na lista, sem o arquivo,
    sem o artigo de inicio no texto, ou maior que o LIMITE."""
    if not caminho_do_no:
        return None
    candidatos = [item for item in _lista(lista)
                  if caminho_do_no == item["conteudo"]
                  or caminho_do_no.startswith(item["conteudo"] + arvore.SEPARADOR)]
    if not candidatos:
        return None
    item = max(candidatos, key=lambda i: len(i["conteudo"]))
    arquivo = (raiz or config.RAIZ) / item["arquivo"]
    if not arquivo.exists():
        return None
    texto = texto_do_arquivo(arquivo)
    artigos = "a lei inteira"
    # O intervalo do no mais fundo que tem um: o titulo do CPM, o do Estatuto.
    for nome in reversed(arvore.partes(caminho_do_no)):
        achado = intervalo(nome)
        if achado:
            pedaco = trecho(texto, *achado)
            if pedaco is None:
                return None
            texto = pedaco
            artigos = PADRAO_INTERVALO.search(nome).group(0)
            break
    if len(texto) > LIMITE:
        return None
    return TextoDaLei(fonte=item["fonte"], url=item.get("url"), arquivo=item["arquivo"],
                      artigos=artigos, texto=texto)

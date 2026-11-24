"""As questoes que o Gabriel coletou do Qconcursos com o script dele (decisao PMSC-26).

A decisao 166 deixava o Qconcursos fora de robo. Em 02/11/2026 o Gabriel
trouxe a pasta `vltool/`, com 5.631 questoes que o script DELE tirou do site,
e decidiu que elas entram. O radar continua sem consultar o site: ele so le o
banco que o script deixou (`vltool/questoes/questoes.db`), e o coletor fica
com o Gabriel.

O que vale, e por que:

- **o gabarito decide a ordem**. So o gabarito que o proprio Qconcursos
  mostrou e certo (26 de 28 batem com o oficial que o radar ja tinha). A
  "resposta provavel" que uma IA deu (12 de 90 erradas) e a questao sem
  gabarito so entram com o gabarito que o Claude Code buscou (decisao
  PMSC-27, `data/gabaritos_buscados.json`): na lei, na internet (nunca no
  Qconcursos nem no TEC) ou no conhecimento do modelo, sempre dizendo qual.
  Ela vem com o aviso "Verificar a questao" ate o Gabriel conferir, e sem a
  pagina do gabarito so treina (`metricas.so_treina`);
- **cada questao e a sua propria "prova"**: o `prova_url` e o link dela no
  site, e o `numero` e o numero Q do site (Q4408706). O script nao guarda o
  caderno nem o numero na prova, e inventar um dos dois seria pior: o link e
  o original, e o numero Q acha a questao no site;
- **a da AOCP vai para o acervo** (evidencia `complementar`, a regra unica do
  `servico/evidencia.py`), e entra em tudo - treino, Simulado PMSC, "como a
  AOCP cobra", macetes -, MENOS na conta de quanto cai cada assunto: o script
  tirou de 10 a 20 questoes por assunto, e contar isso diria que cai mais o
  que o script escolheu. A de outra banca e `fora`, como toda outra banca;
- **ficam fora**: o Certo/Errado (o treino de outras bancas pede 4
  alternativas), a questao escrita pelo proprio site (banca "Qconcursos"), a
  que tem imagem (a imagem mora no servidor do site), o Portugues de texto (o
  texto-base nao veio) e a que o radar ja tem pelo caderno oficial.
"""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import select

from radar import cache, config, destaques
from radar.db import criar_tabelas, sessao
from radar.models import QuestaoDeProva
from radar.questoes import impressao_de
from radar.servico import evidencia

#: O endereco de toda questao do site. E por ele que o radar reconhece a
#: questao que veio do script: a prova do Qconcursos baixada a mao (decisao
#: 172) tem outro endereco ("/provas/...").
PREFIXO = "https://www.qconcursos.com/questoes-de-concursos/questoes/"

#: Os tres grupos de gabarito do banco do script.
DO_SITE = "do Qconcursos"
PROVAVEL = "provável da IA"
SEM = "sem gabarito"

#: A observacao que o script grava na resposta que uma IA deu.
OBSERVACAO_PROVAVEL = "resposta provavel"

#: Onde o Claude Code achou o gabarito (decisao PMSC-27), como a tela escreve.
COMO = {
    "lei": "pela lei",
    "internet": "na internet",
    "conhecimento": "pelo conhecimento do modelo",
}

#: Os sites que nao servem de fonte de gabarito: os termos dos dois proibem
#: robo (decisao 166), e o gabarito do Qconcursos e justamente o que faltou.
_SITES_FORA = ("qconcursos.com", "tecconcursos.com.br")

#: Por que a questao fica fora desta importacao.
GABARITO_NAO_CONFIRMADO = "gabarito ainda sem confirmação (a busca da etapa seguinte)"
CERTO_ERRADO = "Certo/Errado: o treino de outras bancas pede 4 alternativas"
AUTORIA_DO_SITE = "escrita pelo próprio Qconcursos, não caiu em prova"
IMAGEM = "tem imagem, que mora no servidor do Qconcursos"
PORTUGUES_DE_TEXTO = "Português de texto: o texto-base não veio"
JA_NO_RADAR = "o radar já tem, pelo caderno oficial"
GABARITO_FORA = "o gabarito não é uma das alternativas"
DESTAQUE_PERDIDO = "pede o termo destacado, e a marca não veio no HTML do site"

#: A palavra que diz que a questao de Portugues depende de um texto que o
#: script nao trouxe. "Ignora tudo que for de texto" (Gabriel, 02/11): mesmo
#: quando o trecho vem no enunciado, a pergunta costuma ler o texto em volta.
_DE_TEXTO = re.compile(
    r"\b(texto|textos|trecho|trechos|excerto|excertos|par[aá]grafo|par[aá]grafos"
    r"|fragmento|fragmentos|linha|linhas|tirinha|charge|quadrinho|quadrinhos)\b",
    re.IGNORECASE)

#: A questao que pede para olhar um trecho marcado ("o termo destacado").
_PEDE_DESTAQUE = re.compile(r"destacad|sublinhad|grifad|negrito|em destaque", re.IGNORECASE)

#: O negrito que cobre quase o campo inteiro e enfeite do site (o comando da
#: questao todo em negrito), e nao o destaque que a pergunta pede.
_NEGRITO_DO_CAMPO_INTEIRO = 0.8

_ANO_NO_FIM = re.compile(r"\s+(19|20)\d{2}$")


def caminho_padrao() -> Path:
    return config.RAIZ / "vltool" / "questoes" / "questoes.db"


def e_do_qconcursos(prova_url: str | None) -> bool:
    return (prova_url or "").startswith(PREFIXO)


@dataclass
class DoScript:
    """Uma questao do banco do script, como ele a gravou."""

    id_fonte: str
    url: str
    materia: str
    banca: str
    orgao: str
    prova: str
    ano: int | None
    enunciado: str
    enunciado_html: str
    #: [{"letra": "A", "texto": ..., "html": ...}]
    alternativas: list[dict]
    gabarito: str
    observacao: str = ""
    #: Os assuntos do site de onde ela saiu ("3:16260"), pelos links das
    #: faixas do cronograma (a tabela `questoes_assuntos` do script).
    assuntos: list[str] = field(default_factory=list)
    #: O gabarito que o Claude Code buscou, na questao sem o do site.
    buscado: GabaritoBuscado | None = None

    @property
    def grupo(self) -> str:
        if not self.gabarito.strip():
            return SEM
        if _sem_acento(self.observacao).startswith(OBSERVACAO_PROVAVEL):
            return PROVAVEL
        return DO_SITE

    @property
    def resposta(self) -> str:
        """A letra que o radar grava: a do site, ou a que o Claude Code buscou."""
        return (self.buscado.resposta if self.buscado else self.gabarito).strip().lower()


@dataclass
class GabaritoBuscado:
    """O gabarito que o Claude Code achou para uma questao sem o do site."""

    resposta: str
    #: lei | internet | conhecimento (`COMO`).
    como: str
    #: O que sustenta a letra: o artigo, o titulo da pagina, o porque.
    fonte: str
    procedencia: str
    #: A pagina em que o gabarito DESTA questao aparece (o gabarito oficial,
    #: um site que a comenta). O link da lei nao conta: a lei sustenta o
    #: raciocinio, e nao diz qual letra a banca deu.
    link: str | None = None
    #: A letra que a IA do script tinha dado, para comparar.
    palpite_do_script: str | None = None
    #: "AAAA-MM-DD" do dia em que o Gabriel conferiu; vazio enquanto nao.
    conferido_em: str | None = None

    def nota(self) -> str:
        """De onde veio, como a tela escreve."""
        return f"{self.procedencia}, {COMO[self.como]}: {self.fonte}"


def _sem_acento(texto: str | None) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in texto if not unicodedata.combining(c)).lower().strip()


def ler(caminho: Path | None = None) -> list[DoScript]:
    """Todas as questoes do banco do script, na ordem em que entraram. So le:
    o banco abre em modo de leitura, e o script continua dono dele."""
    caminho = Path(caminho or caminho_padrao())
    if not caminho.exists():
        raise FileNotFoundError(f"Banco do script não encontrado: {caminho}")
    conexao = sqlite3.connect(f"file:{caminho.as_posix()}?mode=ro", uri=True)
    try:
        assuntos: dict[int, list[str]] = {}
        tabelas = {t for (t,) in conexao.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")}
        if "questoes_assuntos" in tabelas:
            for disciplina, assunto, questao in conexao.execute(
                    "SELECT discipline_id, subject_id, questao_id FROM questoes_assuntos"
                    " ORDER BY questao_id, discipline_id, subject_id"):
                assuntos.setdefault(questao, []).append(f"{disciplina}:{assunto}")
        linhas = conexao.execute(
            "SELECT id, id_fonte, url, materia, banca, orgao, prova, ano, enunciado,"
            " enunciado_html, alternativas_json, gabarito, gabarito_observacao"
            " FROM questoes ORDER BY id").fetchall()
    finally:
        conexao.close()
    return [DoScript(id_fonte=str(l[1]), url=l[2], materia=l[3] or "", banca=l[4] or "",
                     orgao=l[5] or "", prova=l[6] or "", ano=l[7],
                     enunciado=l[8] or "", enunciado_html=l[9] or "",
                     alternativas=json.loads(l[10] or "[]"), gabarito=l[11] or "",
                     observacao=l[12] or "", assuntos=assuntos.get(l[0], []))
            for l in linhas]


def caminho_dos_gabaritos() -> Path:
    return config.diretorio_dados() / "gabaritos_buscados.json"


def carregar_gabaritos(caminho: Path | None = None) -> dict[str, GabaritoBuscado]:
    """{numero Q: o gabarito buscado}. Sem o arquivo, nenhum. Recusa o que
    nao da para auditar: letra fora de a-e, sem procedencia, sem fonte, ou o
    link do Qconcursos e do TEC."""
    caminho = Path(caminho or caminho_dos_gabaritos())
    if not caminho.exists():
        return {}
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    gabaritos = {}
    for numero, item in (dados.get("questoes") or {}).items():
        buscado = GabaritoBuscado(
            resposta=str(item.get("resposta") or "").strip().lower(),
            como=item.get("como") or "", fonte=(item.get("fonte") or "").strip(),
            procedencia=(item.get("procedencia") or "").strip(),
            link=item.get("link") or None,
            palpite_do_script=item.get("palpite_do_script") or None,
            conferido_em=item.get("conferido_em") or None)
        problema = _problema_do_gabarito(buscado)
        if problema:
            raise ValueError(f"{caminho.name}, questão {numero}: {problema}")
        gabaritos[str(numero)] = buscado
    return gabaritos


def _problema_do_gabarito(buscado: GabaritoBuscado) -> str | None:
    if len(buscado.resposta) != 1 or buscado.resposta not in "abcde":
        return f"a letra {buscado.resposta!r} não é de a a e"
    if buscado.como not in COMO:
        return "'como' tem de ser " + ", ".join(COMO)
    if not buscado.fonte or not buscado.procedencia:
        return "falta a fonte ou a procedência (modelo e data)"
    if buscado.link is not None:
        if not buscado.link.startswith(("https://", "http://")):
            return f"o link {buscado.link!r} não é um endereço"
        if any(site in buscado.link for site in _SITES_FORA):
            return "o Qconcursos e o TEC não servem de fonte de gabarito"
    return None


def com_gabarito_buscado(questoes: list[DoScript],
                         gabaritos: dict[str, GabaritoBuscado]) -> list[DoScript]:
    """Liga o gabarito buscado a questao que nao tem o do site. A do site
    fica com o dele: o buscado nunca passa por cima."""
    for q in questoes:
        if q.grupo != DO_SITE and q.id_fonte in gabaritos:
            q.buscado = gabaritos[q.id_fonte]
    return questoes


def banca_do_radar(banca: str) -> str:
    """O nome da banca como o radar escreve. So a AOCP muda: o site a escreve
    em maiusculas, e o resto do radar (o alvo.yml, as provas lidas) como
    "Instituto AOCP"."""
    return "Instituto AOCP" if _sem_acento(banca) == "instituto aocp" else banca


def cargo_do_radar(q: DoScript) -> str:
    """O orgao e o cargo, tirados do nome da prova que o site da: "INSTITUTO
    AOCP - 2019 - PC-ES - Escrivao de Policia 2019" vira "PC-ES - Escrivao de
    Policia". Sem o nome, so o orgao. O cargo e o que vem depois do ano e do
    orgao, e nao o pedaco depois do terceiro hifen: o orgao tambem tem hifen
    ("Camara de Sapucaia - RJ"), e a banca vem abreviada no nome da prova
    ("FAPEC" em vez de "Fundacao FAPEC")."""
    meio = f" - {q.ano} - {q.orgao} - "
    achado = q.prova.find(meio)
    cargo = q.prova[achado + len(meio):] if achado >= 0 else ""
    cargo = _ANO_NO_FIM.sub("", cargo).strip()
    if cargo and q.orgao:
        return f"{q.orgao} - {cargo}"
    return cargo or q.orgao or q.prova


def alternativas_do_radar(q: DoScript) -> dict[str, str]:
    """{"a": texto, ...}: a letra minuscula, como a leitura dos cadernos."""
    return {str(a.get("letra", "")).strip().lower(): (a.get("texto") or "").strip()
            for a in q.alternativas if str(a.get("letra", "")).strip()}


def _tem_imagem(q: DoScript) -> bool:
    htmls = [q.enunciado_html] + [a.get("html") or "" for a in q.alternativas]
    return any("<img" in h.lower() for h in htmls)


def de_texto(q: DoScript) -> bool:
    """A questao de Portugues que cita um texto, um trecho, uma linha."""
    # "Portugues" no site, "Lingua Portuguesa" no radar.
    if "portugu" not in _sem_acento(q.materia):
        return False
    tudo = " ".join([q.enunciado] + [a.get("texto") or "" for a in q.alternativas])
    return bool(_DE_TEXTO.search(tudo))


class _LeitorDeMarcas(HTMLParser):
    """O texto do HTML do site, letra a letra, com o sublinhado e o negrito
    de cada uma. O site marca o destaque com `text-decoration-line:
    underline` (a classe `q-text-decoration-underline`) e `font-weight: bold`;
    `<u>`, `<b>` e `<strong>` valem o mesmo."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.letras: list[tuple[str, frozenset]] = []
        self._abertas: list[tuple[str, frozenset]] = []

    def handle_starttag(self, tag, atributos):
        if tag == "br":
            self._escrever("\n")
            return
        estilo = " ".join(v or "" for k, v in atributos if k in ("style", "class")).lower()
        tipos = set()
        if tag == "u" or "underline" in estilo:
            tipos.add(destaques.SUBLINHADO)
        if tag in ("b", "strong") or "bold" in estilo:
            tipos.add(destaques.NEGRITO)
        self._abertas.append((tag, frozenset(tipos)))

    def handle_endtag(self, tag):
        # O HTML do site nem sempre fecha na ordem: fecha ate achar a aberta.
        for i in range(len(self._abertas) - 1, -1, -1):
            if self._abertas[i][0] == tag:
                del self._abertas[i:]
                break
        if tag in ("p", "div"):
            self._escrever("\n")

    def handle_data(self, dados):
        self._escrever(dados)

    def _escrever(self, texto):
        ativos = frozenset().union(*(tipos for _, tipos in self._abertas))
        self.letras.extend((letra, ativos) for letra in texto)

    def bloco(self) -> destaques.BlocoMarcado:
        texto = "".join(letra for letra, _ in self.letras)
        marcas = []
        for tipo in (destaques.SUBLINHADO, destaques.NEGRITO):
            inicio = None
            for i, (letra, tipos) in enumerate(self.letras + [("", frozenset())]):
                if tipo in tipos and inicio is None:
                    inicio = i
                elif tipo not in tipos and inicio is not None:
                    trecho = texto[inicio:i]
                    # Sem o espaco das pontas: o trecho e a palavra.
                    de = inicio + len(trecho) - len(trecho.lstrip())
                    ate = i - (len(trecho) - len(trecho.rstrip()))
                    if de < ate:
                        marcas.append((de, ate, tipo))
                    inicio = None
        return destaques.BlocoMarcado(texto=texto, marcas=tuple(marcas))


def destaques_do_html(q: DoScript) -> list[dict]:
    """O sublinhado e o negrito do site, no formato do `questoes.destaques`
    (decisao 178): o trecho e achado no texto que o radar grava pelo texto em
    volta (`destaques.localizar`), campo a campo. O negrito de quase o campo
    inteiro fica de fora (`_NEGRITO_DO_CAMPO_INTEIRO`)."""
    campos = [(destaques.ENUNCIADO, q.enunciado_html, q.enunciado)]
    campos += [(str(a.get("letra", "")).strip().lower(), a.get("html") or "",
                (a.get("texto") or "").strip()) for a in q.alternativas]
    marcas: list[dict] = []
    for campo, html, texto in campos:
        if not html or not texto:
            continue
        leitor = _LeitorDeMarcas()
        leitor.feed(html)
        leitor.close()
        bloco = leitor.bloco()
        if not bloco.marcas:
            continue
        achadas = destaques.localizar([bloco], {0: {campo: texto}}).get(0, [])
        cheio = len(texto.strip()) * _NEGRITO_DO_CAMPO_INTEIRO
        marcas += [m for m in achadas
                   if m["tipo"] != destaques.NEGRITO or m["fim"] - m["inicio"] < cheio]
    return destaques.juntar(marcas)


def pede_destaque(q: DoScript) -> bool:
    """A questao de Portugues que pede o trecho marcado. No Direito a palavra
    aparece sem depender da marca ("destacada vida publica", "o termo
    destacado" entre aspas)."""
    if "portugu" not in _sem_acento(q.materia):
        return False
    tudo = " ".join([q.enunciado] + [a.get("texto") or "" for a in q.alternativas])
    return bool(_PEDE_DESTAQUE.search(tudo))


def motivo_de_fora(q: DoScript, ja_no_radar: set[str],
                   grupos: tuple[str, ...] = (DO_SITE,)) -> str | None:
    """Por que a questao fica fora, ou None quando ela entra. A ordem dos
    testes e a da explicacao: o gabarito primeiro, porque e ele que decide a
    etapa."""
    if q.grupo not in grupos and q.buscado is None:
        return GABARITO_NAO_CONFIRMADO
    alternativas = alternativas_do_radar(q)
    if len(alternativas) < 4:
        return CERTO_ERRADO
    if _sem_acento(q.banca) == "qconcursos":
        return AUTORIA_DO_SITE
    if _tem_imagem(q):
        return IMAGEM
    if de_texto(q):
        return PORTUGUES_DE_TEXTO
    if pede_destaque(q) and not destaques_do_html(q):
        return DESTAQUE_PERDIDO
    if q.resposta not in alternativas:
        return GABARITO_FORA
    if mesma_questao(q.enunciado, alternativas) in ja_no_radar:
        return JA_NO_RADAR
    return None


def mesma_questao(enunciado: str, alternativas: dict) -> str:
    """A identidade de `outras_bancas.mesma_questao`, que ja acha a mesma
    questao em cadernos diferentes: o texto sem espaco e sem acento, as
    alternativas sem a letra e em ordem."""
    from radar.servico.outras_bancas import mesma_questao as identidade

    return identidade(SimpleNamespace(enunciado=enunciado, alternativas=alternativas))


def _ja_no_radar() -> set[str]:
    """As questoes do radar que NAO vieram do script: e o caderno oficial que
    fica quando as duas sao a mesma."""
    criar_tabelas()
    with sessao() as s:
        return {mesma_questao(q.enunciado, q.alternativas or {})
                for q in s.scalars(select(QuestaoDeProva))
                if not e_do_qconcursos(q.prova_url)}


@dataclass
class Triagem:
    entram: list[DoScript] = field(default_factory=list)
    #: [(questao, motivo)]
    fora: list[tuple[DoScript, str]] = field(default_factory=list)

    def motivos(self) -> Counter:
        return Counter(motivo for _, motivo in self.fora)


def triar(questoes: list[DoScript], ja_no_radar: set[str],
          grupos: tuple[str, ...] = (DO_SITE,)) -> Triagem:
    triagem = Triagem()
    for q in questoes:
        motivo = motivo_de_fora(q, ja_no_radar, grupos)
        if motivo is None:
            triagem.entram.append(q)
        else:
            triagem.fora.append((q, motivo))
    return triagem


def gravar(questoes: list[DoScript]) -> tuple[int, int]:
    """Grava (ou atualiza) as questoes no banco do radar. Devolve (novas,
    atualizadas). Rodar de novo nao duplica: a questao e reconhecida pelo
    link e pelo numero Q, a mesma regra de unicidade dos cadernos."""
    criar_tabelas()
    novas = atualizadas = 0
    with sessao() as s:
        existentes = {(q.prova_url, q.numero): q for q in s.scalars(
            select(QuestaoDeProva).where(QuestaoDeProva.prova_url.startswith(PREFIXO)))}
        for q in questoes:
            numero = int(q.id_fonte)
            linha = existentes.get((q.url, numero))
            if linha is None:
                linha = QuestaoDeProva(prova_url=q.url, numero=numero)
                s.add(linha)
                novas += 1
            else:
                atualizadas += 1
            linha.concurso_url = None
            linha.banca = banca_do_radar(q.banca)
            linha.ano = q.ano
            linha.cargo = cargo_do_radar(q)
            linha.materia = q.materia
            linha.enunciado = q.enunciado
            linha.alternativas = alternativas_do_radar(q)
            linha.resposta = q.resposta
            # O gabarito buscado e nao conferido leva o "verificar a questao";
            # o conferido, e o do site, nao.
            a_conferir = q.buscado is not None and not q.buscado.conferido_em
            linha.gabarito_a_conferir = q.buscado.nota() if a_conferir else None
            linha.gabarito_link = q.buscado.link if q.buscado else None
            # O sublinhado e o negrito do site (decisao 178): "o termo
            # destacado" so se responde vendo o termo.
            linha.destaques = destaques_do_html(q) or None
            linha.anulada = False
            linha.impressao = impressao_de(q.enunciado)
    # A evidencia sai da regra unica, como depois de ler um caderno: a da AOCP
    # vira complementar, o resto fora.
    evidencia.atualizar()
    return novas, atualizadas


def importar(caminho: Path | None = None, aplicar: bool = False,
             gabaritos: Path | None = None) -> Triagem:
    """A triagem do banco do script e, com `aplicar`, a gravacao das que
    entram: as do gabarito do site e as do gabarito buscado. Sem `aplicar`
    nada muda no radar."""
    questoes = com_gabarito_buscado(ler(caminho), carregar_gabaritos(gabaritos))
    triagem = triar(questoes, _ja_no_radar())
    if aplicar:
        gravar(triagem.entram)
    return triagem


@cache.por_requisicao
def provas_aceitas() -> set[str]:
    """As questoes do script que sao da banca do alvo (complementar). Cada
    uma e a sua propria "prova" (o link dela), e todas entram no acervo:
    o gabarito e o do site, e a validacao do caderno (numeracao, sha256) nao
    se aplica a quem nao veio de caderno."""
    criar_tabelas()
    with sessao() as s:
        return set(s.scalars(
            select(QuestaoDeProva.prova_url)
            .where(QuestaoDeProva.prova_url.startswith(PREFIXO))
            .where(QuestaoDeProva.evidencia == evidencia.COMPLEMENTAR)))


def nome_da_prova(banca: str | None, ano: int | None, cargo: str | None) -> str:
    """A prova de onde a questao veio, para contar provas DISTINTAS nos padroes
    da banca: duas questoes do mesmo concurso sao uma prova so, e nao duas."""
    return f"{banca or 'sem banca'} {ano or 's/a'} {cargo or ''}".strip()


# --- a classificacao: o no vem do link da faixa ----------------------------------
#
# Cada questao saiu do link de uma faixa do cronograma, e o link e um assunto
# do site (o Qconcursos ja a classificou). A regra da 171 pede duas leituras de
# cada questao; para 4 mil, o Gabriel aprovou em 02/11 outra: a primeira
# leitura e o MAPA do assunto do site para o no da arvore, e a segunda, as
# cegas, le so uma AMOSTRA de cada assunto. O assunto cuja amostra bate passa
# inteiro (conferido); o contradito vira pendente (nao treina); o que a amostra
# nao confirmou nem contradisse fica com o no do mapa, sem conferencia.

#: Quem conferiu a questao do assunto que passou na amostra.
CONFERIDA_PELA_AMOSTRA = "Claude Code, amostra às cegas do assunto do site (PMSC-26)"

#: O veredito da amostra de um assunto do site.
PASSOU, CONTRADITO, SEM_CONFIRMACAO = "passou", "contradito", "sem confirmação"


def caminho_do_mapa() -> Path:
    return config.diretorio_config() / "qconcursos_nos.yml"


@dataclass
class AssuntoDoSite:
    """Um assunto do site no mapa: o no dele e o que a amostra disse."""

    no: str | None
    amostra: str = SEM_CONFIRMACAO
    #: A do lote em que o assunto entrou no mapa, quando nao e a do arquivo.
    procedencia: str | None = None


#: Quem conferiu a questao da propria amostra: lida duas vezes, as duas no
#: mesmo no (ou no no em comum, ou desempatada a favor da leitura as cegas).
CONFERIDA_NA_AMOSTRA = "Claude Code, reanálise às cegas da amostra (PMSC-26)"


@dataclass
class DaAmostra:
    """A questao da amostra que nao segue o no do assunto: o no em comum das
    duas leituras, o da leitura as cegas que o desempate confirmou, ou
    nenhum (pendente)."""

    no: str | None
    conferida: bool = True
    procedencia: str | None = None


@dataclass
class Mapa:
    #: A do arquivo: a do primeiro lote. O assunto ou a questao de um lote
    #: seguinte tem a sua, e o lote antigo nao e regravado com a data nova.
    procedencia: str
    assuntos: dict[str, AssuntoDoSite]
    #: {numero Q: DaAmostra}.
    questoes: dict[str, DaAmostra] = field(default_factory=dict)

    def procedencia_de(self, q: "DoScript") -> str:
        """A da questao da amostra; senao a do primeiro assunto dela que tem
        a sua (o lote mais novo que a leu); senao a do arquivo."""
        da_amostra = self.questoes.get(q.id_fonte)
        if da_amostra and da_amostra.procedencia:
            return da_amostra.procedencia
        for a in q.assuntos:
            item = self.assuntos.get(a)
            if item and item.procedencia:
                return item.procedencia
        return self.procedencia


def carregar_mapa(caminho: Path | None = None) -> Mapa:
    import yaml

    # A chave do no no arquivo e `caminho`: no YAML, `no` vira o booleano falso.
    dados = yaml.safe_load(Path(caminho or caminho_do_mapa()).read_text(encoding="utf-8")) or {}
    assuntos = {str(chave): AssuntoDoSite(no=item.get("caminho"),
                                          amostra=item.get("amostra") or SEM_CONFIRMACAO,
                                          procedencia=item.get("procedencia"))
                for chave, item in (dados.get("assuntos") or {}).items()}
    questoes = {str(numero): DaAmostra(no=item.get("caminho"),
                                       conferida=bool(item.get("conferida", True)),
                                       procedencia=item.get("procedencia"))
                for numero, item in (dados.get("questoes") or {}).items()}
    return Mapa(procedencia=dados["procedencia"], assuntos=assuntos, questoes=questoes)


def no_pelo_link(q: DoScript, mapa: Mapa) -> str | None:
    """O no dos assuntos de onde a questao saiu. A que saiu de dois assuntos
    vai para o no que os dois tem em comum, nunca acima do assunto; sem no em
    comum, nenhum (pendente)."""
    from radar.servico.classificacoes import no_em_comum

    nos = sorted({mapa.assuntos[a].no for a in q.assuntos
                  if a in mapa.assuntos and mapa.assuntos[a].no})
    if not nos:
        return None
    no = nos[0]
    for outro in nos[1:]:
        no = no_em_comum(no, outro)
        if no is None:
            return None
    return no


def veredito(q: DoScript, mapa: Mapa) -> str:
    """O pior veredito entre os assuntos da questao: um assunto contradito
    basta para ela nao valer sem conferencia."""
    vereditos = {mapa.assuntos[a].amostra for a in q.assuntos
                 if a in mapa.assuntos and mapa.assuntos[a].no}
    for pior in (CONTRADITO, SEM_CONFIRMACAO, PASSOU):
        if pior in vereditos:
            return pior
    return SEM_CONFIRMACAO


@dataclass
class Leitura:
    """A classificacao que a questao recebe."""

    chave: str
    #: O no; na pendente, a materia (o mais fundo que se sabe).
    conteudo: str
    pendente: bool
    conferida_por: str | None


def ler_pelo_link(q: DoScript, mapa: Mapa) -> Leitura | None:
    """A classificacao da questao pelo mapa. None quando nem a materia se
    sabe - a questao fica sem linha, como o bloco generico."""
    from radar import conteudos as arvore
    from radar.questoes import chave_da_questao

    chave = chave_da_questao(q.enunciado, alternativas_do_radar(q))
    if q.id_fonte in mapa.questoes:
        da_amostra = mapa.questoes[q.id_fonte]
        # Materia sozinha nao e classificacao: e pendente, sem conferencia.
        if da_amostra.no is None or arvore.SEPARADOR not in da_amostra.no:
            materia = _materia_da_questao(q, mapa)
            return None if materia is None else Leitura(
                chave=chave, conteudo=materia, pendente=True, conferida_por=None)
        return Leitura(chave=chave, conteudo=da_amostra.no, pendente=False,
                       conferida_por=CONFERIDA_NA_AMOSTRA if da_amostra.conferida else None)
    no = no_pelo_link(q, mapa)
    julgado = veredito(q, mapa)
    if no is None or julgado == CONTRADITO or arvore.SEPARADOR not in no:
        materia = _materia_da_questao(q, mapa)
        if materia is None:
            return None
        return Leitura(chave=chave, conteudo=materia, pendente=True, conferida_por=None)
    return Leitura(chave=chave, conteudo=no, pendente=False,
                   conferida_por=CONFERIDA_PELA_AMOSTRA if julgado == PASSOU else None)


def _materia_da_questao(q: DoScript, mapa: Mapa) -> str | None:
    """A materia da arvore em que a pendente espera: a do no de um dos
    assuntos dela, ou a do site quando ela e tambem uma materia da arvore."""
    from radar import conteudos as arvore

    for a in q.assuntos:
        item = mapa.assuntos.get(a)
        if item and item.no:
            return arvore.partes(item.no)[0]
    criar_tabelas()
    from radar.models import Conteudo
    with sessao() as s:
        existe = s.scalar(select(Conteudo.caminho).where(Conteudo.caminho == q.materia))
    return existe


def classificar_pelo_link(questoes: list[DoScript], mapa: Mapa) -> Counter:
    """Grava a classificacao principal de cada questao, com a procedencia do
    mapa. Nao toca a questao ja conferida pelo Gabriel nem a que saiu do
    treino (o passo 2 da 171: a lei mudou depois da prova). Devolve quantas
    ficaram conferidas, sem conferencia, pendentes e sem linha."""
    from radar.models import Classificacao
    from radar.servico import classificacoes

    criar_tabelas()
    with sessao() as s:
        principais = list(s.scalars(
            select(Classificacao).where(Classificacao.principal.is_(True))))
    por_mim = {c.chave for c in principais
               if c.conferida_em is not None and c.conferida_por is None}
    fora = {c.chave for c in principais
            if c.status == classificacoes.PENDENTE and "fora do treino" in (c.trecho or "")}
    atuais = {c.chave: c for c in principais}
    contagem: Counter = Counter()
    agora = _agora()
    for q in questoes:
        leitura = ler_pelo_link(q, mapa)
        if leitura is None:
            contagem["sem linha"] += 1
            continue
        if leitura.chave in por_mim:
            contagem["conferida pelo Gabriel"] += 1
            continue
        if leitura.chave in fora:
            contagem["fora do treino"] += 1
            continue
        procedencia = mapa.procedencia_de(q)
        categoria = ("pendente" if leitura.pendente
                     else "conferida" if leitura.conferida_por else "sem conferência")
        atual = atuais.get(leitura.chave)
        # A que ja esta assim fica como esta: gravar de novo so trocaria as
        # datas, e o data/classificacoes.json mudaria inteiro a cada rodada.
        if (atual is not None and atual.conteudo == leitura.conteudo
                and atual.procedencia == procedencia
                and (atual.status == classificacoes.PENDENTE) == leitura.pendente
                and atual.conferida_por == leitura.conferida_por):
            contagem[categoria] += 1
            continue
        classificacoes.classificar(
            leitura.chave, leitura.conteudo, procedencia,
            status=classificacoes.PENDENTE if leitura.pendente else None,
            trecho="o assunto do site de onde a questão saiu (o link da faixa)",
            conferida_em=agora if leitura.conferida_por else None,
            conferida_por=leitura.conferida_por)
        contagem[categoria] += 1
    return contagem


def _agora():
    from radar.models import agora

    return agora()

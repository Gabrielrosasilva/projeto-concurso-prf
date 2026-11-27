"""A explicacao depois da resposta (PRF-31): o painel de cada questao real.

O painel junta o que o radar ja sabe da questao, cada parte com a origem
dela:

  - o gabarito, por extenso ("o item esta CERTO"): e da banca;
  - o no da arvore, o item do edital, o dispositivo e a pegadinha: da
    classificacao, que duas leituras de IA fizeram (PRF-19);
  - a explicacao: texto de IA importado pelo caminho sem API
    (`radar gerar --pedido --explicacoes`), com o modelo e a data. No Certo/
    Errado ela vem em partes: o veredito, o que a questao cobra, o
    dispositivo e o TRECHO da lei, a pegadinha e, no item errado, como ele
    ficaria certo;
  - o link da lei e o aviso da lei que mudou: do `config/leis.yml`.

O trecho da lei so aparece se for achado, palavra por palavra, no texto
oficial guardado no projeto (`trecho_na_lei`): a IA copia, o radar confere.
Sem achar, o trecho sai e fica o dispositivo com o link - lei inventada e
pior que lei nenhuma (regras 2 e 3 do CLAUDE.md).

A explicacao e achada pela CHAVE da questao (enunciado + alternativas). As
antigas, da PMSC, so tinham a impressao do enunciado: valem pela impressao.
"""
import html
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from functools import cache
from pathlib import Path

from sqlalchemy import select

from radar import config, leis
from radar.db import criar_tabelas, sessao
from radar.models import Classificacao
from radar.origem import IA, OFICIAL
from radar.questoes_certo_errado import e_certo_errado
from radar.util import fuso_local

#: O gabarito do Certo/Errado por extenso, como o painel o diz.
POR_EXTENSO = {"c": "CERTO", "e": "ERRADO"}

#: Status da classificacao que ainda espera a conferencia (servico.classificacoes).
PENDENTE = "pendente"


@dataclass
class Explicacao:
    """A explicacao de uma questao, como o arquivo a guarda.

    `veredito` e o texto principal: na explicacao antiga (um paragrafo so),
    e o paragrafo inteiro; as outras partes ficam vazias."""

    correta: str
    veredito: str
    fonte: str
    modelo: str
    criado_em: str
    chave: str | None = None
    impressao: str | None = None
    o_que_cobra: str | None = None
    dispositivo: str | None = None
    #: O trecho literal da lei, ja conferido no texto oficial do projeto; e
    #: o arquivo onde foi achado.
    trecho_da_lei: str | None = None
    lei_do_trecho: str | None = None
    pegadinha: str | None = None
    #: So no item ERRADO: o item reescrito do jeito certo.
    como_ficaria_certo: str | None = None
    origem: str = IA

    @property
    def em_partes(self) -> bool:
        """A explicacao nova (PRF-31), e nao o paragrafo antigo."""
        return bool(self.o_que_cobra or self.pegadinha or self.como_ficaria_certo
                    or self.trecho_da_lei)

    @property
    def procedencia(self) -> str:
        """Quem escreveu e quando, para o rodape. A procedencia do caminho sem
        API ja traz a data ("... importado manualmente, em 25/11/2026"); a que
        nao traz ganha a do arquivo - a de Brasilia, e nao a do UTC gravado
        (a meia-noite UTC ainda e o dia anterior aqui)."""
        if re.search(r"\d{2}/\d{2}/\d{4}", self.modelo or ""):
            return self.modelo
        try:
            quando = datetime.fromisoformat(self.criado_em)
            if quando.tzinfo is not None:
                quando = quando.astimezone(fuso_local())
            return f"{self.modelo} · {quando:%d/%m/%Y}"
        except (TypeError, ValueError):
            return self.modelo


def _caminho() -> Path:
    return config.diretorio_dados() / "explicacoes.json"


def carregar(caminho: Path | None = None) -> tuple[dict[str, Explicacao], dict[str, Explicacao]]:
    """({chave: explicacao}, {impressao: explicacao}) - so as que dizem a
    fonte, o modelo e a data. O arquivo e editavel a mao, e a tela nao confia
    nele: explicacao sem procedencia nao aparece, como o macete."""
    origem = caminho or _caminho()
    if not origem.exists():
        return {}, {}
    por_chave, por_impressao = {}, {}
    for e in json.loads(origem.read_text(encoding="utf-8")) or []:
        texto = (e.get("veredito") or e.get("explicacao") or "").strip()
        if not (texto and (e.get("fonte") or "").strip() and (e.get("modelo") or "").strip()
                and e.get("criado_em")):
            continue
        explicacao = Explicacao(
            correta=e.get("correta") or "", veredito=texto, fonte=e["fonte"],
            modelo=e["modelo"], criado_em=e["criado_em"], chave=e.get("chave"),
            impressao=e.get("impressao"), o_que_cobra=e.get("o_que_cobra") or None,
            dispositivo=e.get("dispositivo") or None,
            trecho_da_lei=e.get("trecho_da_lei") or None,
            lei_do_trecho=e.get("lei_do_trecho") or None,
            pegadinha=e.get("pegadinha") or None,
            como_ficaria_certo=e.get("como_ficaria_certo") or None)
        if explicacao.chave:
            por_chave[explicacao.chave] = explicacao
        elif explicacao.impressao:
            por_impressao[explicacao.impressao] = explicacao
    return por_chave, por_impressao


def da_questao(questao, explicacoes=None) -> Explicacao | None:
    """A explicacao desta questao: pela chave e, nas antigas, pela impressao."""
    from radar.servico.classificacoes import chave_de

    por_chave, por_impressao = explicacoes if explicacoes is not None else carregar()
    return (por_chave.get(chave_de(questao))
            or por_impressao.get(getattr(questao, "impressao", None)))


# --- o trecho da lei, conferido no texto oficial -----------------------------

def pastas_das_leis() -> list[Path]:
    """Onde o projeto guarda o texto oficial das leis: `leis/` (regra 3 do
    CLAUDE.md) e a copia que veio da PMSC em `fontes/leis/` (so leitura)."""
    return [config.RAIZ / "leis", config.RAIZ / "fontes" / "leis"]


def _normalizar(texto: str) -> str:
    """Sem marcacao, sem aspas curvas e com um espaco so: o trecho copiado e
    o texto da Camara precisam se encontrar mesmo com a quebra de linha."""
    texto = html.unescape(re.sub(r"<[^>]+>", " ", texto))
    texto = texto.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", texto).strip().casefold()


@cache
def _textos_das_leis(pastas: tuple[Path, ...]) -> tuple[tuple[str, str], ...]:
    """(nome do arquivo, texto normalizado) de cada lei em HTML das pastas."""
    textos = []
    for pasta in pastas:
        if pasta.exists():
            for arquivo in sorted(pasta.rglob("*.htm*")):
                bruto = arquivo.read_text(encoding="utf-8", errors="ignore")
                textos.append((arquivo.name, _normalizar(bruto)))
    return tuple(textos)


#: O trecho curto demais acha qualquer coisa ("da pena"): nao confere nada.
TRECHO_MINIMO = 25


def trecho_na_lei(trecho: str | None) -> str | None:
    """O arquivo da lei em que o trecho esta, palavra por palavra; None se
    nao esta em nenhuma (ou e curto demais para provar alguma coisa)."""
    procurado = _normalizar(trecho or "").strip(' "')
    if len(procurado) < TRECHO_MINIMO:
        return None
    for nome, texto in _textos_das_leis(tuple(pastas_das_leis())):
        if procurado in texto:
            return nome
    return None


# --- o painel -----------------------------------------------------------------

@dataclass
class Painel:
    """O que a tela mostra depois da resposta. Todas as contas aqui; o
    template so desenha (CLAUDE.md, metricas)."""

    certo_errado: bool
    #: "CERTO"/"ERRADO" no Certo/Errado; a letra na multipla escolha.
    gabarito: str | None
    #: De onde vem o gabarito: o definitivo da banca, ou o que o Claude Code
    #: buscou e ninguem conferiu (decisao PMSC-27) - este leva o 🟣.
    origem_do_gabarito: str = OFICIAL
    explicacao: Explicacao | None = None
    #: Da classificacao principal (IA, duas leituras): o no, o item do
    #: edital, o dispositivo e a pegadinha. A pendente so mostra o no.
    no: str | None = None
    no_pendente: bool = False
    item_do_edital: str | None = None
    dispositivo: str | None = None
    pegadinha: str | None = None
    lei: leis.Lei | None = None
    mudancas: list = field(default_factory=list)
    #: A questao escrita por IA (PRF-48): o mesmo painel, mas o gabarito, o
    #: no e o artigo sao os que a IA deu - nada conferido pela banca.
    gerada: bool = False

    @property
    def caminho_do_no(self) -> list[str]:
        """O no em partes, sem a materia: "Assunto > Subassunto"."""
        return (self.no or "").split(" > ")[1:]

    @property
    def caminho_curto(self) -> list[str]:
        """Os dois ultimos niveis do no: o assunto do CTB, sozinho, ja ocupa
        duas linhas ("Lei nº 9.503/1997 ... e suas alteracoes, inclusive...")."""
        return self.caminho_do_no[-2:]

    @property
    def dispositivo_a_mostrar(self) -> str | None:
        """O da explicacao, quando ha; senao o da classificacao."""
        if self.explicacao and self.explicacao.dispositivo:
            return self.explicacao.dispositivo
        return self.dispositivo

    @property
    def pegadinha_a_mostrar(self) -> str | None:
        if self.explicacao and self.explicacao.pegadinha:
            return self.explicacao.pegadinha
        return self.pegadinha


def painel(questao, explicacoes=None) -> Painel:
    """O painel de uma questao REAL (a gerada tem o artigo dela, e nao entra)."""
    from radar.servico.classificacoes import chave_de

    alternativas = getattr(questao, "alternativas", None) or {}
    ce = e_certo_errado(alternativas)
    letra = (questao.resposta or "").lower()
    gabarito = POR_EXTENSO.get(letra) if ce else (letra or None)
    criar_tabelas()
    with sessao() as s:
        linha = s.scalar(select(Classificacao)
                         .where(Classificacao.chave == chave_de(questao))
                         .where(Classificacao.principal.is_(True)))
        classificacao = None if linha is None else {
            "no": linha.conteudo, "pendente": linha.status == PENDENTE,
            "item_do_edital": linha.item_do_edital, "dispositivo": linha.dispositivo,
            "pegadinha": linha.pegadinha}
    p = Painel(certo_errado=ce, gabarito=gabarito,
               origem_do_gabarito=IA if getattr(questao, "gabarito_a_conferir", None) else OFICIAL,
               explicacao=da_questao(questao, explicacoes),
               lei=leis.da_materia(questao.materia),
               mudancas=leis.mudancas_da_questao(
                   questao.ano, questao.materia,
                   " ".join([questao.enunciado or ""] + list(alternativas.values())),
                   getattr(questao, "prova_url", None)))
    if classificacao:
        p.no, p.no_pendente = classificacao["no"], classificacao["pendente"]
        if not p.no_pendente:
            p.item_do_edital = (classificacao["item_do_edital"] or "").strip() or None
            p.dispositivo = (classificacao["dispositivo"] or "").strip() or None
            p.pegadinha = (classificacao["pegadinha"] or "").strip() or None
    return p


def painel_da_gerada(questao) -> Painel:
    """O painel de uma questao GERADA (PRF-48), no mesmo desenho do da real.

    A gerada nao tem classificacao nem explicacao em partes: o que ela tem e o
    no em que a IA a escreveu, o artigo em que diz se apoiar e o "por que"
    que a IA escreveu junto (PRF-40). Tudo leva o selo da IA - o gabarito
    tambem, porque nenhuma banca o conferiu (regra 1 do CLAUDE.md)."""
    alternativas = getattr(questao, "alternativas", None) or {}
    ce = e_certo_errado(alternativas)
    letra = (questao.resposta or "").lower()
    texto = (getattr(questao, "explicacao", None) or "").strip()
    artigo = (getattr(questao, "artigo", None) or "").strip() or None
    explicacao = None
    if texto:
        criada = getattr(questao, "criada_em", None)
        explicacao = Explicacao(
            correta=letra, veredito=texto, fonte=artigo or "não citada",
            modelo=questao.modelo or "modelo não registrado",
            criado_em=criada.isoformat() if hasattr(criada, "isoformat") else str(criada or ""),
            # As partes que a gerada nova traz (PRF-51); a de antes, nao.
            pegadinha=(getattr(questao, "pegadinha", None) or "").strip() or None,
            como_ficaria_certo=(getattr(questao, "como_ficaria_certo", None) or "").strip()
            or None)
    return Painel(
        certo_errado=ce, gabarito=POR_EXTENSO.get(letra) if ce else (letra or None),
        origem_do_gabarito=IA, explicacao=explicacao,
        no=getattr(questao, "conteudo", None) or None, dispositivo=artigo,
        lei=leis.do_assunto(questao.materia, getattr(questao, "assunto", None)),
        gerada=True)

"""A redacao: as regras do edital, o tema da vez e a NOTA. Puro.

O texto da aba mora no `redacao.yml` da pasta de config (na PRF,
`PRF/config/redacao.yml`), como o `linguagem.yml`: este arquivo le, acha o
tema da vez, confere a FORMA do que a IA devolve e faz a conta da nota. A
conta da IA nao vale: ela da os conceitos (ou a nota de conteudo) e lista os
erros; quem soma e o radar.

A formula sai do `regras_do_edital` do redacao.yml:

  * NOTA = NC - fator x (NE / TL), e o que der negativo vira 0. O fator e 4
    no Cebraspe (PRF 2021, edital 10.6.4: NPD = NC - 4 x NE / TL) e 1 na AOCP
    da PMSC (NPR = NC - NE / TL), o padrao quando o arquivo nao diz;
  * menos 0,20 de cada linha que faltar para o `linhas_minimo` (so a AOCP
    tem minimo, 20; com 0, nao ha desconto);
  * o que passar do maximo de linhas e desconsiderado: o TL conta, no maximo,
    o `linhas_maximo`.

Com `conceito_maximo` (o Cebraspe), a nota de conteudo nao vem pronta: a
correcao da o conceito de cada quesito (0 a 3) e o radar converte (PRF-37).

Nao fala com banco nem com rede.
"""
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import yaml

from radar import cache, config

#: O desconto de cada linha que falta para o minimo (edital, 11.5, g).
DESCONTO_POR_LINHA = 0.20

#: Os titulos de faixa que trazem o tema depois dos dois-pontos. A
#: "Redacao 1: o que a AOCP cobra..." e aula, e nao tema: nao entra.
PREFIXOS_DE_TEMA = ("Redação da semana:", "Redação do simulado:")

#: A materia das faixas de redacao no cronograma.
MATERIA = "Redação"


class RespostaInvalida(ValueError):
    """O que a IA devolveu nao tem a forma pedida. A mensagem diz o que falta."""


def caminho() -> Path:
    return config.diretorio_config() / "redacao.yml"


def _ler(arquivo: Path) -> dict:
    return yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}


def carregar() -> dict:
    """O redacao.yml, ou {} quando nao ha. A tela diz o que falta."""
    arquivo = caminho()
    if not arquivo.exists():
        return {}
    return cache.do_arquivo(arquivo, lambda: _ler(arquivo), nome="redacao")


# --- a nota -----------------------------------------------------------------

@dataclass
class Nota:
    """A conta do edital, passo a passo, para a tela mostrar de onde veio."""

    nc: float
    ne: int
    linhas: int                 # as que eu contei na folha
    tl: int                     # as que contam: no maximo o limite
    bruta: float                # NC - NE/TL, sem ficar negativa
    linhas_faltando: int
    desconto: float             # 0,20 por linha que falta
    final: float
    minima: float
    acima_do_maximo: bool       # escrevi mais que o limite: o resto nao conta
    zerada: str | None = None   # o motivo, quando a redacao leva zero
    #: Quanto pesa cada erro na conta: 4 no Cebraspe, 1 na AOCP.
    fator: float = 1.0

    @property
    def aprovada(self) -> bool:
        return self.final >= self.minima


def nota(nc: float, ne: int, linhas: int, regras: dict | None = None,
         motivo_zero: str | None = None) -> Nota:
    """A nota da prova de redacao pela formula do edital.

    `nc` e a nota de conteudo (0 a 20), `ne` o numero de erros que a correcao
    listou e `linhas` as que eu contei na folha. Com `motivo_zero`, a final e
    0 - e a conta continua na tela, para eu ver quanto seria.
    """
    regras = regras or {}
    minimo = int(regras.get("linhas_minimo", 20))
    maximo = int(regras.get("linhas_maximo", 30))
    nota_maxima = float(regras.get("nota_maxima", 20))
    minima = float(regras.get("nota_minima", 10))
    fator = float(regras.get("fator_dos_erros", 1))

    nc = max(0.0, min(float(nc), nota_maxima))
    ne = max(0, int(ne))
    linhas = max(0, int(linhas))
    tl = min(linhas, maximo)

    bruta = max(0.0, nc - fator * ne / tl) if tl else 0.0
    faltando = max(0, minimo - tl)
    desconto = round(DESCONTO_POR_LINHA * faltando, 2)
    final = round(max(0.0, bruta - desconto), 2)
    if motivo_zero:
        final = 0.0
    return Nota(nc=nc, ne=ne, linhas=linhas, tl=tl, bruta=round(bruta, 2),
                linhas_faltando=faltando, desconto=desconto, final=final,
                minima=minima, acima_do_maximo=linhas > maximo,
                zerada=motivo_zero or None, fator=fator)


def nc_pelos_conceitos(conceitos: list[float], regras: dict) -> float:
    """A nota de conteudo a partir dos conceitos dos quesitos (Cebraspe).

    O padrao de resposta da banca da a escala de cada quesito (0 a 3), mas nao
    quanto ele vale nos 20 pontos, e o edital (10.6.4, a) poe na NC tambem a
    apresentacao e a estrutura, sem dizer o peso. Entao e uma ESTIMATIVA, e a
    tela diz: os quesitos valem igual, NC = maxima x soma / (conceito maximo x
    quantos quesitos), e a apresentacao entra nos comentarios, sem nota.
    """
    if not conceitos:
        return 0.0
    maximo = float(regras.get("conceito_maximo", 3))
    nota_maxima = float(regras.get("nota_maxima", 20))
    return round(nota_maxima * sum(conceitos) / (maximo * len(conceitos)), 2)


# --- o tema da vez ----------------------------------------------------------

@dataclass
class TemaDaVez:
    tema: str
    data: date | None
    origem: str                 # de onde veio, para eu conferir
    #: Os textos motivadores do tema, como a AOCP os da antes da proposta
    #: (edital, 11.2): trechos de lei ou de noticia de fonte oficial, cada um
    #: com a fonte (decisoes PMSC-22 e PMSC-23).
    textos: list = field(default_factory=list)
    #: O comando da proposta com as palavras da AOCP ("discorra sobre...",
    #: "redija... sobre o tema...", ou a pergunta "A ou B?"), decisao PMSC-23.
    #: Vazio: a tela usa a frase generica.
    comando: str = ""


def _data(valor) -> date | None:
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor))
    except ValueError:
        return None


def _item_do_tema(tema: str, temas: list[dict]) -> dict:
    procurado = " ".join((tema or "").split()).casefold()
    for item in temas or []:
        if " ".join(str(item.get("tema") or "").split()).casefold() == procurado:
            return item
    return {}


def textos_do_tema(tema: str, temas: list[dict]) -> list[dict]:
    """Os textos motivadores do tema na lista `temas`, so os que tem o texto e
    a fonte: sem a fonte, o trecho nao aparece (nada sem procedencia).

    O texto de lei traz `lei` (o dispositivo); o de noticia traz `fonte` (o
    veiculo, a data e o titulo) e `titulo`. A `fonte` de saida e uma so para
    os dois: e o que a tela e o pedido mostram ao lado do trecho.
    """
    textos = []
    for x in _item_do_tema(tema, temas).get("textos") or []:
        if not isinstance(x, dict):
            continue
        texto, url = str(x.get("texto") or "").strip(), str(x.get("url") or "").strip()
        lei = str(x.get("lei") or "").strip()
        fonte = lei or str(x.get("fonte") or "").strip()
        if texto and url and fonte:
            textos.append({"texto": texto, "titulo": str(x.get("titulo") or "").strip(),
                           "tipo": "lei" if lei else "noticia", "fonte": fonte,
                           "url": url, "acesso": str(x.get("acesso") or "").strip()})
    return textos


def comando_do_tema(tema: str, temas: list[dict]) -> str:
    """O comando da proposta do tema, como a banca o escreve (decisao PMSC-23)."""
    return " ".join(str(_item_do_tema(tema, temas).get("comando") or "").split())


def quesitos_do_tema(tema: str, temas: list[dict]) -> list[str]:
    """Os aspectos que a proposta manda abordar, um por quesito do Cebraspe
    (PRF-37). Vao no pedido: a correcao da um conceito para cada um."""
    return [" ".join(str(q).split()) for q in _item_do_tema(tema, temas).get("quesitos") or []
            if str(q).strip()]


def tema_da_vez(dia: date, titulos_do_dia: list[str], temas: list[dict],
                feitos: frozenset[str] | set[str] = frozenset()) -> TemaDaVez | None:
    """O tema da vez (`_tema_da_vez`), com os textos motivadores e o comando."""
    vez = _tema_da_vez(dia, titulos_do_dia, temas, feitos)
    if vez is not None:
        vez.textos = textos_do_tema(vez.tema, temas)
        vez.comando = comando_do_tema(vez.tema, temas)
    return vez


def _tema_da_vez(dia: date, titulos_do_dia: list[str], temas: list[dict],
                 feitos: frozenset[str] | set[str] = frozenset()) -> TemaDaVez | None:
    """O tema para escrever hoje, nesta ordem:

    1. a faixa de Redacao do dia que traz o tema ("Redacao da semana: ...");
    2. o tema da lista `temas` com a data de hoje;
    3. o da mesma semana (de segunda a domingo): o que ja passou e ficou sem
       correcao (o mais recente), senao o proximo, ou o ultimo que ja passou;
    4. o proximo da lista.

    `feitos` sao os temas que ja tem redacao corrigida. Sem eles, a terca
    mostrava o tema de quarta, e o de segunda ficava para tras sem ninguem
    ver (decisao PMSC-39).
    """
    for titulo in titulos_do_dia:
        for prefixo in PREFIXOS_DE_TEMA:
            if titulo.startswith(prefixo) and titulo[len(prefixo):].strip():
                return TemaDaVez(titulo[len(prefixo):].strip(), dia,
                                 "a faixa de Redação do dia")

    datados = sorted(
        ((d, str(t.get("tema") or "").strip()) for t in temas or []
         if (d := _data(t.get("data"))) and str(t.get("tema") or "").strip()),
        key=lambda par: par[0],
    )
    for d, tema in datados:
        if d == dia:
            return TemaDaVez(tema, d, f"a lista de temas ({d:%d/%m})")

    segunda = dia - timedelta(days=dia.weekday())
    domingo = segunda + timedelta(days=6)
    da_semana = [(d, t) for d, t in datados if segunda <= d <= domingo]
    if da_semana:
        feitos = {" ".join(t.split()) for t in feitos}
        atrasados = [(d, t) for d, t in da_semana
                     if d < dia and " ".join(t.split()) not in feitos]
        if atrasados:
            d, tema = atrasados[-1]
            return TemaDaVez(tema, d, f"o tema da semana que ficou sem correção ({d:%d/%m})")
        proximos = [(d, t) for d, t in da_semana if d >= dia]
        d, tema = proximos[0] if proximos else da_semana[-1]
        return TemaDaVez(tema, d, f"o tema da semana ({d:%d/%m})")

    for d, tema in datados:
        if d > dia:
            return TemaDaVez(tema, d, f"o próximo tema da lista ({d:%d/%m})")
    return None


# --- o que a IA devolve -----------------------------------------------------

#: O formato da correcao, como vai no pedido. As chaves sao as do
#: `pedido_de_correcao` do redacao.yml.
FORMATO_DA_CORRECAO = {
    "nota_conteudo": 14.5,
    "criterios": [{"criterio": "Atendimento e desenvolvimento do tema",
                   "nota": 4.0, "comentario": "...",
                   "positivos": ["..."], "negativos": ["..."]}],
    "erros": [{"trecho": "haviam muitos problemas", "correcao": "havia muitos problemas",
               "regra": "haver no sentido de existir é impessoal",
               "tipo": "concordância",
               "explicacao": "'Haver' no sentido de 'existir' não tem sujeito: fica sempre no singular."}],
    "melhorias": [{"voce_escreveu": "...", "como_fica": "...", "por_que": "..."}],
    "pontos_positivos": ["...", "..."],
    "tres_pontos": ["...", "...", "..."],
    "focos": ["...", "...", "..."],
    "legibilidade": {"avaliacao": "legível", "observacao": "..."},
    "linhas_informadas": 24,
    "nota_final": 13.9,
    "paragrafo_mais_fraco": "Desenvolvimento 2",
    "paragrafo_reescrito": "...",
    "motivo_zero": "",
}

#: O formato da correcao do Cebraspe (PRF-37): um criterio por quesito, com o
#: CONCEITO (0 a 3) em `nota`; a NC e conta do radar (`nc_pelos_conceitos`).
#: A apresentacao e a estrutura vao em `apresentacao`, sem nota.
FORMATO_DA_CORRECAO_POR_CONCEITOS = {
    **{chave: valor for chave, valor in FORMATO_DA_CORRECAO.items() if chave != "nota_conteudo"},
    "criterios": [{"criterio": "2.1 <o aspecto 1 da proposta>", "nota": 2,
                   "comentario": "por que este conceito, pela escala do padrão",
                   "positivos": ["..."], "negativos": ["..."]}],
    "apresentacao": {"comentario": "...", "problemas": ["..."]},
    "nota_final": 13.9,
}


def formato_da_correcao(regras: dict | None) -> dict:
    """O formato que vai no pedido: por conceitos no Cebraspe, por nota na AOCP."""
    if (regras or {}).get("conceito_maximo"):
        return FORMATO_DA_CORRECAO_POR_CONCEITOS
    return FORMATO_DA_CORRECAO


#: Os tipos de erro de portugues: os da avaliacao da modalidade escrita (edital,
#: 11.5, b: ortografia, morfossintaxe e pontuacao) e os do caderno da AOCP
#: (concordancia, regencia e grafia, inclusive legibilidade).
TIPOS_DE_ERRO = ("ortografia", "acentuação", "crase", "concordância", "regência",
                 "pontuação", "morfossintaxe", "outro")

#: O formato da avaliacao da reescrita do paragrafo mais fraco (decisao PMSC-22).
FORMATO_DA_REESCRITA = {
    "melhorou": "sim | em parte | não",
    "comentario": "...",
    "o_que_ainda_falta": "...",
    "erros": [{"trecho": "...", "correcao": "...", "regra": "..."}],
}

FORMATO_DAS_IDEIAS = {
    "teses": [{"tese": "...", "argumentos": [
        {"argumento": "...", "fundamentacao": "...", "exemplo": "..."}]}],
    "proposta": {"agente": "...", "acao": "...", "meio": "...", "finalidade": "..."},
}


def _texto(valor) -> str:
    return " ".join(str(valor or "").split())


def _lista(valor) -> list[str]:
    """Uma lista de frases, sem as vazias (o que nao e lista vira lista vazia)."""
    if not isinstance(valor, list):
        return []
    return [_texto(v) for v in valor if _texto(v)]


def _numero(valor, nome: str) -> float:
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        raise RespostaInvalida(f"{nome} não é número: {valor!r}") from None


@dataclass
class Correcao:
    """A correcao que a IA devolveu, ja com a forma conferida."""

    nota_conteudo: float
    criterios: list[dict]
    erros: list[dict]
    tres_pontos: list[str]
    paragrafo_mais_fraco: str
    paragrafo_reescrito: str
    motivo_zero: str
    nota_final_da_ia: float | None
    descartados: list[str] = field(default_factory=list)
    #: O que a correcao didatica traz alem da nota (decisao PMSC-22): o que
    #: esta bom, o "voce escreveu -> como fica" de estilo e coesao (nao conta
    #: no NE), os focos da proxima e a letra, quando veio da foto da folha.
    pontos_positivos: list[str] = field(default_factory=list)
    melhorias: list[dict] = field(default_factory=list)
    focos: list[str] = field(default_factory=list)
    legibilidade: dict = field(default_factory=dict)
    #: Cebraspe (PRF-37): a NC saiu dos conceitos, e a apresentacao e a
    #: estrutura vem comentadas, sem nota.
    por_conceitos: bool = False
    apresentacao: dict = field(default_factory=dict)


def conferir_correcao(item: dict, regras: dict | None = None) -> Correcao:
    """A correcao com a forma certa, ou RespostaInvalida.

    Confere forma, e so forma: se o erro de portugues e mesmo erro, quem
    decide e eu, lendo a regra ao lado. O erro sem trecho ou sem correcao e
    descartado, e contado (ele nao entra no NE).

    Com `conceito_maximo` nas regras (o Cebraspe), cada criterio e um quesito
    com o conceito inteiro de 0 ao maximo, e a NC e a do radar; a
    `nota_conteudo` da IA, se vier, nao vale.
    """
    if not isinstance(item, dict):
        raise RespostaInvalida("a correção não é um objeto JSON")
    regras = regras or {}
    nota_maxima = float(regras.get("nota_maxima", 20))
    por_conceitos = bool(regras.get("conceito_maximo"))
    nc = 0.0
    if not por_conceitos:
        if "nota_conteudo" not in item:
            raise RespostaInvalida("falta a nota_conteudo")
        nc = _numero(item["nota_conteudo"], "nota_conteudo")
        if not 0 <= nc <= nota_maxima:
            raise RespostaInvalida(f"nota_conteudo fora de 0 a {nota_maxima:g}: {nc:g}")

    criterios = []
    for c in item.get("criterios") or []:
        if isinstance(c, dict) and _texto(c.get("criterio")):
            criterios.append({"criterio": _texto(c.get("criterio")),
                              "nota": _numero(c.get("nota", 0), "nota do critério"),
                              "comentario": _texto(c.get("comentario")),
                              "positivos": _lista(c.get("positivos")),
                              "negativos": _lista(c.get("negativos"))})
    if not criterios:
        raise RespostaInvalida("faltam as notas por critério")
    if por_conceitos:
        maximo = float(regras["conceito_maximo"])
        for c in criterios:
            if not (c["nota"] == int(c["nota"]) and 0 <= c["nota"] <= maximo):
                raise RespostaInvalida(
                    f"o conceito de {c['criterio']!r} tem de ser inteiro de 0 a {maximo:g}: "
                    f"{c['nota']:g}")
        nc = nc_pelos_conceitos([c["nota"] for c in criterios], regras)

    erros, descartados = [], []
    for e in item.get("erros") or []:
        if isinstance(e, dict) and _texto(e.get("trecho")) and _texto(e.get("correcao")):
            tipo = _texto(e.get("tipo")).casefold()
            erros.append({"trecho": _texto(e.get("trecho")),
                          "correcao": _texto(e.get("correcao")),
                          "regra": _texto(e.get("regra")),
                          "tipo": tipo if tipo in TIPOS_DE_ERRO else ("outro" if tipo else ""),
                          "explicacao": _texto(e.get("explicacao"))})
        else:
            descartados.append(f"erro sem trecho ou sem correção: {e!r}"[:200])

    pontos = [_texto(p) for p in item.get("tres_pontos") or [] if _texto(p)][:3]
    melhorias = [{"voce_escreveu": _texto(m.get("voce_escreveu")),
                  "como_fica": _texto(m.get("como_fica")),
                  "por_que": _texto(m.get("por_que"))}
                 for m in item.get("melhorias") or []
                 if isinstance(m, dict) and _texto(m.get("voce_escreveu"))
                 and _texto(m.get("como_fica"))]
    letra = item.get("legibilidade") if isinstance(item.get("legibilidade"), dict) else {}
    bruta = item.get("apresentacao") if isinstance(item.get("apresentacao"), dict) else {}
    apresentacao = {"comentario": _texto(bruta.get("comentario")),
                    "problemas": _lista(bruta.get("problemas"))} if bruta else {}
    da_ia = item.get("nota_final")
    return Correcao(
        nota_conteudo=nc, criterios=criterios, erros=erros, tres_pontos=pontos,
        paragrafo_mais_fraco=_texto(item.get("paragrafo_mais_fraco")),
        paragrafo_reescrito=str(item.get("paragrafo_reescrito") or "").strip(),
        motivo_zero=_texto(item.get("motivo_zero")),
        nota_final_da_ia=_numero(da_ia, "nota_final") if da_ia not in (None, "") else None,
        descartados=descartados,
        pontos_positivos=_lista(item.get("pontos_positivos")),
        melhorias=melhorias,
        focos=_lista(item.get("focos"))[:3],
        legibilidade={chave: _texto(letra.get(chave)) for chave in ("avaliacao", "observacao")
                      if _texto(letra.get(chave))},
        por_conceitos=por_conceitos,
        apresentacao=apresentacao,
    )


def conferir_ideias(item: dict) -> dict:
    """As ideias com a forma certa ({"teses": [...], "proposta": {...}})."""
    if not isinstance(item, dict):
        raise RespostaInvalida("as ideias não são um objeto JSON")
    teses = []
    for t in item.get("teses") or []:
        if not (isinstance(t, dict) and _texto(t.get("tese"))):
            continue
        argumentos = [
            {"argumento": _texto(a.get("argumento")),
             "fundamentacao": _texto(a.get("fundamentacao")),
             "exemplo": _texto(a.get("exemplo"))}
            for a in t.get("argumentos") or []
            if isinstance(a, dict) and _texto(a.get("argumento"))
        ]
        teses.append({"tese": _texto(t.get("tese")), "argumentos": argumentos})
    if not teses:
        raise RespostaInvalida("faltam as teses")
    bruta = item.get("proposta") if isinstance(item.get("proposta"), dict) else {}
    proposta = {chave: _texto(bruta.get(chave)) for chave in ("agente", "acao", "meio", "finalidade")}
    return {"teses": teses, "proposta": proposta}


def conferir_reescrita(item: dict) -> dict:
    """A avaliacao da reescrita do paragrafo mais fraco, com a forma certa."""
    if not isinstance(item, dict):
        raise RespostaInvalida("a avaliação da reescrita não é um objeto JSON")
    melhorou = _texto(item.get("melhorou")).casefold()
    if melhorou not in ("sim", "em parte", "não"):
        raise RespostaInvalida(f"melhorou tem de ser sim, em parte ou não: {melhorou!r}")
    if not _texto(item.get("comentario")):
        raise RespostaInvalida("falta o comentário da reescrita")
    erros = [{"trecho": _texto(e.get("trecho")), "correcao": _texto(e.get("correcao")),
              "regra": _texto(e.get("regra"))}
             for e in item.get("erros") or []
             if isinstance(e, dict) and _texto(e.get("trecho")) and _texto(e.get("correcao"))]
    return {"melhorou": melhorou, "comentario": _texto(item.get("comentario")),
            "o_que_ainda_falta": _texto(item.get("o_que_ainda_falta")), "erros": erros}


# --- o texto com os erros no lugar ------------------------------------------

def texto_anotado(texto: str, erros: list[dict]) -> list[tuple[str, int | None]]:
    """O texto em pedacos, com o numero do erro (1, 2...) no pedaco do trecho.

    Cada trecho e procurado depois do anterior (o texto e lido na ordem) e,
    se nao estiver ali, desde o comeco; o que nao se acha fica so na lista,
    sem marca. Dois erros no mesmo lugar: vale o primeiro.
    """
    texto = texto or ""
    marcas, de, ocupado = [], 0, []
    for numero, erro in enumerate(erros or [], start=1):
        trecho = (erro.get("trecho") or "").strip()
        if not trecho:
            continue
        inicio = texto.find(trecho, de)
        if inicio < 0:
            inicio = texto.find(trecho)
        if inicio < 0:
            continue
        fim = inicio + len(trecho)
        if any(inicio < b and a < fim for a, b in ocupado):
            continue
        ocupado.append((inicio, fim))
        marcas.append((inicio, fim, numero))
        de = fim
    pedacos, cursor = [], 0
    for inicio, fim, numero in sorted(marcas):
        if inicio > cursor:
            pedacos.append((texto[cursor:inicio], None))
        pedacos.append((texto[inicio:fim], numero))
        cursor = fim
    if cursor < len(texto):
        pedacos.append((texto[cursor:], None))
    return pedacos


# --- a redacao-modelo (decisao PMSC-24) -------------------------------------

#: O numero que o modelo pode usar sem estar nas fontes do tema: o ano da
#: Constituicao, que todo candidato sabe. Qualquer outro numero tem que vir do
#: repertorio, do comando ou de um texto motivador do proprio tema.
NUMEROS_LIVRES = {"1988"}

_NUMERO = re.compile(r"\d+(?:[.,]\d+)*")


def fontes_do_tema(item_do_tema: dict, repertorio: list[str]) -> list[str]:
    """O que o candidato tem na mao: o tema, o comando, cada texto motivador
    com a sua fonte, e o repertorio do redacao.yml."""
    fontes = [str(item_do_tema.get("tema") or ""), str(item_do_tema.get("comando") or "")]
    for x in item_do_tema.get("textos") or []:
        if isinstance(x, dict):
            fontes += [str(x.get(chave) or "") for chave in ("texto", "lei", "fonte", "titulo")]
    return fontes + [str(r) for r in repertorio or []]


def numeros_sem_fonte(texto: str, fontes: list[str]) -> list[str]:
    """Os numeros do texto que nao aparecem, como numero, em nenhuma fonte:
    numero inventado num modelo ensina a inventar na prova."""
    conhecidos = set(NUMEROS_LIVRES)
    for fonte in fontes:
        conhecidos.update(_NUMERO.findall(fonte))
    return [n for n in _NUMERO.findall(texto or "") if n not in conhecidos]

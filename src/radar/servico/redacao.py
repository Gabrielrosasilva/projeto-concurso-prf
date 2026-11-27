"""A aba Redacao: o historico, os pedidos a IA e a correcao (Etapa 2 do
PEDIDO_PMSC.md, decisao PMSC-5).

O historico mora em `data/redacoes.json`, versionado, e nunca no banco: o
arquivo E a fonte, como o `data/acompanhamentos.json` (decisao 141). Por isso o
`exportar` e o `importar` nao tem o que copiar, e o `sincronizar` o leva ao git
junto com os outros (`cli.ARQUIVOS_DO_RADAR`).

Dois caminhos para a IA, como o resto do radar:

  * **sem API** (o padrao: a chave fica desligada na copia PMSC): o pedido vai
    para `data/pedido_ia.json`, eu respondo pelo Claude Code e o
    `radar redacao --importar` le de volta, pelo mesmo `manual.importar` das
    questoes geradas - com a procedencia "Claude Code, importado manualmente";
  * **com API**, quando ha `RADAR_ANTHROPIC_KEY`: uma chamada, com o custo
    estimado mostrado antes do botao.

Nos dois, a NOTA e do radar (`radar.redacao.nota`), e a conta da IA so aparece
ao lado, se ela mandou. Texto de IA sem procedencia nao entra.
"""
import json
import uuid
from datetime import date, datetime
from pathlib import Path

import requests

from radar import config, cronograma, gerador
from radar import redacao as regras_da_redacao
from radar.models import agora
from radar.servico import manual
from radar.util import fuso_local

TIPO_CORRECAO = "redacao_correcao"
TIPO_IDEIAS = "redacao_ideias"
#: A segunda correcao, so do paragrafo mais fraco reescrito (decisao PMSC-22).
TIPO_REESCRITA = "redacao_reescrita"

#: De onde veio o texto: a foto da folha (eu transcrevo, conto as linhas e
#: avalio a letra) ou o que foi digitado na aba.
ORIGENS = ("foto", "digitado")

#: O teto de tokens de saida da correcao: o modelo pensa antes de responder,
#: e o raciocinio conta como saida. Apertar corta a resposta no meio.
MAX_TOKENS = 8000

#: A media de saida que entra na estimativa de custo: a correcao inteira,
#: com o paragrafo reescrito e o raciocinio, fica nisso com folga.
SAIDA_ESTIMADA = {TIPO_CORRECAO: 5000, TIPO_IDEIAS: 2500, TIPO_REESCRITA: 1500}


def caminho() -> Path:
    return config.diretorio_dados() / "redacoes.json"


def ler() -> dict:
    """{"redacoes": [...], "ideias": [...]}. Arquivo ausente e vazio."""
    arquivo = caminho()
    if not arquivo.exists():
        return {"redacoes": [], "ideias": []}
    dados = json.loads(arquivo.read_text(encoding="utf-8")) or {}
    return {"redacoes": list(dados.get("redacoes") or []),
            "ideias": list(dados.get("ideias") or [])}


def gravar(dados: dict) -> None:
    arquivo = caminho()
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    ordenado = {
        "redacoes": sorted(dados.get("redacoes") or [],
                           key=lambda r: (r.get("data") or "", r.get("criado_em") or "")),
        "ideias": sorted(dados.get("ideias") or [],
                         key=lambda r: (r.get("data") or "", r.get("criado_em") or "")),
    }
    arquivo.write_text(json.dumps(ordenado, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")


# --- o que a tela mostra ----------------------------------------------------

def tema_da_vez(dia: date) -> regras_da_redacao.TemaDaVez | None:
    """O tema de hoje: a faixa de Redacao do dia, ou a lista do redacao.yml."""
    titulos = []
    try:
        plano = cronograma.carregar()
        dia_do_plano = cronograma.montar_dia(plano, dia)
        titulos = [f.titulo for f in (dia_do_plano.faixas() if dia_do_plano else [])
                   if f.materia == regras_da_redacao.MATERIA and f.titulo]
    except (cronograma.ErroNoCronograma, OSError):
        # Sem cronograma (ou com um quebrado), o tema sai so da lista.
        titulos = []
    temas = regras_da_redacao.carregar().get("temas") or []
    feitos = {str(r.get("tema") or "") for r in ler()["redacoes"]}
    return regras_da_redacao.tema_da_vez(dia, titulos, temas, feitos)


def historico() -> list[dict]:
    """As redacoes corrigidas, da mais nova para a mais antiga."""
    return list(reversed(ler()["redacoes"]))


def evolucao() -> list[tuple[str, float]]:
    """(data, nota final) de cada redacao, em ordem de data: a curva da nota."""
    return [(r.get("data") or "", float((r.get("nota") or {}).get("final") or 0))
            for r in ler()["redacoes"]]


def achar(redacao_id: str) -> dict | None:
    return next((r for r in ler()["redacoes"] if r.get("id") == redacao_id), None)


# --- a redacao-modelo (decisao PMSC-24) -------------------------------------

def caminho_dos_modelos() -> Path:
    return config.diretorio_dados() / "redacoes_modelo.json"


def modelo_do_tema(tema: str | None) -> dict | None:
    """A redacao-modelo do tema, escrita pela IA, com a procedencia do arquivo.

    So a pagina da correcao a mostra: ver o modelo antes de escrever ensina a
    copiar, e nao a pensar. Arquivo ausente ou tema sem modelo: None.
    """
    arquivo = caminho_dos_modelos()
    if not tema or not arquivo.exists():
        return None
    dados = json.loads(arquivo.read_text(encoding="utf-8")) or {}
    procurado = " ".join(tema.split()).casefold()
    for modelo in dados.get("modelos") or []:
        if " ".join(str(modelo.get("tema") or "").split()).casefold() == procurado:
            return {"tema": modelo.get("tema"),
                    "paragrafos": [p.strip() for p in str(modelo.get("texto") or "").split("\n\n")
                                   if p.strip()],
                    "pontos": [str(p) for p in modelo.get("pontos") or []],
                    "procedencia": str(dados.get("procedencia") or "")}
    return None


# --- o texto de apoio (PRF-67) ----------------------------------------------

def caminho_dos_textos_de_apoio() -> Path:
    return config.diretorio_dados() / "textos_de_apoio.json"


def texto_de_apoio_do_tema(tema: str | None) -> dict | None:
    """O texto de apoio do tema, escrito pela IA, com a procedencia do arquivo.

    E repertorio para LER ANTES de escrever (contexto, caminhos de argumento,
    o que saber, situacoes, a lei quando pertinente e um fecho), e nao uma
    redacao pronta: por isso aparece na proposta, e o modelo so na correcao.
    Arquivo ausente ou tema sem texto: None (a tela mostra o "Me da ideias").
    """
    arquivo = caminho_dos_textos_de_apoio()
    if not tema or not arquivo.exists():
        return None
    dados = json.loads(arquivo.read_text(encoding="utf-8")) or {}
    procurado = " ".join(tema.split()).casefold()
    for apoio in dados.get("textos") or []:
        if " ".join(str(apoio.get("tema") or "").split()).casefold() == procurado:
            return {**apoio, "procedencia": str(dados.get("procedencia") or "")}
    return None


def texto_de_apoio_corrido(apoio: dict | None) -> str:
    """O texto de apoio numa string so, para ir no pedido de correcao: o
    corretor precisa dele para ver o trecho copiado (como faz com os textos
    motivadores)."""
    if not apoio:
        return ""
    partes = [apoio.get("contexto") or ""]
    partes += [f"{c.get('titulo')}: {c.get('texto')}" for c in apoio.get("caminhos") or []]
    partes += list(apoio.get("o_que_saber") or []) + list(apoio.get("situacoes") or [])
    partes += [f"{b.get('lei')}: {b.get('trecho')} ({b.get('por_que')})"
               for b in apoio.get("base_legal") or []]
    partes.append(apoio.get("fecho") or "")
    return "\n".join(" ".join(str(p).split()) for p in partes if str(p).strip())


def ultimas_ideias(tema: str | None = None) -> dict | None:
    """As ideias mais novas (do tema, quando ele vem)."""
    ideias = ler()["ideias"]
    if tema:
        ideias = [i for i in ideias if i.get("tema") == tema] or ideias
    return ideias[-1] if ideias else None


# --- o pedido ---------------------------------------------------------------

def _instrucao(tipo: str) -> str:
    """O pedido do redacao.yml mais o repertorio e o formato, igual nos dois
    caminhos (arquivo e API): e o mesmo texto, para a resposta vir igual."""
    dados = regras_da_redacao.carregar()
    if not dados:
        raise ValueError(f"falta o {regras_da_redacao.caminho()}")
    base = dados.get({TIPO_CORRECAO: "pedido_de_correcao", TIPO_IDEIAS: "pedido_de_ideias",
                      TIPO_REESCRITA: "pedido_de_reescrita"}[tipo]) or ""
    formato = _formato(tipo)
    repertorio = "\n".join(f"- {r}" for r in dados.get("repertorio") or [])
    return (f"{base.strip()}\n\nREPERTÓRIO (o único que você pode citar):\n{repertorio}\n\n"
            "Responda SOMENTE um JSON neste formato (as chaves exatamente assim; "
            "os valores são só exemplo de forma):\n"
            f"{json.dumps(formato, ensure_ascii=False)}")


def _formato(tipo: str) -> dict:
    regras = regras_da_redacao.carregar().get("regras_do_edital") or {}
    return {TIPO_CORRECAO: regras_da_redacao.formato_da_correcao(regras),
            TIPO_IDEIAS: regras_da_redacao.FORMATO_DAS_IDEIAS,
            TIPO_REESCRITA: regras_da_redacao.FORMATO_DA_REESCRITA}[tipo]


#: A chave de cada resposta no lote: {"id": "r1", <chave>: {...}}.
CHAVE_DA_RESPOSTA = {TIPO_CORRECAO: "correcao", TIPO_IDEIAS: "ideias",
                     TIPO_REESCRITA: "avaliacao"}


def textos_do_tema(tema: str) -> list[dict]:
    """Os textos motivadores do tema no redacao.yml (decisao PMSC-22)."""
    return regras_da_redacao.textos_do_tema(tema, regras_da_redacao.carregar().get("temas") or [])


def comando_do_tema(tema: str) -> str:
    """O comando da proposta no redacao.yml (decisao PMSC-23)."""
    return regras_da_redacao.comando_do_tema(tema, regras_da_redacao.carregar().get("temas") or [])


def _pedido(tipo: str, tema: str, data: date, texto: str | None = None,
            linhas: int | None = None, origem: str | None = None) -> dict:
    pedido = {"id": "r1", "tema": tema, "data": data.isoformat()}
    if tipo == TIPO_CORRECAO:
        # O corretor le os textos motivadores da proposta: e por eles que se
        # ve a copia de trecho e a informatividade que vai alem deles. E le o
        # comando: a pergunta "A ou B?" pede posicionamento (decisao PMSC-23).
        pedido.update({"linhas": int(linhas or 0), "texto": texto or "",
                       "origem": origem if origem in ORIGENS else "digitado",
                       "comando": comando_do_tema(tema),
                       "textos_motivadores": textos_do_tema(tema)})
        # No Cebraspe, um conceito por aspecto da proposta (PRF-37).
        quesitos = regras_da_redacao.quesitos_do_tema(
            tema, regras_da_redacao.carregar().get("temas") or [])
        if quesitos:
            pedido["quesitos"] = quesitos
        # O texto de apoio foi lido antes de escrever: trecho copiado dele
        # tambem nao e argumento do candidato (PRF-67).
        apoio = texto_de_apoio_corrido(texto_de_apoio_do_tema(tema))
        if apoio:
            pedido["texto_de_apoio"] = apoio
    return pedido


def montar_lote(tipo: str, tema: str, data: date, texto: str | None = None,
                linhas: int | None = None, origem: str | None = None,
                pedido: dict | None = None) -> dict:
    """O lote no formato do `manual` (decisao 116): lote, tipo, instrucao,
    formato da resposta com o `modelo` que escreveu, e o pedido."""
    momento = agora()
    chave = CHAVE_DA_RESPOSTA[tipo]
    formato = _formato(tipo)
    return {
        "lote": f"{tipo}-{momento:%Y%m%d-%H%M%S}",
        "tipo": tipo,
        "criado_em": momento.isoformat(),
        "como_responder": _instrucao(tipo),
        "formato_da_resposta": {"lote": "<o lote deste arquivo>",
                                "modelo": "<o modelo que escreveu>",
                                "respostas": [{"id": "r1", chave: formato}]},
        "pedidos": [pedido or _pedido(tipo, tema, data, texto, linhas, origem)],
    }


def _gravar_lote(lote: dict) -> Path:
    destino = manual.caminho_do_pedido()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(lote, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    return destino


def escrever_pedido(tipo: str, tema: str, data: date, texto: str | None = None,
                    linhas: int | None = None, origem: str | None = None) -> Path:
    """Grava o pedido em data/pedido_ia.json (o mesmo das geradas: pedido
    novo substitui o anterior) e devolve o caminho."""
    if tipo == TIPO_CORRECAO:
        _conferir_texto(texto, linhas)
    return _gravar_lote(montar_lote(tipo, tema, data, texto, linhas, origem))


def escrever_pedido_de_reescrita(redacao_id: str, texto: str) -> Path:
    """O pedido da segunda correcao: o paragrafo mais fraco, reescrito a mao
    depois da correcao (decisao PMSC-22). Leva a redacao inteira, o que a
    correcao disse do paragrafo e o modelo dela, para comparar."""
    registro = achar(redacao_id)
    if registro is None:
        raise ValueError(f"não achei a redação {redacao_id}")
    if not (texto or "").strip():
        raise ValueError("falta o parágrafo reescrito")
    pedido = {"id": "r1", "redacao_id": redacao_id, "tema": registro.get("tema"),
              "data": registro.get("data"),
              "paragrafo_mais_fraco": registro.get("paragrafo_mais_fraco") or "",
              "redacao": registro.get("texto") or "",
              "o_que_a_correcao_disse": registro.get("tres_pontos") or [],
              "paragrafo_reescrito_pelo_corretor": registro.get("paragrafo_reescrito") or "",
              "reescrita": texto.strip()}
    dia = date.fromisoformat(registro.get("data")) if registro.get("data") else agora().date()
    return _gravar_lote(montar_lote(TIPO_REESCRITA, registro.get("tema") or "", dia,
                                    pedido=pedido))


def passos_sem_api() -> list[str]:
    """O que fazer depois que o pedido foi gravado (o passo 1): pedir a
    correcao ao Claude Code, que responde e importa."""
    return [
        'no Claude Code do VS Code: "corrige a redação" (ele lê data/pedido_ia.json, '
        "corrige como a banca e importa)",
        "ou, à mão: .venv\\Scripts\\radar.exe redacao --importar data/resposta_ia.json",
    ]


def _conferir_texto(texto: str | None, linhas: int | None) -> None:
    if not (texto or "").strip():
        raise ValueError("cole o texto da redação")
    if not linhas or not 1 <= int(linhas) <= 40:
        raise ValueError("informe quantas linhas a folha teve (de 1 a 40)")


# --- a importacao (pelo manual.importar) ------------------------------------

def _registro_da_correcao(pedido: dict, correcao: regras_da_redacao.Correcao,
                          procedencia: str, momento: datetime) -> dict:
    regras = regras_da_redacao.carregar().get("regras_do_edital") or {}
    conta = regras_da_redacao.nota(correcao.nota_conteudo, len(correcao.erros),
                                   int(pedido.get("linhas") or 0), regras,
                                   correcao.motivo_zero)
    return {
        "id": uuid.uuid4().hex[:12],
        "data": pedido.get("data"),
        "tema": pedido.get("tema"),
        "linhas": int(pedido.get("linhas") or 0),
        "texto": pedido.get("texto") or "",
        "nota_conteudo": correcao.nota_conteudo,
        "criterios": correcao.criterios,
        "por_conceitos": correcao.por_conceitos,
        "apresentacao": correcao.apresentacao,
        "erros": correcao.erros,
        "tres_pontos": correcao.tres_pontos,
        "paragrafo_mais_fraco": correcao.paragrafo_mais_fraco,
        "paragrafo_reescrito": correcao.paragrafo_reescrito,
        "motivo_zero": correcao.motivo_zero,
        "nota_final_da_ia": correcao.nota_final_da_ia,
        "pontos_positivos": correcao.pontos_positivos,
        "melhorias": correcao.melhorias,
        "focos": correcao.focos,
        "legibilidade": correcao.legibilidade,
        "origem": pedido.get("origem") or "digitado",
        "textos_motivadores": [{"fonte": x.get("fonte") or x.get("lei"), "url": x.get("url")}
                               for x in pedido.get("textos_motivadores") or []],
        "reescritas": [],
        "nota": {"nc": conta.nc, "ne": conta.ne, "tl": conta.tl, "bruta": conta.bruta,
                 "linhas_faltando": conta.linhas_faltando, "desconto": conta.desconto,
                 "final": conta.final, "aprovada": conta.aprovada, "fator": conta.fator,
                 "acima_do_maximo": conta.acima_do_maximo},
        "procedencia": procedencia,
        "criado_em": momento.isoformat(),
    }


def _por_id(respostas: list[dict], chave: str) -> dict:
    return {r.get("id"): r.get(chave) for r in respostas if isinstance(r, dict)}


def importar_correcao(lote: dict, respostas: list[dict], procedencia: str) -> dict:
    """Grava as correcoes do lote. Devolve o resultado no formato do manual."""
    dados = ler()
    gravadas, recusas = 0, []
    respostas_por_id = _por_id(respostas, "correcao")
    regras = regras_da_redacao.carregar().get("regras_do_edital") or {}
    for pedido in lote.get("pedidos") or []:
        bruta = respostas_por_id.get(pedido.get("id"))
        if bruta is None:
            recusas.append(f"{pedido.get('id')}: sem resposta")
            continue
        try:
            correcao = regras_da_redacao.conferir_correcao(bruta, regras)
        except regras_da_redacao.RespostaInvalida as erro:
            recusas.append(f"{pedido.get('id')}: {erro}")
            continue
        dados["redacoes"].append(_registro_da_correcao(pedido, correcao, procedencia, agora()))
        recusas.extend(correcao.descartados)
        gravadas += 1
    if gravadas:
        gravar(dados)
    return {"gravadas": gravadas, "repetidas": 0, "recusas": recusas}


def importar_reescrita(lote: dict, respostas: list[dict], procedencia: str) -> dict:
    """Grava a avaliacao da reescrita na redacao de origem (`reescritas`)."""
    dados = ler()
    gravadas, recusas = 0, []
    respostas_por_id = _por_id(respostas, "avaliacao")
    for pedido in lote.get("pedidos") or []:
        registro = next((r for r in dados["redacoes"]
                         if r.get("id") == pedido.get("redacao_id")), None)
        if registro is None:
            recusas.append(f"{pedido.get('id')}: a redação {pedido.get('redacao_id')} não existe")
            continue
        try:
            avaliacao = regras_da_redacao.conferir_reescrita(respostas_por_id.get(pedido.get("id")))
        except regras_da_redacao.RespostaInvalida as erro:
            recusas.append(f"{pedido.get('id')}: {erro}")
            continue
        registro.setdefault("reescritas", []).append({
            "texto": pedido.get("reescrita") or "", **avaliacao,
            "procedencia": procedencia, "criado_em": agora().isoformat()})
        gravadas += 1
    if gravadas:
        gravar(dados)
    return {"gravadas": gravadas, "repetidas": 0, "recusas": recusas}


def importar_ideias(lote: dict, respostas: list[dict], procedencia: str) -> dict:
    dados = ler()
    gravadas, recusas = 0, []
    respostas_por_id = _por_id(respostas, "ideias")
    for pedido in lote.get("pedidos") or []:
        bruta = respostas_por_id.get(pedido.get("id"))
        try:
            ideias = regras_da_redacao.conferir_ideias(bruta)
        except regras_da_redacao.RespostaInvalida as erro:
            recusas.append(f"{pedido.get('id')}: {erro}")
            continue
        dados["ideias"].append({"id": uuid.uuid4().hex[:12], "data": pedido.get("data"),
                                "tema": pedido.get("tema"), **ideias,
                                "procedencia": procedencia,
                                "criado_em": agora().isoformat()})
        gravadas += 1
    if gravadas:
        gravar(dados)
    return {"gravadas": gravadas, "repetidas": 0, "recusas": recusas}


# --- com API ----------------------------------------------------------------

def tem_api() -> bool:
    return bool(config.chave_da_anthropic())


def estimar(tipo: str, texto: str = "") -> tuple[int, int, float]:
    """(tokens de entrada, tokens de saida, custo em dolar) antes de gastar.
    A regra pratica de ~3,5 caracteres por token, a mesma do `gerador`."""
    try:
        caracteres = len(_instrucao(tipo)) + len(texto or "")
    except ValueError:
        caracteres = len(texto or "")
    entrada = int(caracteres / 3.5)
    saida = SAIDA_ESTIMADA[tipo]
    custo = entrada / 1e6 * gerador.PRECO_ENTRADA + saida / 1e6 * gerador.PRECO_SAIDA
    return entrada, saida, custo


def procedencia_da_api(quando: datetime | None = None) -> str:
    momento = (quando or agora()).astimezone(fuso_local())
    return f"{gerador.MODELO} pela API, em {momento:%d/%m/%Y}"


def _chamar(tipo: str, conteudo: str, sessao=None) -> dict:
    """Uma chamada a API. Devolve o JSON da resposta (ainda sem conferir)."""
    sessao = sessao or requests.Session()
    resposta = sessao.post(
        gerador.API,
        headers={"x-api-key": config.chave_da_anthropic() or "",
                 "anthropic-version": gerador.VERSAO_DA_API,
                 "content-type": "application/json"},
        json={"model": gerador.MODELO, "max_tokens": MAX_TOKENS,
              "thinking": {"type": "adaptive"},
              "system": _instrucao(tipo),
              "messages": [{"role": "user", "content": conteudo}]},
        timeout=config.TIMEOUT_REQUISICAO * 10,
    )
    resposta.raise_for_status()
    corpo = resposta.json()
    texto = "".join(parte.get("text", "") for parte in corpo.get("content") or [])
    return manual._ler_json(texto)


def corrigir_pela_api(texto: str, linhas: int, tema: str, data: date, sessao=None) -> dict:
    """Corrige pela API e grava. Devolve o registro gravado."""
    if not tem_api():
        raise ValueError("a chave da API está desligada: use o caminho sem API")
    _conferir_texto(texto, linhas)
    textos = "\n\n".join(f"TEXTO {i}: {x['texto']} ({x['fonte']})"
                         for i, x in enumerate(textos_do_tema(tema), start=1))
    comando = comando_do_tema(tema)
    apoio = texto_de_apoio_corrido(texto_de_apoio_do_tema(tema))
    corpo = _chamar(TIPO_CORRECAO,
                    f"TEMA: {tema}\n" + (f"COMANDO DA PROPOSTA: {comando}\n" if comando else "")
                    + f"LINHAS ESCRITAS NA FOLHA: {linhas}\n\n"
                    f"TEXTOS MOTIVADORES:\n{textos or '(sem)'}\n\n"
                    + (f"TEXTO DE APOIO (lido antes de escrever):\n{apoio}\n\n" if apoio else "")
                    + f"REDAÇÃO:\n{texto}",
                    sessao)
    regras = regras_da_redacao.carregar().get("regras_do_edital") or {}
    correcao = regras_da_redacao.conferir_correcao(corpo.get("correcao", corpo), regras)
    pedido = _pedido(TIPO_CORRECAO, tema, data, texto, linhas)
    registro = _registro_da_correcao(pedido, correcao, procedencia_da_api(), agora())
    dados = ler()
    dados["redacoes"].append(registro)
    gravar(dados)
    return registro


def ideias_pela_api(tema: str, data: date, sessao=None) -> dict:
    if not tem_api():
        raise ValueError("a chave da API está desligada: use o caminho sem API")
    corpo = _chamar(TIPO_IDEIAS, f"TEMA: {tema}", sessao)
    ideias = regras_da_redacao.conferir_ideias(corpo.get("ideias", corpo))
    registro = {"id": uuid.uuid4().hex[:12], "data": data.isoformat(), "tema": tema,
                **ideias, "procedencia": procedencia_da_api(),
                "criado_em": agora().isoformat()}
    dados = ler()
    dados["ideias"].append(registro)
    gravar(dados)
    return registro

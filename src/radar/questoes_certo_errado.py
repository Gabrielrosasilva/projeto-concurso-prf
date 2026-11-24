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
X e a anulada. Certo/Errado nunca mede nem treina como a multipla escolha
(decisao 166): a prova fica recusada no acervo complementar, pelo
`complementar.validar`, e a tela so a mostra para conferir, sem gravar
resposta.

O caderno escaneado tambem nao tem o traco do sublinhado que o
`radar/destaques.py` le - ele achava letra solta. O termo destacado vem da
transcricao (`destaques`, a lista dos termos de cada item), pelo `marcas`.
"""
import json
import re
from pathlib import Path

from radar.questoes import Questao
from radar.questoes_selecon import materia_da_faixa

#: As duas alternativas de todo item de Certo/Errado.
ALTERNATIVAS = {"c": "Certo", "e": "Errado"}
LETRAS = tuple(sorted(ALTERNATIVAS))


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

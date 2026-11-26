"""A distancia dos aprovados (analise pedida pelo Gabriel em 25/11/2026, PRF-34): a minha
nota liquida em cada bloco da objetiva, ao lado da dos aprovados da PRF 2021.

Os numeros dos aprovados moram em `data/aprovados_prf.json`: so agregados (nenhum nome,
nenhuma inscricao), com a fonte (os editais do Cebraspe) e a procedencia; como sairam
esta em `docs/aprovados_prf.md`. A minha nota e a do `metricas` (a nota liquida do
Certo/Errado, PRF-28), separada pelo bloco da materia de cada questao. As contas moram
aqui; a tela so desenha.
"""
import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

from radar import amostra, config
from radar.db import criar_tabelas, sessao
from radar.models import QuestaoDeProva
from radar.origem import ACERVO
from radar.servico import metricas
from radar.servico.metricas import NotaLiquida, nota_liquida


def _caminho() -> Path:
    return config.diretorio_dados() / "aprovados_prf.json"


def carregar(caminho: Path | None = None) -> dict | None:
    """O arquivo dos aprovados; None sem ele (a tela simplesmente nao mostra)."""
    arquivo = caminho or _caminho()
    if not arquivo.exists():
        return None
    return json.loads(arquivo.read_text(encoding="utf-8"))


def _porcento(nota: float, itens: int) -> int:
    return round(100 * nota / itens)


@dataclass
class LinhaDoBloco:
    """Um bloco da objetiva: a minha nota liquida e a dos aprovados de 2021."""

    #: Os numeros dos aprovados sao do acervo (contados nos editais), nao da banca.
    origem = ACERVO

    bloco: str
    itens: int
    minha: NotaLiquida
    #: Menos itens respondidos que o minimo da materia (config/amostra.yml):
    #: a porcentagem aparece, mas com o aviso.
    pouca_amostra: bool
    #: A mediana da lista geral (todos com a discursiva corrigida na ampla) e
    #: a das 1.500 maiores notas, em porcentagem do bloco.
    mediana_geral: int
    mediana_das_1500: int

    @property
    def falta(self) -> int | None:
        """Quantos pontos percentuais faltam para a mediana das 1.500. None sem
        item respondido; zero ou negativo quando ja cheguei."""
        if self.minha.porcentagem is None:
            return None
        return self.mediana_das_1500 - self.minha.porcentagem


@dataclass
class Distancia:
    """O cartao inteiro: os tres blocos e o que vale para a prova toda."""

    origem = ACERVO

    linhas: list[LinhaDoBloco]
    corte_da_ampla: float
    mediana_objetiva_das_1500: float
    mediana_discursiva_das_1500: float
    cairam_na_discursiva: int
    corrigidas: int
    #: Quantos estao na lista geral (a da ampla), de onde sai a mediana dela.
    na_lista_geral: int

    def frase(self) -> str:
        """O resto do quadro, por extenso e no formato brasileiro."""
        corrigidas = f"{self.corrigidas:,}".replace(",", ".")
        na_geral = f"{self.na_lista_geral:,}".replace(",", ".")
        discursiva = f"{self.mediana_discursiva_das_1500:.2f}".replace(".", ",")
        return (f"Lista geral: a mediana dos {na_geral} da ampla concorrência, entre "
                f"{corrigidas} discursivas corrigidas; o corte da ampla para ter a "
                f"discursiva corrigida foi "
                f"{self.corte_da_ampla:.0f} de 120. As 1.500: objetiva com mediana "
                f"{self.mediana_objetiva_das_1500:.0f} e discursiva com mediana "
                f"{discursiva} de 20. {self.cairam_na_discursiva} caíram na discursiva "
                f"(abaixo de 10).")


def distancia(dados: dict | None = None) -> Distancia | None:
    """A minha nota liquida por bloco ao lado da dos aprovados de 2021. None
    sem o arquivo dos aprovados."""
    dados = dados if dados is not None else carregar()
    if not dados:
        return None
    bloco_da_materia = {m: bloco for bloco, materias in dados["blocos"].items() for m in materias}
    criar_tabelas()
    with sessao() as s:
        respostas = metricas.respostas_de_certo_errado(s)
        ids = {r.questao_id for r in respostas}
        materias = dict(s.execute(select(QuestaoDeProva.id, QuestaoDeProva.materia)
                                  .where(QuestaoDeProva.id.in_(ids))).all()) if ids else {}
    por_bloco: dict[str, list] = {bloco: [] for bloco in dados["blocos"]}
    for r in respostas:
        bloco = bloco_da_materia.get(materias.get(r.questao_id))
        if bloco:
            por_bloco[bloco].append(r)
    minimo = amostra.carregar().do_nivel("materia")
    ano = dados["2021"]
    linhas = []
    for bloco, respostas_do_bloco in por_bloco.items():
        geral, das_1500 = ano["lista_geral"][f"bloco_{bloco}"], ano["as_1500"][f"bloco_{bloco}"]
        minha = nota_liquida(respostas_do_bloco)
        linhas.append(LinhaDoBloco(
            bloco=bloco, itens=geral["itens"], minha=minha, pouca_amostra=minha.itens < minimo,
            mediana_geral=_porcento(geral["mediana"], geral["itens"]),
            mediana_das_1500=_porcento(das_1500["mediana"], das_1500["itens"])))
    return Distancia(linhas=linhas, corte_da_ampla=ano["corte_da_ampla"],
                     mediana_objetiva_das_1500=ano["as_1500"]["objetiva"]["mediana"],
                     mediana_discursiva_das_1500=ano["as_1500"]["discursiva"]["mediana"],
                     cairam_na_discursiva=ano["cairam_na_discursiva"], corrigidas=ano["corrigidas"],
                     na_lista_geral=ano["lista_geral"].get("n", 0))

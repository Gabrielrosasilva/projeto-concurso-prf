"""Analises > Meu rendimento (PRF-63): uma tela so com o meu rendimento.

Uma linha por materia do edital, na ordem do peso na prova: a nota liquida
do Cebraspe, o acerto bruto ao lado, quantas questoes fiz, o peso, a seta de
tendencia e a cor contra a meta. Embaixo, "Estude primeiro": os tres assuntos
mais fracos com amostra que sustente a conta.

Nenhuma conta nova mora aqui: os numeros sao do `servico.metricas`
(`rendimento_por_materia`) e do `servico.desempenho_por_conteudo`; o peso e a
meta, do cronograma. Este arquivo so junta e decide a cor.
"""
from dataclasses import dataclass, field
from datetime import datetime

from radar import amostra as regua
from radar import cronograma as plano_de_estudo
from radar.servico import desempenho_por_conteudo, metricas
from radar.servico.materias import _achar

#: Quantos pontos abaixo da meta ainda e amarelo (e nao vermelho).
FAIXA_DO_AMARELO = 15

#: Quantos assuntos no "Estude primeiro".
QUANTOS_PRIMEIRO = 3


@dataclass
class LinhaDoRendimento:
    """Uma materia do edital e o que eu fiz nela."""
    materia: str
    questoes_na_prova: int
    meta: int                           # acertos na prova (cronograma.yml)
    minimo: int                         # respostas para a cor valer
    numeros: metricas.RendimentoDaMateria = None

    def __post_init__(self):
        if self.numeros is None:
            self.numeros = metricas.RendimentoDaMateria(self.materia)

    @property
    def meta_em_porcentagem(self) -> int:
        return round(100 * self.meta / self.questoes_na_prova) if self.questoes_na_prova else 0

    @property
    def medida(self) -> int | None:
        """O numero que vai contra a meta: a nota liquida (em %) quando ha
        item de Certo/Errado - e assim que o Cebraspe conta -, senao o bruto."""
        if self.numeros.nota.itens:
            return self.numeros.nota.porcentagem
        return self.numeros.bruto.porcentagem

    @property
    def amostra(self) -> int:
        """As respostas que sustentam a `medida`."""
        if self.numeros.nota.itens:
            return self.numeros.nota.itens
        return self.numeros.bruto.medidas

    @property
    def cor(self) -> str:
        """"sem_dado", "pouca_amostra", "verde", "amarelo" ou "vermelho"."""
        if not self.numeros.feitas:
            return "sem_dado"
        if self.amostra < self.minimo or self.medida is None:
            return "pouca_amostra"
        if self.medida >= self.meta_em_porcentagem:
            return "verde"
        if self.medida >= self.meta_em_porcentagem - FAIXA_DO_AMARELO:
            return "amarelo"
        return "vermelho"


@dataclass
class Rendimento:
    linhas: list[LinhaDoRendimento] = field(default_factory=list)
    primeiro: list = field(default_factory=list)       # LinhaDaTela do desempenho
    minimo_do_assunto: int = 0


def montar(plano=None, referencia: datetime | None = None) -> Rendimento:
    """As linhas na ordem do peso (mais questoes primeiro) e o Estude primeiro.

    Materia com questao respondida e fora do edital do cronograma entra no fim,
    sem meta: sumir com ela esconderia o que eu fiz.
    """
    plano = plano or plano_de_estudo.carregar()
    minimos = regua.carregar()
    minimo = minimos.do_nivel("materia")
    numeros = metricas.rendimento_por_materia(referencia)
    nomes = [m.nome for m in plano.materias]

    linhas = {m.nome: LinhaDoRendimento(m.nome, m.questoes, m.meta, minimo)
              for m in plano.materias}
    sobra = []
    for materia, dela in numeros.items():
        nome = _achar(materia, nomes)
        if nome is None:
            sobra.append(LinhaDoRendimento(materia, 0, 0, minimo, dela))
        else:
            linhas[nome].numeros = dela

    ordenadas = sorted(linhas.values(), key=lambda l: (-l.questoes_na_prova, l.materia))
    return Rendimento(
        linhas=ordenadas + sorted(sobra, key=lambda l: l.materia),
        primeiro=estude_primeiro(minimos),
        minimo_do_assunto=minimos.do_nivel("assunto"),
    )


def estude_primeiro(minimos=None, quantos: int = QUANTOS_PRIMEIRO) -> list:
    """Os assuntos de pior acerto, so os com amostra suficiente (a regua do
    nivel "assunto"): abaixo dela a porcentagem e sorteio e nao ordena nada."""
    minimos = minimos or regua.carregar()
    candidatos = [
        linha for linha in desempenho_por_conteudo.tela(desempenho_por_conteudo.SEMPRE)
        if linha.nivel == "assunto" and linha.estado.suficiente
        and linha.estado.porcentagem is not None
    ]
    candidatos.sort(key=lambda l: (l.estado.porcentagem, -l.estado.respostas))
    return candidatos[:quantos]

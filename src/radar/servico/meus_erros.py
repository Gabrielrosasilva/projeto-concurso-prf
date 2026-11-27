"""Revisao > Meus erros (PRF-64): os erros entram sozinhos.

O Caderno de erros era manual (clicar em "Anotar erro") e por isso nunca foi
usado. Aqui toda questao REAL que eu errei na ULTIMA vez que respondi aparece
sozinha (`simulado.questoes_erradas`: o chute errado e o em branco ficam
fora, PRF-28; a anulada tambem), agrupada por materia e assunto, com o que
marquei, o gabarito, a explicacao e a ficha do tema para estudar.

Sair da lista nao precisa de botao: refiz e acertei, a ultima resposta e um
acerto e ela some; errei de novo, ela fica. O motivo do erro e opcional, de
um clique (os botoes da decisao 174), gravado na resposta.

A questao gerada por IA vem num bloco separado e nunca entra na conta das
reais (regra 1 do CLAUDE.md).
"""
from collections import defaultdict
from dataclasses import dataclass, field

from radar import conteudos as arvore
from radar import fichas as fichas_puras
from radar.db import criar_tabelas, sessao
from radar.models import QuestaoDeProva, QuestaoGerada
from radar.questoes_certo_errado import EM_BRANCO
from radar.servico import explicacoes, metricas
from radar.servico import fichas as servico_fichas
from radar.servico import simulado
from radar.servico.desempenho_por_conteudo import nos_das_questoes

SEM_ASSUNTO = "sem assunto na árvore"


@dataclass
class Ficha:
    ident: str
    tema: str


@dataclass
class Erro:
    item: simulado.ItemDeRevisao
    painel: object = None               # explicacoes.Painel


@dataclass
class Assunto:
    nome: str
    caminho: str | None
    ficha: Ficha | None = None
    erros: list[Erro] = field(default_factory=list)


@dataclass
class Materia:
    nome: str
    assuntos: list[Assunto] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(len(a.erros) for a in self.assuntos)

    @property
    def ids(self) -> list[int]:
        return [e.item.questao_id for a in self.assuntos for e in a.erros]


@dataclass
class MeusErros:
    materias: list[Materia] = field(default_factory=list)
    geradas: list[simulado.ItemDeRevisao] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(m.total for m in self.materias)


def ficha_do_no(caminho: str | None, escritas) -> Ficha | None:
    """A ficha que cobre o no: a de escopo mais justo que o contem. Sem
    nenhuma, a primeira que cobre um no DENTRO dele (a ficha de um
    subassunto serve para o erro marcado no assunto)."""
    if not caminho:
        return None
    melhor, tamanho = None, -1
    for escrita in escritas:
        for no in escrita.nos:
            if fichas_puras.dentro_de([no])(caminho) and len(no) > tamanho:
                melhor, tamanho = escrita, len(no)
    if melhor is None:
        prefixo = caminho + arvore.SEPARADOR
        melhor = next((e for e in escritas if any(n.startswith(prefixo) for n in e.nos)), None)
    return Ficha(melhor.id, melhor.tema) if melhor else None


def _assunto_do_no(caminho: str | None) -> tuple[str, str | None]:
    """(nome, caminho) do ASSUNTO de um no: o segundo nivel da arvore."""
    if not caminho:
        return SEM_ASSUNTO, None
    partes = arvore.partes(caminho)
    if len(partes) < 2:
        return SEM_ASSUNTO, None
    return partes[1], arvore.SEPARADOR.join(partes[:2])


def montar(com_painel: bool = True) -> MeusErros:
    """Os erros das reais por materia (mais erros primeiro) e assunto, e o
    bloco das geradas. Dentro do assunto, o erro mais recente primeiro."""
    ids = simulado.questoes_erradas()
    nome_da_materia = metricas._nome_da_materia()
    das_geradas = [r for r in metricas.ultimas_das_geradas().values()
                   if r.acertou is False and not r.chutou
                   and r.escolhida not in (None, EM_BRANCO)]
    criar_tabelas()
    with sessao() as s:
        ultimas = metricas.ultimas_respostas_reais(s)
        pares = [(ultimas[qid], s.get(QuestaoDeProva, qid)) for qid in ids if qid in ultimas]
        geradas = [(r, s.get(QuestaoGerada, r.questao_id)) for r in das_geradas]

    nos = nos_das_questoes() if pares else {}
    escritas = servico_fichas.carregar() if pares else []
    por_materia: dict[str, dict] = defaultdict(dict)
    pares.sort(key=lambda par: par[0].respondida_em or par[0].id, reverse=True)
    for resposta, questao in pares:
        if questao is None:
            continue
        item = simulado.item_da_revisao(resposta, questao, nos)
        nome, caminho = _assunto_do_no(item.conteudo)
        assuntos = por_materia[nome_da_materia(questao.materia)]
        if nome not in assuntos:
            assuntos[nome] = Assunto(nome, caminho, ficha_do_no(caminho or item.conteudo, escritas))
        assuntos[nome].erros.append(
            Erro(item, explicacoes.painel(questao) if com_painel else None))

    materias = [Materia(nome, sorted(assuntos.values(), key=lambda a: -len(a.erros)))
                for nome, assuntos in por_materia.items()]
    materias.sort(key=lambda m: (-m.total, m.nome))
    return MeusErros(
        materias=materias,
        geradas=[simulado.item_da_revisao(r, q, {}) for r, q in geradas if q is not None],
    )


def criar_rodada(materia: str | None = None) -> simulado.Simulado | None:
    """O "Refazer": uma rodada com os erros de uma materia, ou todos."""
    erros = montar(com_painel=False)
    ids = [qid for m in erros.materias if materia in (None, m.nome) for qid in m.ids]
    if not ids:
        return None
    return simulado.criar_simulado_de_erros(quantidade=None, ids=ids)

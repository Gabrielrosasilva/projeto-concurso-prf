# Estado - 24/11/2026

Etapa 0 (isolamento) feita, esperando o aval do Gabriel. A Etapa 1 nao comecou.

## O que roda
- `radar subir` na 8002, com "MODO PRF" e titulo "PRF · ...". Config em `prf/config/` (pelo `.env`), sem Telegram.
- Diario zerado (decisao PRF-4). O treino livre (Estudar > Simulado) cria, responde e encerra.

## Quebrado ate existir `prf/config/cronograma.yml`
- A Hoje e a Semanas avisam "falta o arquivo do cronograma".
- Erro 500 em Meu foco (`/`), Fichas, Gerar questoes, Analises > Conferencia e Analises > Desempenho: o cronograma e lido em ~40 lugares que nao tratam a falta dele.

## Ainda da PMSC/PP na tela (so listado; nada apagado)
- Sem `alvo.yml`, o `alvo.py` volta ao padrao da PP: FEPESE, "Policia Penal SC", "2013 e 2019".
- Aba Redacao (AOCP/PMSC), Simulado PMSC, "a prova da PMSC e de multipla escolha".
- O radar de concursos de SC: Concursos, Previsao, Mais.
- A arvore, as questoes, os macetes e as fichas herdados (Etapas 1 e 3).

## Fora do git por enquanto (sem commit, e sem estar no .gitignore)
- `PRF/` menos `PRF/config/`: o script e o que ele coletou (~7 mil links do Qconcursos). Decide-se na Etapa 2.
- `PEDIDO_PRF.md` e `PRIMEIRO_PEDIDO.md` da raiz (rascunhos; o pedido fica em `entrada/`).

## Testes
- Tocados: 264 passam. 2 do `test_redacao.py` falham porque leem `pmsc/config/`, pasta que nao existe nesta copia (nao e efeito da Etapa 0).

## Proximo
- Decidir a lista acima e o cronograma; depois, a Etapa 1 (edital de 2021).

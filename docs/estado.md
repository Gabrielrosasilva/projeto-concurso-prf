# Estado - 24/11/2026

Etapas 0 e 1 feitas; a 1 espera o aval do Gabriel. A Etapa 2 nao comecou.

## O que roda
- `radar subir` na 8002, com "MODO PRF". Config em `PRF/config/` (pelo `.env`), sem Telegram.
- Diario zerado (PRF-4). O treino livre (Estudar > Simulado) cria, responde e encerra.
- A arvore de conteudos e a do edital de 2021: 273 nos (PRF-6), refeita com `radar conteudos --semear --edital "Edital 2021.pdf"`.

## O edital e a prioridade
- `docs/edital.md`: o edital lido, com o link. `docs/prioridade.md`: a ordem das materias, com os itens das provas de 2021 e 2019 (PRF-7).
- Os pesos por materia so entram no radar (prioridade das fichas, compilado) pelo cronograma, na Etapa 5.

## Quebrado ate existir `PRF/config/cronograma.yml`
- A Hoje e a Semanas avisam "falta o arquivo do cronograma".
- Erro 500 em Meu foco (`/`), Fichas, Gerar questoes, Analises > Conferencia e > Desempenho.

## Ainda da PMSC/PP (so listado; nada apagado)
- Sem `alvo.yml`, o `alvo.py` volta ao padrao da PP: FEPESE, "Policia Penal SC", "2013 e 2019".
- Aba Redacao (AOCP/PMSC), Simulado PMSC, "a prova da PMSC e de multipla escolha"; o radar de concursos de SC.
- As questoes, classificacoes, fichas, geradas e macetes herdados: apontam para nos que sairam (Etapa 3).

## Fora do git por enquanto
- `PRF/` menos `PRF/config/`: o script e o que ele coletou (Etapa 2). Os rascunhos `PEDIDO_PRF.md` e `PRIMEIRO_PEDIDO.md` da raiz.

## Testes (leem um espelho do `data/` com a arvore antiga fixa, PRF-9)
- Etapa 1: os 76 arquivos que leem o cronograma ou a arvore - 1.695 passam, 4 falham desde a copia (leem `pmsc/config/`, que nao existe aqui): 2 do `test_redacao`, 1 do `test_simulado_da_semana`, 1 do `test_fichas`. A suite inteira nao rodou.

## Proximo
- O aval da Etapa 1 e as decisoes pendentes; depois, a Etapa 2 (a pasta `PRF/`).

# Estado - 24/11/2026

Etapas 0, 1 e 2 feitas; a 2 espera o aval do Gabriel. A Etapa 3 nao comecou.

## O que roda
- `radar subir` na 8002, com "MODO PRF". Config em `PRF/config/` (pelo `.env`), sem Telegram.
- Diario zerado (PRF-4). A arvore e a do edital de 2021: 273 nos (PRF-6).
- O alvo e a PRF (PRF-11). Entraram 5.831 questoes do Cebraspe: 237 do alvo, das provas de 2019 e 2021, com materia, e 5.594 complementares sem materia (PRF-12).
- Documentos: `docs/edital.md` (o edital lido), `docs/prioridade.md` (a ordem das materias), `docs/script_prf.md` (o script de PRF/ e o que se usa de novo).

## Falta para usar as questoes
- Classificar nos nos da arvore: a Incidencia mostra 0 por conteudo.
- O Certo/Errado como formato principal, com nota liquida e chute: a Etapa 4.

## Quebrado ate existir `PRF/config/cronograma.yml`
- Erro 500 em Meu foco (`/`), Fichas, Gerar questoes, Analises > Conferencia e > Desempenho. A Hoje e a Semanas avisam.

## Ainda da PMSC/PP (so listado; nada apagado)
- Aba Redacao (AOCP/PMSC), Simulado PMSC, "a prova da PMSC e de multipla escolha"; o radar de concursos de SC.
- As 16.317 questoes herdadas, as classificacoes, fichas e macetes: Etapa 3.

## Fora do git
- `PRF/` menos `PRF/config/` (PRF-13), os rascunhos da raiz, `data/provas/` (os PDFs importados).

## Testes (leem um espelho do `data/` com a arvore antiga fixa, PRF-9)
- Etapa 2: os 10 arquivos tocados - 235 passam; os 2 do `test_redacao` que leem `pmsc/config/` falham desde a copia.

## Proximo
- O aval da Etapa 2 e as decisoes pendentes; depois, a Etapa 3 (as questoes herdadas).

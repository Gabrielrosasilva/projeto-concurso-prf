# Estado - 25/11/2026

Etapas 0, 1 e 2 feitas, e a classificacao das questoes do Cebraspe (pedida
depois da 2); tudo espera o aval do Gabriel. A Etapa 3 nao comecou.

## O que roda
- `radar subir` na 8002, com "MODO PRF". Config em `PRF/config/` (pelo `.env`), sem Telegram.
- Diario zerado (PRF-4). Arvore do edital de 2021 + os 22 capitulos do CTB + 237 nos da classificacao: 532 (PRF-6, PRF-17).
- Questoes do Cebraspe da PRF/: 237 do alvo (2019 e 2021) e 1.693 complementares, todas com materia (PRF-16).
- Classificadas nos nos, com releitura as cegas (PRF-19): alvo 223 conferidas, 14 pendentes; complementar 1.171 de Certo/Errado, 1.066 conferidas, 105 pendentes. A Incidencia ja mostra por no.
- Documentos: `docs/edital.md`, `docs/prioridade.md`, `docs/script_prf.md`, `docs/dados_cronograma.md` (para a Etapa 5).

## Para o Gabriel conferir
- As pendentes (Analises > Conferencia, quando o cronograma existir): 14 do alvo e 105 do complementar.
- Dois gabaritos que o agente achou suspeitos (complementar, Direito Penal, do Qconcursos herdado): 2023-q2215611 e 2023-q2048199. Nada foi trocado.
- `data/classificacoes.json` (versionado, repositorio publico) guarda o `trecho` de cada questao: trecho curto de prova de terceiros (regra 5).

## Falta
- As 363 de multipla escolha do complementar ficam sem no: o acervo complementar so aceita prova validada (`radar complementar`).
- O Certo/Errado como formato principal, com nota liquida e chute: a Etapa 4.

## Quebrado ate existir `PRF/config/cronograma.yml`
- Erro 500 em Meu foco (`/`), Fichas, Gerar questoes, Analises > Conferencia e > Desempenho.

## Ainda da PMSC/PP (so listado; nada apagado)
- Aba Redacao (AOCP/PMSC), Simulado PMSC; o radar de concursos de SC; as 16.317 questoes herdadas, classificacoes, fichas e macetes: Etapa 3.

## Testes (leem um espelho do `data/` com a arvore antiga fixa, PRF-9)
- Os 16 arquivos que tocam o leitor e as provas: 331 passam.

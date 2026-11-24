# Decisoes - Radar PRF

Uma linha cada. As da PP (so numero) e da PMSC (PMSC-n) citadas no codigo
ficaram registradas nos projetos de origem.

- **PRF-1** (24/11/2026) Isolamento: porta 8002 (8000 e da PP, 8001 da PMSC), faixa "MODO PRF" e titulo da aba comecando com "PRF"; `radar agendar` recusa (`automacao.COPIA_PRF`), porque as tarefas e os atalhos do Windows tem os nomes da PP. A cor da faixa ainda e a da PMSC.
- **PRF-2** (24/11/2026) A config mora em `prf/config/` (o `.env` aponta `RADAR_CONFIG_DIR`), copia de `fontes/config_pmsc/` sem `alvo.yml`, `cronograma.yml`, `redacao.yml` e `acompanhamentos.yml` (so carreiras de SC, e dependia do alvo). O `config/` da raiz fica para os testes. No Windows `prf/` e `PRF/` sao a mesma pasta: a config mora em `PRF/config/`, ao lado dos PDFs e do script, e e assim que o git a mostra.
- **PRF-3** (24/11/2026) Leis de SC (ALESC) fora do `prf/config/leis.yml` e do `textos_de_lei.yml`; as federais ficam, inclusive o CPM e a Lei 14.751 (so da PM: a decidir).
- **PRF-4** (24/11/2026) Diario zerado no banco e nos JSON (simulados e respostas, registros e faixas do dia, caderno de erros, estudo extra, notas da semana, redacoes); a copia de antes esta em `data/copias/antes-do-prf/`.
- **PRF-5** (24/11/2026) O repositorio no GitHub e publico: os trechos de prova, gabaritos e editais de terceiros de `tests/fixtures/` ficam fora do git (regra 5); os testes que os leem so rodam nesta maquina.

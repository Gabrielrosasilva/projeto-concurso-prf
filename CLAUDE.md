# CLAUDE.md - Radar PRF

Lido em toda conversa. **Fica curto (no maximo ~150 linhas).** Historico vai
para `docs/historico.md`; decisao, uma linha cada, em `docs/decisoes.md`; o
estado de agora em `docs/estado.md` (no maximo 30 linhas). So leia os docs
quando a tarefa pedir. O pedido original esta em `entrada/PEDIDO_PRF.md` (nao
se edita).

## O que e

Sistema **pessoal** (um usuario, sem login, nao vai para producao) para estudar
para a **PRF - Policial Rodoviario Federal**. O codigo veio do radar da PMSC em
24/11/2026 (o layout, a tela Hoje, o treino, o simulado e o caderno de erros
ficam como estao: so se adaptam a PRF). Prioridade: funcionar e ser facil de
manter sozinho.

## Quem mantem

Analista de infraestrutura/SRE (Linux, Docker, K8s, Terraform, CI, AWS, OCI,
shell, SQL, Java). **Nao tem pratica em Python** - e a linguagem daqui para
aprender. Por isso: o jeito simples e legivel, a biblioteca padrao quando a
diferenca for pequena, nada de abstracao sem necessidade concreta, e comentario
explica **por que**. Codigo, commits, telas e nomes: em **portugues**.

## O alvo

- Edital novo previsto para 2027, ainda nao saiu. **Ate la vale o de 2021**
  (o PDF esta nesta pasta). Banca, materias, pesos e numero de itens: **so do
  edital lido** (`docs/edital.md`, com o link), nunca de memoria. A ordem de
  prioridade das materias, com os itens de cada prova: `docs/prioridade.md`.
- **Formato principal: Certo/Errado do Cebraspe.** Um item errado anula um
  certo; em branco nao conta. O radar mede assim (nota liquida) e mostra o
  acerto bruto ao lado, nunca no lugar.
- Questao de multipla escolha de outra banca **treina o conteudo**, mas nao
  mede o padrao do Cebraspe: o numero dela aparece separado.

## Regras que nao se quebram

1. **Questao gerada por IA treina, nunca mede.** Mora em `questoes_geradas`,
   e os dois acertos nunca sao somados.
2. **Dado vindo de IA so com procedencia** (modelo e data). Nunca inventar URL,
   seletor de HTML, artigo de lei nem gabarito: se nao souber, diga e peca.
3. **Lei pelo texto vigente oficial**, em `leis/` (o Planalto bloqueia robo:
   Camara ou LexML). Questao com lei que mudou depois da prova leva aviso ou
   sai do treino.
4. `robots.txt` e os termos de cada site, sem excecao. **Guarde sempre o link original.**
5. **PDF de prova, texto de prova de terceiros e o banco ficam fora do git.**
6. Teste com dado fixo em arquivo: nunca internet, nunca a data de hoje, nunca
   dependente do Windows.

## Mapa do codigo (`src/radar/`)

So abra o arquivo que a tarefa pede.
- `cli.py`: os comandos `radar ...` (typer). `web/app.py`: as telas (FastAPI);
  `web/templates/` (Jinja) e `web/static/design.css` (o design system: as
  cores e os selos so la).
- `config.py`: le `RADAR_CONFIG_DIR` (o `.env` aponta para `prf/config/`).
  `automacao.py`: a porta (`PORTA_PADRAO`).
- `db.py`, `models.py`, `migracoes.py`: o banco SQLite (`data/radar.db`).
  **Mudanca de estrutura do banco vira passo novo em `migracoes.py`.**
- `servico/` (um arquivo por assunto; escreva `servico.funcao(...)`):
  - `metricas.py`: **toda contagem de questao, acerto e erro passa por aqui**;
    tela nenhuma refaz conta, template nenhum soma. A nota liquida
    (`NotaLiquida`) e o chute fora do acerto acumulado (`conta_no_acerto`).
  - `evidencia.py`: alvo, complementar e fora (uma regra, nunca somados).
  - `composicao.py`: o que vai numa rodada que mede (so questao real).
  - `simulado.py`, `simulado_da_semana.py`, `estudo.py` (a fila de revisao,
    uma so), `erros.py` (o motivo do erro), `cronograma.py` (a tela Hoje),
    `fichas.py`, `certo_errado.py` (a regra do chute, o Certo x Errado),
    `desempenho_por_conteudo.py`.
- `amostra.py` + `config/amostra.yml`: **todo minimo de amostra sai dali**.
- `origem.py`: os selos (🟢 oficial, 🔵 acervo, 🟡 automatico, 🟣 IA); o
  servico grava a origem, o template so desenha.
- `conteudos.py` + `data/conteudos.json`: a arvore (materia > assunto >
  subassunto); tudo que aponta para conteudo usa o caminho do no. Nasce do
  edital pelo `edital_cebraspe.py` (`radar conteudos --semear --edital`).
- `fichas.py`, `artigos.py`, `traducao.py`, `glossario.py`: a ficha, o resumo
  e o "Traduz pra mim" de cada tema (`data/fichas.json`).
- Leitores de prova: `questoes_cebraspe.py`, `questoes_certo_errado.py` (o
  caderno de Certo/Errado do Cebraspe, direto do PDF: `ler_caderno`),
  `gabarito.py`, `destaques.py` (sublinhado e negrito do caderno). As provas
  da `PRF/` entram pela lista `PRF/config/provas_de_outras_bancas.yml`; o que
  o script da `PRF/` faz esta em `docs/script_prf.md`.
- `cache.py`: conta pesada repetida numa tela.
- A questao e reconhecida pela CHAVE (enunciado + alternativas), nunca so pela
  impressao do enunciado.

## De onde vem as questoes

- `PRF/`: PDFs do Cebraspe e o script (`PRF/RELATORIO.md` e grande: leia por
  partes, so o que a tarefa pedir).
- `fontes/radar_pmsc.db`: **copia intocada** do banco da PMSC (16.317 questoes;
  ~780 do Cebraspe). So se le. `fontes/leis/`: leis copiadas da PMSC.
  `fontes/config_pmsc/`: a config da PMSC, so de referencia.
- **Nunca abra, leia, escreva nem rode nada em
  `C:\Projeto concurso claude\Projeto-Concurso` (PP) nem em
  `C:\Projeto concurso claude\Projeto-Concurso-PMSC`.** O que veio de la esta
  em `fontes/`. Se uma tarefa parecer pedir essas pastas, pare e pergunte.

## Como trabalhar

- **Antes do primeiro comando de cada conversa, `git remote -v`**: tem que
  terminar em `projeto-concurso-prf.git`. Se nao, pare e avise.
- Branch `main`, sem PR. **Commit e push ao fim de cada etapa.**
- **Uma etapa por conversa, e cada uma espera o aval do Gabriel.** Ao fim:
  `docs/estado.md` e `docs/decisoes.md` atualizados.
- Antes de dizer que terminou: os testes tocados passando (`pytest -q
  tests/...`) **e** o comando afetado rodado de verdade. A suite inteira (~35
  min) so quando o Gabriel pedir.
- **Porta 8002** (a 8000 e da PP e a 8001 da PMSC: nao mexa nelas).
- **Nunca rode `radar agendar`**: os nomes das tarefas do Windows sao os da PP.
- Nunca `git add .` sem olhar o `git status`.
- Nao adicione dependencia sem justificar em uma linha. Nao refatore o que nao
  faz parte do pedido.

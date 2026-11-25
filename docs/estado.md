# Estado - 25/11/2026

Etapas 0 a 4, a classificacao do Cebraspe e as 6 provas do levantamento (PRF-26) feitas; tudo espera o aval do Gabriel. A Etapa 5 nao comecou.

## O que roda
- `radar subir` na 8002, com "MODO PRF". Config em `PRF/config/` (pelo `.env`), sem Telegram.
- Diario zerado (PRF-4). Arvore do edital de 2021 + os 22 capitulos do CTB + 237 nos da classificacao: 532 (PRF-6, PRF-17).
- Questoes: 9.501. Da PRF/: 245 do alvo (com as 8 de espanhol, PRF-24) e 1.693 complementares (PRF-16, PRF-19); do levantamento do Cebraspe, 97 complementares de Fisica, Geopolitica e Espanhol (PRF-26). Herdadas da PMSC: ficaram 7.466 de 16.317 (PRF-21, PRF-23): 476 do Cebraspe (complementar) e 6.990 de outras bancas (fora: treinam, nao medem).
- Geradas por IA: 1.404 (as da PMSC num no da PRF). Fichas 103, macetes 45, explicacoes 512, glossario 462 (PRF-22).
- Certo/Errado (PRF-28, `docs/certo_errado.md`): em branco, nota liquida na rodada, chute fora do desempenho por assunto e (errado) do caderno de erros; Analises > Certo/Errado e `radar chute`. Os 58 cadernos C/E do Cebraspe treinam e medem: estoque de 1.180 complementares + 210 do alvo.
- Documentos: `docs/edital.md`, `docs/prioridade.md`, `docs/script_prf.md`, `docs/certo_errado.md`, `docs/dados_cronograma.md` e `docs/comparativo_pmsc_prf.md` (os dois para a Etapa 5).

## Para o Gabriel conferir
- As pendentes (Analises > Conferencia, quando o cronograma existir): 14 do alvo, 111 do complementar (6 da PRF-26: 3 da curva com atrito e 3 fora do treino pelo gabarito) e ~400 herdadas que ja eram pendentes na PMSC (so a materia). As 1.000 do mapa foram resolvidas (PRF-23).
- Dois gabaritos suspeitos (complementar, Direito Penal, do Qconcursos herdado; continuam no banco): 2023-q2215611 e 2023-q2048199. Nada foi trocado.
- `data/classificacoes.json` (versionado, repositorio publico) guarda o `trecho` de cada questao: trecho curto de prova de terceiros (regra 5).

## Falta
- As 363 de multipla escolha do complementar e 1.128 herdadas ficam sem no (so a materia): podem passar pelo mesmo processo da PRF-23.
- Redacao Cebraspe e Simulado PMSC: pendencia em `docs/dados_cronograma.md`.
- 6 cadernos antigos de Certo/Errado sem recuo podem ter o texto-base grudado no item (PRF-26): reler com o leitor novo, com o seu aval. Agora eles treinam e medem.
- A multipla escolha do Cebraspe (761) segue fora do treino que mede (so o C/E entrou, PRF-28).

## Quebrado ate existir `PRF/config/cronograma.yml`: erro 500 em Meu foco (`/`), Fichas, Gerar questoes, Analises > Conferencia e > Desempenho.

## Ainda da PMSC/PP
- Aba Redacao (AOCP), Simulado PMSC e o cartao "Sobre o chute" dos Macetes (letras A-E). Concursos e Acompanhando vazias (PRF-22).

## Testes
- Leem um espelho do `data/` (PRF-9). Os 24 arquivos que o leem passam, 2 pulados; os da PRF-28 em `tests/test_certo_errado_prf.py`. Falha desde antes da PRF-28: `test_simulado_da_semana::test_a_tela_do_dia_real_nao_manda_ao_qconcursos` (procura `pmsc/config/cronograma.yml`).

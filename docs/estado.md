# Estado - 25/11/2026

Etapas 0 a 4, a classificacao do Cebraspe, os levantamentos 1 e 2 do Cebraspe (PRF-26, PRF-30, PRF-32) e a explicacao com a Revisao do simulado (PRF-33) feitos; tudo espera o aval do Gabriel. A Etapa 5 nao comecou.

## O que roda
- `radar subir` na 8002, com "MODO PRF". Config em `PRF/config/` (pelo `.env`), sem Telegram.
- Diario zerado (PRF-4). Arvore do edital de 2021 + os 22 capitulos do CTB + os nos da classificacao: 638 (PRF-6, PRF-17, PRF-32).
- Questoes: 10.259. Da PRF/: 245 do alvo (com as 8 de espanhol, PRF-24) e 1.693 complementares (PRF-16, PRF-19); dos levantamentos do Cebraspe, 97 (PRF-26) e 758 (PRF-32, provas de policia) complementares. Herdadas da PMSC: ficaram 7.466 de 16.317 (PRF-21, PRF-23): 476 do Cebraspe (complementar) e 6.990 de outras bancas (fora: treinam, nao medem).
- Geradas por IA: 1.404 (as da PMSC num no da PRF). Fichas 103, macetes 45, glossario 462 (PRF-22). Explicacoes 734: 512 da PMSC e 222 das C/E do alvo, em partes (PRF-33): o painel abre na questao corrigida do treino, e no fim o relatorio leva a `/simulado/{id}/revisao` (uma por vez: errei, chutei, em branco, acertei).
- Certo/Errado (PRF-28, `docs/certo_errado.md`): em branco, nota liquida na rodada, chute fora do desempenho por assunto e (errado) do caderno de erros; Analises > Certo/Errado e `radar chute`. Os 79 cadernos C/E do Cebraspe treinam e medem: 2.018 itens unicos (alvo + complementar).
- Documentos: `docs/edital.md`, `docs/prioridade.md`, `docs/script_prf.md`, `docs/certo_errado.md`, `docs/dados_cronograma.md` e `docs/comparativo_pmsc_prf.md` (os dois para a Etapa 5).

## Para o Gabriel conferir
- As pendentes (Analises > Conferencia, quando o cronograma existir): 14 do alvo, 124 do complementar (6 da PRF-26; 13 da PRF-32: 10 divergencias, o CPP art. 61 e 2 de lei mudada); 3 do alvo de lei mudada (PRF-33: CP art. 311, CTB art. 20 XII, tolerancia por eixo) e ~400 herdadas que ja eram pendentes na PMSC (so a materia). As 1.000 do mapa foram resolvidas (PRF-23).
- Dois gabaritos suspeitos (complementar, Direito Penal, do Qconcursos herdado; continuam no banco): 2023-q2215611 e 2023-q2048199. Nada foi trocado.
- `data/classificacoes.json` (versionado, repositorio publico) guarda o `trecho` de cada questao: trecho curto de prova de terceiros (regra 5).

## Falta
- Leitor de C/E (PRF-32), para reler com o seu aval: o comando sem "julgue" e o titulo de secao grudam no item de antes (6 itens novos; a PM/AL 2017 q100-105 ficou fora); lixo da capa no texto-base (CBM/AL 2021, MJSP, e antigos: PC/AL e PM/AL 2021, SERIS, SESAU); os itens de lingua dos 4 cadernos de duas linguas (25) ficaram fora; a Petrobras 2023 (cabecalho de 14 caracteres). Os 14 de multipla escolha do levantamento 2 so baixados.
- Explicacao (PRF-33): gerar o resto (`--quais todas`, comecando pelo Transito) e a da multipla escolha. Pendentes: a IA gerar questao para assunto com menos de 50 (depois da Etapa 5); a analise dos aprovados da PRF 2021 na objetiva e na discursiva (editais 11 e 12 do Cebraspe, sem nome), comparada com a de 2019, e o padrao de resposta da discursiva; num doc e num cartao das Analises; antes ou no comeco da Etapa 5.
- Sem no (so a materia): 363 de multipla escolha do complementar e 1.128 herdadas (processo da PRF-23). A multipla escolha do Cebraspe (761) segue fora do treino que mede (PRF-28).
- 6 cadernos antigos de C/E sem recuo (PRF-26): reler, com o seu aval; o leitor de hoje piora a PF 2018 (PRF-32). Transito segue com 137 C/E e capitulos do CTB zerados. Redacao Cebraspe e Simulado PMSC: `docs/dados_cronograma.md`.

## Quebrado ate existir `PRF/config/cronograma.yml`: erro 500 em Meu foco (`/`), Fichas, Gerar questoes, Analises > Conferencia e > Desempenho.

## Ainda da PMSC/PP
- Aba Redacao (AOCP), Simulado PMSC e o cartao "Sobre o chute" dos Macetes (letras A-E). Concursos e Acompanhando vazias (PRF-22).

## Testes
- Leem um espelho do `data/` (PRF-9). Os 24 arquivos que o leem passam, 2 pulados; os da PRF-28 em `tests/test_certo_errado_prf.py`. Falham desde antes (procuram `pmsc/config/`): `test_simulado_da_semana::test_a_tela_do_dia_real_nao_manda_ao_qconcursos` e dois do `test_redacao` (a faixa de redacao e os modelos reais).

# Estado - 26/11/2026

Etapas 0 a 5 feitas, com a classificacao do Cebraspe, os levantamentos 1 e 2 (PRF-26, PRF-30, PRF-32), a explicacao com a Revisao do simulado (PRF-33), a analise dos aprovados (PRF-34) e o cronograma em dois ciclos (PRF-38); tudo espera o aval do Gabriel.

## O que roda
- `radar subir` na 8002, com "MODO PRF". Config em `PRF/config/` (pelo `.env`), sem Telegram.
- Diario zerado (PRF-4). Arvore do edital de 2021 + os 22 capitulos do CTB + os nos da classificacao: 638 (PRF-6, PRF-17, PRF-32).
- Questoes: 10.259. Da PRF/: 245 do alvo (com as 8 de espanhol, PRF-24) e 1.693 complementares (PRF-16, PRF-19); dos levantamentos do Cebraspe, 97 (PRF-26) e 758 (PRF-32, provas de policia) complementares. Herdadas da PMSC: ficaram 7.466 de 16.317 (PRF-21, PRF-23): 476 do Cebraspe (complementar) e 6.990 de outras bancas (fora: treinam, nao medem).
- Geradas por IA: 1.404, todas de multipla escolha (as da PMSC num no da PRF). Fichas 160: 103 herdadas (PRF-22) e 57 do Ciclo 1 antigo (PRF-36); macetes 45, glossario 462. Explicacoes 734 (PRF-33).
- Certo/Errado (PRF-28, `docs/certo_errado.md`): em branco, nota liquida, chute fora do desempenho por assunto; Analises > Certo/Errado e `radar chute`. 2.018 itens C/E unicos (alvo + complementar).
- Cronograma (PRF-35, PRF-38, `docs/metodo.md`): 16 semanas, 04/01 a 24/04/2027, em `PRF/config/cronograma.yml`, gerado por `PRF/cronograma/gerar_cronograma.py` (como rodar, no topo). Ciclo 1 (ate 27/02): Transito, Portugues e os Direitos; Ciclo 2: Espanhol, Informatica, Raciocinio, Fisica, Etica e Geopolitica, com 15 itens de manutencao do Ciclo 1 toda manha. Diagnostico de 120 em 09/01, fechamento em 24/04.
- Documentos: `docs/edital.md`, `docs/prioridade.md`, `docs/script_prf.md`, `docs/certo_errado.md`, `docs/dados_cronograma.md`, `docs/comparativo_pmsc_prf.md`, `docs/aprovados_prf.md`, `docs/metodo.md` e `docs/resolucoes_contran.md`. Redacao no criterio do Cebraspe (PRF-37), 10 temas (PRF-38) em `PRF/config/redacao.yml`.

## Para o Gabriel conferir
- O cronograma novo na tela Hoje (`/hoje?data=2027-01-04`, `2027-03-01`) e o `docs/metodo.md`; a aba Redacao: os 10 temas, os modelos e a NC estimada pelos conceitos (PRF-37, PRF-38).
- As 57 fichas (Hoje > Fichas, 🟣 nao conferida; `radar fichas --conferir <tema>`) e `docs/resolucoes_contran.md` (11 das 15 resolucoes revistas foram revogadas).
- As pendentes (Analises > Conferencia): 14 do alvo, 124 do complementar; 3 do alvo de lei mudada (PRF-33) e ~400 herdadas que ja eram pendentes na PMSC (so a materia).
- Dois gabaritos suspeitos (complementar, Penal, do Qconcursos herdado: 2023-q2215611 e 2023-q2048199; nada trocado). `data/classificacoes.json` (versionado, publico) guarda o `trecho` curto de cada questao (regra 5).

## Falta
- Antes de 04/01: as fichas das 55 aulas do Ciclo 1 sem ficha (sem ela, o simulado de sabado nao acha as questoes pelos nos), com o Resumo e "o que mais caiu e como o Cebraspe cobra" (pedido de 26/11). As 57 do Ciclo 2, antes de 01/03.
- Pendente cobrado: a IA gerar C/E para os temas com poucos itens (40 dos 60 temas do Ciclo 1 antigo; o pior e o Transito). Duas anotacoes do CONTRAN velhas (pelicula de 28%, medidor estatico e movel).
- Leitor de C/E (PRF-32), para reler com o seu aval: comando sem "julgue", lixo da capa, os 25 itens de lingua dos cadernos de duas linguas, a Petrobras 2023, os 6 cadernos antigos sem recuo. Explicacao: o resto (`--quais todas`) e a da multipla escolha.
- Sem no (so a materia): 363 de multipla escolha do complementar e 1.128 herdadas.

## Ainda da PMSC/PP
- O cartao "Sobre o chute" dos Macetes (letras A-E) e a frase da tela Certo ou Errado ("a prova da PMSC e de multipla escolha": nada ali e gravado). Concursos e Acompanhando vazias (PRF-22).

## Testes
- Leem um espelho do `data/` (PRF-9); `tests/test_cronograma_prf.py` le o `PRF/config/cronograma.yml` com a arvore da PRF. Falha desde antes (procura `pmsc/config/`): `test_simulado_da_semana::test_a_tela_do_dia_real_nao_manda_ao_qconcursos`.

# Estado - 25/11/2026

Etapas 0 a 5 feitas, com a classificacao do Cebraspe, os levantamentos 1 e 2 (PRF-26, PRF-30, PRF-32), a explicacao com a Revisao do simulado (PRF-33) e a analise dos aprovados (PRF-34); tudo espera o aval do Gabriel.

## O que roda
- `radar subir` na 8002, com "MODO PRF". Config em `PRF/config/` (pelo `.env`), sem Telegram.
- Diario zerado (PRF-4). Arvore do edital de 2021 + os 22 capitulos do CTB + os nos da classificacao: 638 (PRF-6, PRF-17, PRF-32).
- Questoes: 10.259. Da PRF/: 245 do alvo (com as 8 de espanhol, PRF-24) e 1.693 complementares (PRF-16, PRF-19); dos levantamentos do Cebraspe, 97 (PRF-26) e 758 (PRF-32, provas de policia) complementares. Herdadas da PMSC: ficaram 7.466 de 16.317 (PRF-21, PRF-23): 476 do Cebraspe (complementar) e 6.990 de outras bancas (fora: treinam, nao medem).
- Geradas por IA: 1.404 (as da PMSC num no da PRF). Fichas 160: 103 herdadas (PRF-22) e as 57 do Ciclo 1 (PRF-36); macetes 45, glossario 462. Explicacoes 734 (PRF-33): o painel abre na questao corrigida do treino, e no fim o relatorio leva a `/simulado/{id}/revisao`.
- Certo/Errado (PRF-28, `docs/certo_errado.md`): em branco, nota liquida, chute fora do desempenho por assunto; Analises > Certo/Errado e `radar chute`. 2.018 itens C/E unicos (alvo + complementar).
- Cronograma (PRF-35, `docs/metodo.md`): Ciclo 1 de 04/01 a 13/02/2027 em `PRF/config/cronograma.yml`, gerado por `PRF/cronograma/` (como rodar, no topo do script). Diagnostico de 120 no sabado 09/01 e fechamento no 13/02, divididos como a prova de 2021 pelo bloco `materias`.
- Documentos: `docs/edital.md`, `docs/prioridade.md`, `docs/script_prf.md`, `docs/certo_errado.md`, `docs/dados_cronograma.md`, `docs/comparativo_pmsc_prf.md`, `docs/aprovados_prf.md`, `docs/metodo.md` e `docs/resolucoes_contran.md`. Redacao no criterio do Cebraspe (PRF-37, `PRF/config/redacao.yml`).

## Para o Gabriel conferir
- O Ciclo 1 na tela Hoje (`/hoje?data=2027-01-04` e os sabados 09/01 e 16/01) e o `docs/metodo.md`; a aba Redacao (`/redacao?data=2027-01-09`): os 6 temas, os textos-modelo e a NC estimada pelos conceitos (PRF-37).
- As 57 fichas novas (Hoje > Fichas, 🟣 nao conferida; `radar fichas --conferir <tema>`) e `docs/resolucoes_contran.md` (11 das 15 resolucoes do edital revogadas).
- As pendentes (Analises > Conferencia): 14 do alvo, 124 do complementar; 3 do alvo de lei mudada (PRF-33) e ~400 herdadas que ja eram pendentes na PMSC (so a materia).
- Dois gabaritos suspeitos (complementar, Penal, do Qconcursos herdado: 2023-q2215611 e 2023-q2048199; nada trocado). `data/classificacoes.json` (versionado, publico) guarda o `trecho` curto de cada questao (regra 5).

## Falta
- Duas anotacoes de classificacao do CONTRAN estao velhas (pelicula de 28%, medidor estatico e movel: `docs/resolucoes_contran.md`). Pendente cobrado: a IA gerar questao para assunto com menos de 50.
- Leitor de C/E (PRF-32), para reler com o seu aval: comando sem "julgue", lixo da capa no texto-base, os 25 itens de lingua dos cadernos de duas linguas, a Petrobras 2023, os 6 cadernos antigos sem recuo. Os 14 de multipla escolha do levantamento 2 so baixados.
- Explicacao (PRF-33): gerar o resto (`--quais todas`, comecando pelo Transito) e a da multipla escolha.
- Sem no (so a materia): 363 de multipla escolha do complementar e 1.128 herdadas. Transito segue com 137 C/E e capitulos do CTB zerados.

## Ainda da PMSC/PP
- O cartao "Sobre o chute" dos Macetes (letras A-E) e a frase da tela Certo ou Errado ("a prova da PMSC e de multipla escolha": nada ali e gravado). Concursos e Acompanhando vazias (PRF-22).

## Testes
- Leem um espelho do `data/` (PRF-9); `tests/test_cronograma_prf.py` le o `PRF/config/cronograma.yml` com a arvore da PRF. Falha desde antes (procura `pmsc/config/`): `test_simulado_da_semana::test_a_tela_do_dia_real_nao_manda_ao_qconcursos`.

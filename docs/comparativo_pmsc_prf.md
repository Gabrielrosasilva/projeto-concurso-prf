# Comparativo PMSC/PP x PRF

Etapa 3, 25/11/2026. Para o cronograma (Etapa 5) saber, matéria a matéria e
assunto a assunto, o que o Gabriel já estudou e o que é do zero.

## De onde sai cada número

- **Edital:** a árvore da PMSC (`fontes/radar_pmsc.db`, 871 nós) guardava os
  programas do edital da Polícia Penal de 2019 (e da prova de 2013) e do
  edital da PMSC de 2026 (nº 002/CCP/2026), com a procedência em cada matéria.
- **Assunto:** o mapa de nós PMSC -> PRF (`data/mapa_pmsc_prf.json`, decisão
  PRF-21). Um assunto da PRF está "coberto" quando algum nó da PMSC/PP cai
  nele ou embaixo dele. É conteúdo que **estava no programa**; não quer dizer
  que foi estudado.
- **Seus acertos:** as 495 respostas do radar da PMSC (simulados de 26/10 a
  16/11/2026), só as das questões reais. Eram de múltipla escolha (AOCP,
  FEPESE...): **treinam, mas não dizem como você vai no Certo/Errado do
  Cebraspe.** O mínimo para confiar numa matéria é de 20 respostas
  (`amostra.yml`); abaixo disso, o número só aparece.
- **Herdadas que ficaram:** as questões da PMSC que continuam no banco depois
  da Etapa 3 (evidência "fora": treinam, não medem).

## Matéria a matéria

| # | Matéria (ordem da prioridade) | No edital PMSC/PP? | Assuntos da PRF cobertos | Suas respostas (acerto) | Herdadas que ficaram |
|---:|---|---|---:|---|---:|
| 1 | Legislação de Trânsito | PMSC (só parte do CTB) | 1 de 3; 7 dos 22 capítulos do CTB | 38 (58%) | 123 |
| 2 | Língua Portuguesa | PMSC e PP | 7 de 7 | 18 (abaixo do mínimo) | 2.624 |
| 3 | Língua Estrangeira (Espanhol) | não | 0 de 2 | - | 0 |
| 4 | Informática | PMSC (e prova PP 2013) | 3 de 5 | 69 (70%) | 713 |
| 5 | Direito Administrativo | PP (Administração Pública; prova 2013) | 8 de 8 | - | 140 |
| 6 | Direito Constitucional | PMSC e PP | 5 de 5 | 57 (60%) | 854 |
| 7 | Raciocínio Lógico-Matemático | PP (Raciocínio Lógico) | 2 de 10 | - | 273 |
| 8 | Legislação Especial | PMSC e PP (outras leis) | 10 de 12 | 8 (abaixo do mínimo) | 489 |
| 9 | Ética e Cidadania | não | 2 de 5 | - | 92 |
| 10 | Física | não | 0 de 9 | - | 0 |
| 11 | Direito Penal | PMSC e PP | 6 de 6 | 31 (39%) | 1.519 |
| 12 | Direito Processual Penal | PMSC e PP | 4 de 6 | 26 (65%) | 363 |
| 13 | Direitos Humanos | PP | 3 de 3 | - | 94 |
| 14 | Geopolítica | não | 0 de 10 | - | 0 |

"Assuntos cobertos" conta os assuntos (2º nível da árvore). Em Direito
Penal, Constitucional e Administrativo o assunto todo pode estar coberto e
ainda faltar subassunto: a PRF cobra artigos que a PMSC/PP não cobrava, e o
contrário (Penas, Concurso de pessoas, LEP e Recursos ficaram fora da PRF).

## Do zero (nenhum nó da PMSC/PP caiu aqui)

- **Física:** os 9 assuntos (cinemática a colisões).
- **Geopolítica:** os 10 assuntos.
- **Espanhol.**
- **Raciocínio Lógico-Matemático:** 8 de 10. A PP cobrava lógica
  proposicional, que a PRF não tem. Do zero: equações e sistemas, função,
  taxas de variação, porcentagem, sequências, análise de dados, figuras
  planas e métrica. Cobertos: conjuntos, contagem e probabilidade.
- **Ética e Cidadania:** ética e moral; princípios e valores; ética e função
  pública (integridade). Cobertos: ética no setor público e cidadania.
- **Legislação de Trânsito:** a Lei 5.970/1973, as Resoluções do CONTRAN e 15
  dos 22 capítulos do CTB. Cobertos: capítulos I, II, III, VII, IX, XVIII e
  XIX.
- **Informática:** internet e intranet; transformação digital.
- **Direito Processual Penal:** Termo Circunstanciado (Lei 9.099) e
  identificação criminal (Lei 12.037).
- **Legislação Especial:** Decreto 1.655/1995 (e art. 47 do Decreto
  9.662/2019) e Lei 13.675/2018 (SUSP).

## O que isso diz para o cronograma

- **Começar do zero:** Física, Geopolítica, Espanhol, a parte de matemática
  do Raciocínio e o resto do Trânsito (Trânsito é 1/4 da prova).
- **Revisar e aprender o jeito do Cebraspe:** Português, Constitucional,
  Penal, Processo Penal, Administrativo, Direitos Humanos, Informática e
  Legislação Especial. O conteúdo já passou por você, mas o formato é outro.
- **Direito Penal:** 39% em 31 respostas, o menor acerto acima do mínimo.

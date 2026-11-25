# Levantamento do Cebraspe: provas das matérias que faltam

25/11/2026, Claude Code (claude-opus-5-5). Para achar questão do Cebraspe de
Espanhol, Física e Geopolítica, as matérias da PRF com pouca questão no banco
(Física 11, Espanhol 8, Geopolítica 33, todas quase só das provas da PRF).

## Como (sem Qconcursos, regra 4)

- robots.txt de www.cebraspe.org.br: `Disallow:` vazio (tudo liberado);
  apis e cdn sem robots.txt.
- A lista de concursos encerrados é a mesma que a tela do site usa (o
  endereço está no `main.*.chunk.js` público da página /concursos):
  `https://apis.cebraspe.org.br/cebraspe/eventos/tipo/concursos/fase/encerrado`
  (428 concursos).
- A página de cada um: `https://apis.cebraspe.org.br/cebraspe/eventos/{slug}`,
  com os arquivos e a descrição de cada um. Lidos os 428 com o User-Agent do
  radar e 1,5 s entre os pedidos; 36 não responderam.
- Os PDFs: `https://cdn.cebraspe.org.br/concursos/{slug}/arquivos/{arquivo}`.
- Tudo guardado fora do git em `PRF/levantamento_cebraspe/` (a lista, as 427
  páginas, os scripts `varrer.py` e `baixar.py` e os 28 PDFs).

## O que achei (caderno de conhecimentos específicos + gabarito definitivo)

Certo/Errado, o formato da PRF:

| Matéria | Prova | Caderno | Gabarito |
|---|---|---|---|
| Espanhol | SEE/DF 2016, professor de espanhol | SEE_16_DF/290_SEEDF_017_01.pdf | Gab_Definitivo_290_SEEDF_017_01.pdf |
| Espanhol | SEE/PE 2022, professor de espanhol | SEE_PE_22_EDUCACAO_BASICA/714_SEE_PE_008_01.PDF | GAB_DEFINITIVO_714_SEE_PE_008_01.PDF |
| Física | SEE/PE 2022, professor de física | SEE_PE_22_EDUCACAO_BASICA/714_SEE_PE_005_01.PDF | GAB_DEFINITIVO_714_SEE_PE_005_01.PDF |
| Física | FUB 2016, técnico de laboratório (física) | FUB_16_1/281FUB_012_01.pdf | Gab_Definitivo_281FUB_012_01.pdf |
| Geografia | SEE/DF 2016, professor de geografia | SEE_16_DF/290_SEEDF_014_01.pdf | Gab_Definitivo_290_SEEDF_014_01.pdf |
| Geografia | SEE/PE 2022, professor de geografia | SEE_PE_22_EDUCACAO_BASICA/714_SEE_PE_006_01.PDF | GAB_DEFINITIVO_714_SEE_PE_006_01.PDF |

Múltipla escolha (treina o conteúdo, não o padrão do Cebraspe): SEED/PR 2020
(espanhol, física e geografia), SESI/SP 2023 (física e geografia), SDS/PE
2016 perito de física, Prefeitura de São Luís 2016 e de Barra dos Coqueiros
2020 (geografia).

Espanhol no formato da prova (compreensão de texto em Certo/Errado) só há o
da PRF 2021. As provas de professor misturam itens de língua (servem) com
itens de didática (não servem). O Itamaraty (IRBr) tem espanhol só na
discursiva.

## Falta (próximo passo, com o aval do Gabriel)

1. Os 6 de Certo/Errado entram em `PRF/config/provas_de_outras_bancas.yml`
   (baixadas a mão, os PDFs já estão aqui) com as faixas só dos itens do
   programa da PRF: língua espanhola sem didática; em Física, a mecânica do
   edital; em Geografia, o Brasil do item de Geopolítica. Como na PRF-16.
2. `radar questoes --banca CEBRASPE` e a classificação nos nós (duas leituras
   às cegas, PRF-19).

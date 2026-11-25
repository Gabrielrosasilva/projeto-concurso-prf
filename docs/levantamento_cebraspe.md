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

## Feito (25/11/2026, PRF-26)

As 6 de Certo/Errado entraram em `PRF/config/provas_de_outras_bancas.yml`
(seção do fim), com as faixas só dos itens do programa da PRF, e foram
classificadas com duas leituras às cegas, como na PRF-19: 97 de 380 itens
(Física 27, Geopolítica 23, Espanhol 47). O que ficou fora de cada caderno
está no `# fora:` da entrada. As de múltipla escolha continuam de fora.

## Levantamento 2: provas de polícia (25/11/2026, PRF-30)

Claude Code (claude-opus-5-5). Contadas só as Certo/Errado reais do Cebraspe
(alvo + complementar, sem anuladas), por item da prova de 2021: Ética 18 (3
por item), Direitos Humanos 24 (4,8), Trânsito 168 (5,6), Língua Estrangeira
60 (só 7 de inglês), Física 38 e Geopolítica 38 (7,6). As outras passam de 12.
Assuntos com zero: CTB caps. IV, V, VI, X e XI; "Ética e função pública:
integridade"; Lei 13.675/2018 e Decreto 1.655/1995; Poder constituinte;
figuras planas; três de Geopolítica e "energia, atrito" de Física.

**Como:** a mesma lista do levantamento 1 (`eventos/`). Dos concursos de
polícia, bombeiro e segurança que não estão no banco, li o edital de abertura
de 20 (`editais/`) e procurei as matérias fracas no conteúdo programático.
Depois baixei o caderno e o gabarito definitivo dos que têm alguma
(`candidatos2.json`, 33 cadernos e 33 gabaritos, todos 200 e PDF). Os scripts
`baixar_editais.py`, `ler_editais.py`, `contexto_editais.py` e `baixar2.py`
ficam em `PRF/levantamento_cebraspe/`, fora do git, com o User-Agent do radar
e 1,5 s entre os pedidos.

**O que os editais cobram:**
- CBM/AL 2017 e 2021: "Ética, Cidadania e Direitos Humanos" com os mesmos
  tópicos da PRF (ética e moral; princípios e valores; democracia e
  cidadania; função pública; setor público; teoria geral dos DH), Física
  (vetores, Newton, trabalho e energia) e Inglês.
- DEPEN 2020: "Ética no serviço público" (os tópicos da PRF), "Noções de
  Direitos Humanos" e a Lei 13.675/2018. **O caderno já está em `PRF/`** e
  não entrou porque tem três gabaritos para um caderno (`docs/script_prf.md`).
- Polícia Científica/AL 2022: Direitos Humanos (teoria geral), a Convenção
  Americana e os crimes de trânsito.
- PM/AL 2017 e 2018: Noções de Direitos Humanos (a Convenção Americana).
- PM/MA 2017: Física (Newton, atrito e plano inclinado).
- ABIN 2017: Inglês (oficial de inteligência) e DH internacional.
- MJSP 2021: ética no serviço público e a Lei 13.675/2018.
- PC/AL 2022, PC/MA 2017, PJC/MT 2017, PC/PE 2016 e PC/GO 2016: só a
  Convenção Americana e os **crimes** de trânsito.

**Trânsito:** nenhum concurso da lista cobra o CTB inteiro. Fora a PRF 2018 e
2021 e o DETRAN-AL 2026 (que já estão no banco), só há o agente de trânsito
de Barra dos Coqueiros 2020, de múltipla escolha. A PRF 2013 não está na API
(`eventos/PRF_13` responde 204). O CTB que falta tem que vir de outro lugar:
o que o Gabriel baixar à mão (PRF-27) ou questão gerada (que treina, não mede).

**Os 33 cadernos baixados (`pdf/`, prefixo do concurso):**

| Situação | Cadernos |
|---|---|
| C/E, o leitor já lê (15, 1.139 itens) | CBM/AL 2017 específicos (oficial e soldado); CBM/AL 2021 cargos 1 e 2; Polícia Científica/AL 2022 cargo 1 e básicos CB1, CB2, CB3; PM/AL 2017 básicos; PM/AL 2018; PM/MA 2017 gerais e específicos; ABIN 2017 CB1; MJSP 2021 gerais; PC/AL 2022 delegado gerais |
| C/E, o leitor ainda não lê (4) | CBM/AL 2017 básicos CB1 e CB2 e ABIN 2017 CB2 e CB3 (o gabarito traz inglês e espanhol na mesma grade: "duas letras" no item); PM/AL 2017 específicos (o gabarito vai até 119, o caderno até 120) |
| Múltipla escolha (14, esperam: não medem) | CBM/TO 2021 e 2022 (cargos 1 e 2); PM/TO 2020 QPS; PC/MA 2017 escrivão e investigador; PC/PE 2016 gerais e agente; PC/GO 2016 básicos, gerais e agente; PJC/MT 2017 delegado |

Só entra o item do programa da PRF: quantos, sai da leitura item a item,
como na PRF-26 (lá foram 97 de 380).

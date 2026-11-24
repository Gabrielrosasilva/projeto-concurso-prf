# O edital - PRF

**Edital Concurso PRF nº 1, de 18 de janeiro de 2021** - Policial Rodoviário
Federal, banca **Cebraspe** (com a PRF, item 1.1), abrangência nacional (1.2).
Página do concurso, citada no próprio edital (7.4.9.11.7, 8.3 e outros):
http://www.cebraspe.org.br/concursos/prf_21

- O PDF é o `Edital 2021.pdf` da raiz, idêntico a
  `PRF/cebraspe_prf_2021_edital_abertura.pdf` (os dois fora do git).
- Lido em 24/11/2026 pelo Claude Code (claude-opus-5-5). Edital de
  retificação, se houve, não está no acervo e não foi lido.
- Vale até sair o edital novo (previsto para 2027).

## A prova (8.1)

| Prova | Itens | Caráter |
|---|---:|---|
| P1 objetiva - Bloco I | 55 | eliminatório e classificatório |
| P1 objetiva - Bloco II | 30 | |
| P1 objetiva - Bloco III | 35 | |
| P2 discursiva | texto dissertativo de até 30 linhas | eliminatório e classificatório |

As duas no mesmo turno, à tarde, em 4h30 (8.2). Depois vêm o exame de
aptidão física, a avaliação psicológica, os documentos, a saúde, os títulos e
a investigação social; a segunda etapa é o Curso de Formação Policial (1.3).

## A objetiva (9)

- Vale 120,00 pontos (9.1); cada item é julgado CERTO ou ERRADO (9.2).
- Cada item: **+1,00** se concorda com o gabarito definitivo, **-1,00** se
  discorda, **0,00** em branco ou com marcação dupla (9.12.2).
- Eliminado com menos de **15,00 no Bloco I**, **10,00 no Bloco II**,
  **10,00 no Bloco III** ou **50,00 no total** (9.12.4).

## A discursiva (10)

- Vale 20,00 pontos: texto dissertativo de até 30 linhas sobre tema dos
  objetos de avaliação (10.1).
- **NPD = NC - 4 x (NE / TL)**: NC é o conteúdo (até 20,00), NE os erros de
  grafia, morfossintaxe e propriedade vocabular, TL as linhas escritas
  (10.6.4). Eliminado com NPD abaixo de 10,00; fuga ao tema ou sem texto, zero.
- Só é corrigida até a 6.000ª posição na objetiva: 4.500 ampla concorrência,
  1.200 negros, 300 com deficiência (10.6.1).

## A nota e o desempate

- Nota da primeira etapa = objetiva + discursiva + títulos (17.1).
- Desempate (18.1): 60 anos ou mais; **maior nota no Bloco II**, mais acertos
  no Bloco II; nota e acertos no Bloco III; nota e acertos no Bloco I; nota da
  discursiva; mais idade; jurado.

## As matérias (24.2)

O edital diz quantos itens tem cada **bloco**, e não cada matéria. Quanto
cada matéria teve de verdade está em `docs/prioridade.md`, contado nas provas.

| Bloco | Matéria | Assuntos | Subassuntos |
|---|---|---:|---:|
| I (55 itens) | Língua Portuguesa | 7 | 18 |
| I | Raciocínio Lógico-Matemático | 10 | 15 |
| I | Informática | 5 | 8 |
| I | Física | 9 | 0 |
| I | Ética e Cidadania | 5 | 6 |
| I | Geopolítica | 10 | 0 |
| I | Língua Estrangeira (Inglês ou Espanhol) | 2 | 4 |
| II (30 itens) | Legislação de Trânsito | 3 | 39 |
| III (35 itens) | Direito Administrativo | 8 | 22 |
| III | Direito Constitucional | 5 | 23 |
| III | Direito Penal | 6 | 18 |
| III | Direito Processual Penal | 6 | 13 |
| III | Legislação Especial | 12 | 0 |
| III | Direitos Humanos | 3 | 1 |

## A árvore de conteúdos

Está em `data/conteudos.json` (273 nós): as 14 matérias, 91 assuntos e 167
subassuntos, mais "História da PRF", marcada como fora do edital atual (estava
no de 2018 e caiu na prova de 2019). Foi montada a partir do PDF pelo
`radar conteudos --semear --edital "Edital 2021.pdf"` (src/radar/edital_cebraspe.py).

- Assunto é o tópico numerado (1, 2, 3...); subassunto é o subtópico (4.1,
  4.2...). O terceiro nível (3.1.1) fica no texto do edital do subassunto.
- A lista de resoluções do CONTRAN (Trânsito, tópico 3) virou 39 subassuntos,
  um por resolução.
- Todo nó guarda o texto literal (`texto_do_edital`) e a procedência
  "EDITAL CONCURSO PRF Nº 1, DE 18 DE JANEIRO DE 2021, item 24, BLOCO ...".
- Defeitos do edital mantidos como estão: Direito Penal vai do 2 direto ao 2.2;
  em Geopolítica falta o ponto entre os tópicos 7 e 8 (o leitor separa os dois).

## O edital de 2018, para comparar

**Edital nº 1 - PRF, de 27 de novembro de 2018** (`PRF/cebraspe_prf_2018_edital_abertura.pdf`,
prova aplicada em 3/2/2019):

- Blocos com **50, 40 e 30** itens; mínimos de 10,00, 12,00 e 6,00, e 48,00 no total.
- Bloco I sem língua estrangeira e com **História da PRF**; Bloco III com
  "Noções de Direito Penal e de Direito Processual Penal" numa matéria só.
- Outros nomes: Noções de Física, Ética no Serviço Público, Geopolítica
  Brasileira, Direitos Humanos e Cidadania (são sinônimos na
  `PRF/config/taxonomia.yml`).

De 2018 para 2021 o Trânsito caiu de 40 para 30 itens, o Bloco I subiu de 50
para 55 e o Bloco III de 30 para 35. O edital de 2027 pode mudar de novo.

# A ordem de prioridade das matérias - PRF

Etapa 1, 24/11/2026. O edital (docs/edital.md) só dá o número de itens de cada
**bloco**; quanto cada matéria pesou de verdade sai das duas provas da PRF que
temos, as duas do Cebraspe. Todo item vale o mesmo (+1/-1), então o peso de
uma matéria é o número de itens dela.

**A regra:** (1) itens na prova de 2021, a do edital que vale; (2) no empate,
itens na prova de 2019; (3) no empate, a ordem do edital (item 24.2).

| # | Matéria | Bloco | 2021 | % da objetiva | 2019 | Média do bloco no edital |
|---:|---|:---:|---:|---:|---:|---:|
| 1 | Legislação de Trânsito | II | 30 | 25,0% | 40 | 30 |
| 2 | Língua Portuguesa | I | 18 | 15,0% | 20 | 7,9 |
| 3 | Língua Estrangeira (Inglês ou Espanhol) | I | 8 | 6,7% | - | 7,9 |
| 4 | Informática | I | 7 | 5,8% | 6 | 7,9 |
| 5 | Direito Administrativo | III | 7 | 5,8% | 5 | 5,8 |
| 6 | Direito Constitucional | III | 7 | 5,8% | 5 | 5,8 |
| 7 | Raciocínio Lógico-Matemático | I | 6 | 5,0% | 8 | 7,9 |
| 8 | Legislação Especial | III | 6 | 5,0% | 5 | 5,8 |
| 9 | Ética e Cidadania | I | 6 | 5,0% | 4 | 7,9 |
| 10 | Física | I | 5 | 4,2% | 6 | 7,9 |
| 11 | Direito Penal | III | 5 | 4,2% | 5* | 5,8 |
| 12 | Direito Processual Penal | III | 5 | 4,2% | 5* | 5,8 |
| 13 | Direitos Humanos | III | 5 | 4,2% | 5 | 5,8 |
| 14 | Geopolítica | I | 5 | 4,2% | 4 | 7,9 |
| - | História da PRF (fora do edital de 2021) | - | 0 | - | 2 | - |

- "2019" é a prova do edital de 2018, aplicada em 3/2/2019, que tinha outros
  blocos (50/40/30). Língua estrangeira não existia nela.
- \* Em 2018, Penal e Processo Penal eram uma matéria só ("Noções de Direito
  Penal e de Direito Processual Penal"), com 10 itens; a divisão 5 e 5 é minha.
- "Média do bloco" é o que o edital sozinho diz: itens do bloco divididos
  pelas matérias dele (55/7, 30/1, 35/6).

O que pesa além da tabela:
- **Trânsito é 1/4 da objetiva** e é o primeiro desempate depois da idade
  (maior nota e mais acertos no Bloco II, item 18.1, b e c).
- **Português também conta na discursiva**: cada erro tira pontos da nota
  (NPD = NC - 4 x NE / TL).
- Os mínimos: 15 dos 55 do Bloco I, 10 dos 30 do Bloco II, 10 dos 35 do
  Bloco III e 50 no total (item 9.12.4).

## Como contei

Cada grupo de itens abre com um comando ("Julgue os itens a seguir, a
respeito de...") e as matérias vêm na ordem do edital. Marquei onde cada uma
começa e termina, lendo os PDFs oficiais. A classificação é do Claude Code
(claude-opus-5-5), em 24/11/2026: confira pelas faixas.

**Prova de 2021** (`PRF/cebraspe_prf_2021_policial_prova_lingua_inglesa.pdf`,
itens 1 a 8, e `..._prova_itens_9_120.pdf`):
- Língua Estrangeira: 1-8. O caderno do acervo é o de inglês; o de espanhol
  não está nele.
- Língua Portuguesa: 9-26 (22-26 do Manual de Redação da Presidência).
- Raciocínio Lógico-Matemático: 27-32.
- Informática: 33-39.
- Física: 40-44.
- Ética e Cidadania: 45-50.
- Geopolítica: 51-55.
- Legislação de Trânsito: 56-85.
- Direito Administrativo: 86-92 (91 e 92 sobre a carreira de PRF).
- Direito Constitucional: 93-99.
- Direito Penal: 100-104.
- Direito Processual Penal: 105-109.
- Legislação Especial: 110-115.
- Direitos Humanos: 116-120.

**Prova de 2019** (`PRF/cebraspe_prf_2018_policial_prova.pdf`):
- Língua Portuguesa: 1-20.
- Raciocínio Lógico-Matemático: 21-28.
- Informática: 29-34.
- Física: 35-40.
- Ética: 41-44.
- Geopolítica: 45-48.
- História da PRF: 49-50.
- Legislação de Trânsito: 51-90.
- Direito Administrativo: 91-95.
- Direito Constitucional: 96-100.
- Penal e Processo Penal: 101-110. Penal: 101, 102, 106, 107 e 108 (o 108 é o
  tipo penal do tráfico de pessoas); Processo Penal: 103-105, 109 e 110.
- Legislação Especial: 111-115.
- Direitos Humanos: 116-120.

O item anulado conta na matéria em que caiu.

**Conferência.** Comparei com a classificação do Qconcursos que o script de
`PRF/` guardou (`PRF/cobertura_metadados.json`), matéria a matéria:
- **2021, batem:** Português (13 + 5 de Redação Oficial), Raciocínio (6),
  Informática (6 + 1 de Banco de Dados), Física (5), Geopolítica (3 de
  Geografia + 2 de Conhecimentos Gerais) e Trânsito (30).
- **2021, não batem:** Ética (2 lá, 6 aqui) e o Bloco III. O Qconcursos
  classifica pela taxonomia dele, e a soma dele dá 105 dos 112 itens de 9 a
  120.
- **2019, batem:** o Bloco I e o II inteiros. Lá, os 2 itens de História da
  PRF estão em "Conhecimentos Gerais".

## O resto do acervo do Cebraspe (não entra na ordem)

As outras ~100 provas do Cebraspe em `PRF/` são de outros concursos (PF, PC,
DEPEN, DETRAN...), cada uma com o seu edital. Elas medem quanta questão de
treino existe por matéria, e não o peso na prova da PRF. Somando o que o
Qconcursos atribui a cada matéria nas 80 páginas de prova do Cebraspe do
script:

| Matéria | Questões |
|---|---:|
| Língua Portuguesa | 829 |
| Legislação de Trânsito | 583 |
| Direito Penal | 509 |
| Direito Administrativo | 477 |
| Informática | 443 |
| Direito Constitucional | 430 |
| Raciocínio Lógico-Matemático | 396 |
| Direito Processual Penal | 326 |
| Direitos Humanos | 113 |
| Geopolítica | 47 |
| Física | 44 |
| Ética | 34 |

**Falta treino de Física, Ética e Geopolítica.** Legislação Especial e língua
estrangeira não aparecem com esse nome na classificação do Qconcursos. A
Etapa 2 decide se o script e esses dados ficam (regra 4 do CLAUDE.md).

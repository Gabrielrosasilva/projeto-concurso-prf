# Os aprovados da PRF: onde pesa e onde se perde ponto

25/11/2026, Claude Code (claude-opus-5-5), pedido do Gabriel (PRF-34). Contado nos
editais de resultado do Cebraspe, **só as notas**: nenhum nome nem inscrição sai da
pasta `PRF/levantamento_cebraspe/aprovados/` (fora do git). Os números agregados
moram em `data/aprovados_prf.json`, e a tela Análises > Certo/Errado mostra a sua
nota de cada bloco ao lado deles.

## De onde veio

| Ano | O que | Link |
|---|---|---|
| 2021 | Edital nº 11: notas dos blocos, objetiva e discursiva provisória | [PDF](https://cdn.cebraspe.org.br/concursos/PRF_21/arquivos/ED_11_PRF_2021_FINAL_OBJETIVA_PROV_DISCURSIVA.PDF) |
| 2021 | Edital nº 12: discursiva final | [PDF](https://cdn.cebraspe.org.br/concursos/PRF_21/arquivos/ED_12_PRF_2021_FINAL_DISCURSIVA_CONV_TAF_FIP_MATRCULA.PDF) |
| 2021 | Padrão de resposta definitivo da discursiva | [PDF](https://cdn.cebraspe.org.br/concursos/PRF_21/arquivos/PRF_21_PADRAO_DE_RESPOSTA_DEFINITIVO.PDF) |
| 2019 | Edital nº 7 do concurso PRF_18: notas **e acertos** dos blocos | [PDF](https://cdn.cebraspe.org.br/concursos/PRF_18/arquivos/ED_7_PRF_2018_RETOMADA_E_RES_FINAL_OBJET_PROV_DISC.PDF) |
| 2019 | Edital nº 8: discursiva final | [PDF](https://cdn.cebraspe.org.br/concursos/PRF_18/arquivos/ED_8_PRF_2018_RES_FINAL_DISC_CONV_EXAMES_FIP.PDF) |
| 2019 | Padrão de resposta definitivo da discursiva | [PDF](https://cdn.cebraspe.org.br/concursos/PRF_18/arquivos/PRF_18___PADRO_DE_RESPOSTAS_DEFINITIVO.PDF) |

Os scripts: `PRF/levantamento_cebraspe/baixar_aprovados.py`, `ler_aprovados.py` e
`contar_aprovados.py` (User-Agent do radar, 1,5 s entre os pedidos).

## Como contei

- **Passou** = teve a discursiva corrigida e ficou com 10 ou mais nela (edital 2021,
  10.6.4). Só as 6.000 primeiras na objetiva têm a discursiva corrigida (10.6.1).
- **Lista geral** (2021) = a lista 1.1 do Edital nº 11: a da ampla concorrência, com
  os cotistas que passaram o corte dela. O menor valor dela é o **corte da ampla**.
- **As 1.500** (2021) = as 1.500 maiores notas de objetiva + discursiva entre as que
  passaram. É uma **aproximação** das vagas: sem a nota de títulos e sem as listas de
  cotas, que o edital separa.
- Em 2019 as listas são por UF, e a ampla não foi separada: os números são de todos
  os que passaram. Em compensação, o edital de 2019 dá os **acertos** de cada bloco, e
  com a nota líquida isso dá os erros e os em branco.
- Nota líquida = certos − errados (o em branco vale 0).

## 2021 (o edital que vale)

5.886 discursivas corrigidas; **488 (8%) caíram na discursiva** (abaixo de 10); 5.398
passaram. **Corte da ampla para ter a discursiva corrigida: 73 de 120.**

| | Itens | Lista geral (mediana) | As 1.500 (mediana) | As 1.500 (q1 – q3) |
|---|---:|---:|---:|---:|
| Objetiva | 120 | 77 | **83** (69%) | 81 – 86 |
| Bloco I (básicos) | 55 | 28 (51%) | **31** (56%) | 28 – 34 |
| Bloco II (Trânsito) | 30 | 26 (87%) | **27** (90%) | 25 – 28 |
| Bloco III (Direito) | 35 | 25 (71%) | **26** (74%) | 24 – 28 |
| Discursiva | 20 | 15,33 | **17,09** | 15,56 – 18,34 |

## 2019 (comparação)

2.479 discursivas corrigidas; **190 (8%) caíram na discursiva**; 2.283 passaram.
Medianas de quem passou (todas as listas):

| | Itens | Nota líquida | Certos | Errados | Em branco |
|---|---:|---:|---:|---:|---:|
| Objetiva | 120 | 88 (73%) | | | |
| Bloco I (básicos) | 50 | 32 (64%) | 37 | 4 | **8** |
| Bloco II (Trânsito) | 40 | 33 (83%) | 36 | 2 | 1 |
| Bloco III (Direito) | 30 | 23 (77%) | 26 | 3 | 1 |
| Discursiva | 20 | 15,24 | | | |

## O balanço

1. **Trânsito é piso, não diferencial.** O aprovado típico faz 87% a 90% líquido no
   bloco de Trânsito, e quem está entre as 1.500 faz só 1 ponto a mais que a lista
   geral. Ou seja: todo mundo que passa vai muito bem em Trânsito, e quem não vai
   fica para trás. É um quarto da prova e o primeiro desempate depois da idade
   (18.1).
2. **O Bloco I é onde os aprovados se separam.** Da lista geral para as 1.500, a
   mediana sobe 3 líquidos no Bloco I contra 1 nos outros dois. E é onde o aprovado
   mais **deixa em branco**: em 2019, 8 itens em branco no Bloco I contra 1 nos
   outros blocos, com só 4 errados. No bloco dos básicos (Português, Raciocínio
   Lógico, Informática, Física...) o aprovado não chuta o que não sabe.
3. **A discursiva pesa e elimina.** 8% dos que tiveram a discursiva corrigida caíram
   nela, nos dois anos. Entre as 1.500, a mediana foi 17,09 de 20, contra 15,33 na
   lista geral: quase 2 pontos, o mesmo que 2 itens líquidos da objetiva.
4. **A meta prática (2021):** objetiva por volta de **83 líquidos** (69%), e nunca
   abaixo de 73 (o corte para ter a discursiva corrigida); discursiva por volta de
   **17**; por bloco, **31 de 55**, **27 de 30** e **26 de 35**.
5. **Não compare as medianas de 2019 e 2021 direto:** em 2019 só 2.479 tiveram a
   discursiva corrigida, contra 5.886 em 2021, e o grupo menor tem a mediana
   maior. O que se compara entre os anos é o desenho: Trânsito alto, básicos
   separando, discursiva eliminando 8%.

## A discursiva

Os dois temas foram de trânsito, com três quesitos de conteúdo (2.1, 2.2 e 2.3), de
0 a 3 cada:

- **2019:** as infrações nas rodovias - o que a PRF faz ou pode fazer (efetivo,
  equipamentos eletrônicos, operações integradas, campanhas), o que a sociedade pode
  fazer (campanhas, palestras, escolas) e o que o indivíduo pode fazer
  (conscientização, atividades educativas, ajuda a vítimas).
- **2021:** o efeito dos crimes de trânsito no CTB e da Lei Seca nos acidentes (a
  redução no começo e o aumento depois, e as causas: menos fiscalização, campanhas
  curtas) e as ações para reduzir os acidentes (conscientização, educação para o
  trânsito, mais estrutura de fiscalização).

O que dá nota 3 em cada quesito, pelos dois padrões: **explicar** (não só citar) o
aspecto, **com exemplos e causas**, **articulado** com o tema e com os outros
aspectos. Citar sem desenvolver vale 1; desenvolver desconectado do texto vale 2.

O desconto do português: **NPD = NC − 4 × (NE / TL)**. Numa redação de 30 linhas
com 6 erros de grafia, morfossintaxe ou vocabulário, saem 4 × 6 / 30 = **0,8 ponto**,
quase um item líquido da objetiva. Abaixo de 10, eliminado.

## O que os editais não dizem

- **O acerto item a item:** cada candidato vê só o próprio. Não existe "a questão que
  os aprovados mais erraram"; dá para saber o bloco, não a questão.
- **As redações dos candidatos:** não são públicas. O que se sabe é o que a banca
  esperava (o padrão de resposta) e a nota de cada um.

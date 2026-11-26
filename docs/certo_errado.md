# O Certo/Errado do Cebraspe - nota líquida e regra do chute

Etapa 4 da PRF (decisão PRF-28), 25/11/2026. Contado pelo Claude Code
(claude-opus-5-5) com o próprio radar: a tela **Análises > Certo/Errado** e o
comando `radar chute` (com `--gabaritos` para os gabaritos inteiros) refazem
toda conta daqui.

## A pontuação (edital PRF 2021)

- Cada item: **+1** se concorda com o gabarito definitivo, **−1** se discorda,
  **0** em branco ou com marcação dupla (item 9.12.2). Uma errada anula uma certa.
- Eliminado com menos de 15 pontos no Bloco I, 10 no II, 10 no III ou 50 no
  total (item 9.12.4). Fonte: `docs/edital.md`.

## A conta do chute

Com chance **p** de acertar, chutar rende em média p × (+1) + (1 − p) × (−1)
= **2p − 1** ponto. Só compensa com p acima de 50%. Em branco rende 0.

## O Cebraspe dá mais Certo ou mais Errado?

Margem de 95% da proporção (1,96 × raiz(p(1−p)/n)): enquanto ela cobre os
50%, a diferença pode ser sorteio.

**Itens do Cebraspe no radar** (uma vez por item pela chave, gabarito
definitivo, anulado à parte):

| Recorte | Certo | Errado | Anulados | Cadernos | % Errado | Margem |
|---|---:|---:|---:|---:|---:|---:|
| Prova da PRF de 2019 | 46 | 59 | 12 | 1 | 56,2 | ±9,5 |
| Prova da PRF de 2021 | 57 | 60 | 11 | 3 | 51,3 | ±9,1 |
| Provas da PRF juntas | 103 | 119 | 23 | 4 | 53,6 | ±6,6 |
| Acervo complementar do Cebraspe | 578 | 595 | 45 | 54 | 50,7 | ±2,9 |
| **Tudo** | **681** | **714** | 68 | 58 | **51,2** | ±2,6 |

Limite: o complementar só tem os itens das matérias do programa da PRF
(PRF-16), não os cadernos inteiros. Os 3 itens de figura da prova de 2019
saíram (PRF-14).

**Gabaritos definitivos inteiros** dos cadernos de Certo/Errado do Cebraspe
da lista `PRF/config/provas_de_outras_bancas.yml` (todo item, cada arquivo
uma vez, lidos dos PDFs pelo `ler_gabarito_do_cebraspe`):

| Recorte | Certo | Errado | Anulados | Cadernos | % Errado | Margem |
|---|---:|---:|---:|---:|---:|---:|
| Provas da PRF (2019, 2021 e as 2 línguas) | 105 | 120 | 23 | 4 | 53,3 | ±6,5 |
| Os outros cadernos | 1.915 | 2.031 | 164 | 58 | 51,5 | ±1,6 |
| **Todos** | **2.020** | **2.151** | 187 | 62 | **51,6** | ±1,5 |

Limite: cadernos do mesmo concurso repetem a parte comum, que aqui conta em
cada um (os da PF 2021 de agente e de escrivão dão os mesmos 51 Certo e 64
Errado) - o n é menor do que parece, e a margem, maior.

**Leitura.** Nos itens únicos, 51,2% Errado com margem de 2,6: equilibrado.
Nos gabaritos inteiros, 51,6% com margem de 1,5: um lado Errado no limite da
margem, com a repetição inflando o n. Mesmo que exista, chutar sempre Errado
às cegas renderia de +0,024 a +0,031 ponto por item: uns 3 pontos a cada 100
itens chutados. Na prova de 120 itens, isso é nada perto do risco de errar.

## A regra do chute

1. **Sabe:** marque.
2. **Tem uma inclinação** (lembra em parte, descartou algo): vale o que os
   SEUS chutes mostram. Nos treinos e simulados, marque "Vou no chute" antes
   de responder; com 30 chutes (`config/amostra.yml`, `desempenho.chutes`) o
   radar diz se eles acertam mais de 50% além da margem (chute), menos
   (em branco) ou se a margem cobre os 50% (tanto faz: na dúvida, em branco).
   Até lá: em branco.
3. **Não faz ideia:** em branco. O chute cego rende zero na prática (acima).

## O que o radar faz com isso

- **Em branco**: todo item de Certo/Errado tem o botão "Deixar em branco"
  (treino e simulado). A resposta fica dada (a rodada anda), sem acerto e sem
  chute; vale 0 na nota. Gravado como `escolhida = "-"`, `acertou` nulo -
  sem mudar a estrutura do banco.
- **Nota líquida**: a rodada com Certo/Errado mostra a nota (certos − errados,
  de N itens, e a porcentagem do máximo) no lugar do acerto, com o acerto
  bruto ao lado e o saldo dos chutes. A múltipla escolha da mesma rodada fica
  à parte, nunca somada.
- **O chute** (escolha do Gabriel em 25/11/2026):
  - na **nota da rodada**: conta, como na prova (o chute errado tira 1);
  - no **caderno de erros**: o chute errado fica fora (refazer os erros, R+7,
    contagem de motivos; a tela não oferece o motivo nem o "Anotar"). Volta
    pelo Simulado da semana, que traz primeiro o que errei ou chutei;
  - no **desempenho por assunto** (faixa, ficha, Minhas matérias, Análises,
    evolução, o 1-7-30 da revisão): sai o chute inteiro, o certo e o errado,
    e o número de chutes aparece ao lado. Tirar só o errado deixaria o acerto
    maior do que eu sei. A questão cuja última resposta foi no chute não conta
    pela resposta firme de antes. Chutar continua contando como "praticado".
- No desempenho por assunto não há nota líquida à parte: sem o em branco (que
  fica fora), ela é sempre 2 × acerto − 100, e não diria nada novo.
- **O Certo/Errado do Cebraspe treina e mede**: os 58 cadernos de Certo/Errado
  do Cebraspe da lista entram como complementar aceito
  (`complementar.cadernos_de_certo_errado`): 1.180 itens únicos e classificados
  no estoque das rodadas, além dos 210 do alvo. A múltipla escolha do Cebraspe
  (761 itens) continua fora, como antes.

## O Certo/Errado escrito pela IA (PRF-40, 26/11/2026)

A maior parte das aulas do Ciclo 1 tem poucos itens reais (o CTB tem capítulo
com zero). A IA escreve o que falta, **por aula do cronograma**, e o item
**treina, nunca mede** (regra 1): mora em `questoes_geradas`, não entra na
nota líquida, na incidência nem no simulado que mede.

- **Quanto:** cada aula completa **35** itens de treino (os 15 da Fixação e os
  20 da Aprendizagem do mesmo dia, sem repetir), contando os reais de
  Certo/Errado do complementar e as geradas que já tem. As revisões R+7 e
  R+30 repetem, as erradas primeiro.
- **De onde:** `radar gerar --pedido --certo-errado --materia "<matéria>"`
  monta um pedido por aula, com os nós da ficha (os mesmos que a faixa usa),
  o texto vigente da lei (`PRF/config/textos_de_lei.yml`: o CTB da Câmara e,
  nas resoluções do CONTRAN, a que substituiu a do edital, em
  `leis/contran/`) e os itens reais do tema só como exemplo de estilo. A
  prova da PRF não vai de exemplo: é ela que mede.
- **O que a importação recusa:** item sem `artigo`, sem `explicacao`, com
  resposta que não é c ou e, com nó fora da aula, ou cópia de um exemplo.
- **A conferência:** quem escreve confere item por item no texto da lei; depois
  outro agente julga cada item às cegas (sem o gabarito), e o que diverge é
  decidido pelo texto antes de importar.
- **Na tela:** o botão "IA · N" da faixa; depois de responder, o "Por quê,
  segundo a IA" (a coluna `explicacao`, passo 12 da migração) e o artigo. O
  item tem o "Deixar em branco", como o real. "Essa questão está errada" tira
  o item do sorteio para sempre.
- **As partes de capítulo:** as aulas que dividem um capítulo do CTB
  (infrações 1, 2 e 3, por exemplo) ganharam um nó próprio ("CTB, arts. 161 a
  190") na árvore e na ficha: sem ele, a faixa da parte 1 sortearia item das
  partes 2 e 3.

## As outras matérias do Ciclo 1 (PRF-41, 26/11/2026)

O mesmo pedido por aula, agora em Português, nos Direitos e na Legislação
Especial: **788 itens** (Português 40, Constitucional 136, Administrativo 70,
Penal 127, Processo Penal 94, Legislação Especial 255, Direitos Humanos 66).

- **O que ficou com menos de 35:** Poder constituinte (30) e Princípios básicos
  (33): o resto da ficha é doutrina, e doutrina não decide item. A
  Correspondência oficial ficou sem: o Manual de Redação da Presidência não
  tem cópia local (o Planalto bloqueia robô). A aula de Interpretação de texto
  3 e a da Lei 10.826 continuam sem ficha.
- **O texto:** `PRF/config/textos_de_lei.yml` ganhou os nós dessas matérias.
  O nó da CF não tem intervalo no nome: o `artigos` do item diz o trecho
  ("arts. 76 a 91"), e um nó pode ter mais de um item (duas normas, ou a CF
  arts. 1º a 5º e art. 109). A CF, o CP, o CPP e a Lei 11.343 foram baixados de
  novo da Câmara (iguais às cópias da PMSC); a acentuação vai pelo Acordo
  Ortográfico (Decreto 6.583/2008).
- **A regra:** o gabarito sai do texto da norma. Doutrina, jurisprudência e
  súmula não decidem item; dispositivo com nota de ADI/ADPF ou afastado pelo
  STF fica de fora (a ADPF 779, no art. 25 do CP, só afastou a "legítima
  defesa da honra": a legítima defesa entrou). Concordância e regência, que
  não têm norma: só regra pacífica, sem caso facultativo.
- **A conferência:** 8 agentes escreveram e outros 8 julgaram às cegas: 0
  divergência nos 788; 4 itens reescritos por cautela.
- **A ordem no botão "IA":** das nunca feitas, o Certo/Errado vem antes da
  múltipla escolha herdada da PMSC (até 92 num tema só), e a rodada de vários
  nós dá primeiro o C/E de todos eles. Sem isso, o botão da aula do art. 5º
  traria quase só múltipla escolha.

## O Ciclo 2 (PRF-43, 26/11/2026)

**1.685 itens** em Raciocínio (375), Física (507), Espanhol (208), Informática
(88), Geopolítica (287) e Ética (220). Só a Ética tem lei (os nós dela no
`textos_de_lei.yml`). Nas outras, o item traz todos os dados e a conta foi
refeita em Python por quem escreveu e por quem julgou; o Espanhol é, como no
Cebraspe, um item em português sobre um trecho em espanhol, escrito no próprio
enunciado; Geopolítica sem número do IBGE; Informática sem menu nem versão.
0 divergência de gabarito na conferência às cegas. Na tela, o "apoio" do item
de Certo/Errado (o campo `artigo`) só aparece depois da resposta: sem lei, ele
dizia a regra e entregava o gabarito.

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

# Pedido PRF (24/11/2026)

Policial Rodoviario Federal. O edital novo esta previsto para 2027 e ainda
nao saiu: ate la vale o de 2021 (Cebraspe), que esta nesta pasta. O
cronograma ainda nao tem data para comecar, mas quero montar agora a
estrutura, os dados e as analises.

O codigo veio do radar da PMSC. **Quero o mesmo layout, a mesma tela Hoje, o
mesmo treino, simulado e caderno de erros**, adaptados para a PRF. Tudo o que
e da PM e da Policia Penal sai da tela; as questoes servem onde a materia for
do edital da PRF.

Uma etapa por conversa, e cada uma espera o meu aval:

0. **Isolamento.** O sistema rodando na porta 8002, com "MODO PRF" na tela, a
   config em `prf/config/`, o diario zerado e nada da PMSC aparecendo.
1. **O edital de 2021.** Materias, pesos, numero de itens e a arvore de
   conteudos. E a **ordem de prioridade das disciplinas**: pelo peso no edital
   e por quanto cada uma caiu nas provas do Cebraspe que temos, com o numero
   de cada.
2. **A pasta `PRF/`.** O que o meu script faz, se da para usa-lo de novo
   (respeitando o robots.txt e os termos do Cebraspe), e importar as questoes
   com gabarito definitivo.
3. **As questoes herdadas.** Do `fontes/radar_pmsc.db` ficam so as das
   materias do edital da PRF; o resto sai do banco de trabalho (a fonte fica
   intocada). O que nao serve nao fica para a IA ler.
4. **O Certo/Errado como formato principal.** Nota liquida (uma errada anula
   uma certa) e a **regra do chute**: quando chutar e quando deixar em branco,
   e se o Cebraspe costuma dar mais Certo ou mais Errado, contado nas provas
   que temos. **Nas questoes e nos simulados, quando eu marcar "chute" e
   errar, esse erro nao entra no acervo** (na Etapa 4, confirmar comigo onde
   ele fica de fora: na nota, no caderno de erros, no desempenho por assunto).
5. **O metodo e o cronograma.** O que a pesquisa diz sobre como estudar para
   prova (com as fontes) e o cronograma montado em cima disso e da prioridade
   da etapa 1, com a data de inicio em aberto.

Tudo com numero e fonte, nunca de memoria.

Repositorio: https://github.com/Gabrielrosasilva/projeto-concurso-prf

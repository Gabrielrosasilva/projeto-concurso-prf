# As explicacoes das questoes reais da Cebraspe (PRF-56, 27/11/2026)

Das 1.914 questoes reais de Certo/Errado da Cebraspe no estoque, 1.893 tem a
explicacao em partes (o porque, o que cobra, o trecho da lei conferido, a
pegadinha e, no item errado, o "como ficaria certo"). Este lote escreveu 1.798
(`radar gerar --pedido --explicacoes --quais todas`, so as de Certo/Errado),
por 12 agentes do Claude Code (claude-opus-5-5), com o texto de `leis/`. O
gabarito oficial nunca muda: a explicacao que discorda nao entra.

Ficaram sem explicacao 27 itens, de proposito (discordancia, dado faltando ou
montado de memoria). O que os agentes acharam e precisa de conferencia:

## Gabarito suspeito (o texto do item traz "JUSTIFICATIVA - CERTO" e o gravado e E)
- CEBRASPE 2019 Escrivao de Policia q70 (questao id 24067), Penal.
- CEBRASPE s/a Defensor Publico q90 (id 22673), Processo Penal. (Ja estava na lista do estado.)

## Lei que mudou depois da prova (a explicacao avisa; falta o aviso na questao ou tirar do treino)
- id 23167 (Delegado q106): captacao ambiental hoje exige autorizacao judicial (Lei 13.964/2019, art. 8o-A da Lei 9.296, que nao esta em `leis/`).
- id 22849 (Escrivao 2021 q88): o estelionato deixou de depender de representacao (art. 171, § 5o revogado pela Lei 15.397/2026).
- id 22801 (Agente 2021 q81): ameaca contra a mulher e incondicionada (Lei 14.994/2024).
- id 23163 (Delegado q96) e id 22838 (Escrivao 2021 q77): feminicidio virou crime autonomo (CP, art. 121-A).
- id 25239 (Agente Federal de Execucao Penal 2021 q44): a dispensa para reforma de estabelecimento penal (Lei 8.666) nao foi repetida na 14.133.
- id 22523 (DETRAN/AL 2026 q70): a Res. 809/2020 foi revogada pela 1.027/2026, que inverte o gabarito.

## Discordancias (o agente nao concordou ou nao teve fonte segura)
- id 24141 (PF 2018 Papiloscopista q35): inquerito "por portaria" num caso de flagrante.
- id 25349 (Papiloscopista 2023 q36): trajeto de saida do local de crime, que nenhuma lei regula.
- id 24445 (Tecnico de Laboratorio 2016 q52): a variacao total da energia cinetica do teste e zero.
- id 24622 (CBM 2021 q27): 16 acidentes em PA; o C so sai se o 10o for o primeiro termo.
- id 24116 (PF 2018 Papiloscopista q10) e id 25542 (ABIN 2018 q14): o erro do item nao fica claro.
- id 22430 (Especialista em Regulacao q102): a figura do modelo nao veio.
- id 24159 (PF 2018 Papiloscopista q72): "permitem" plugins antiphishing.
- id 23881 (CFP 2021 q3): "precaucao" no uso da forca, sem fonte local.
- id 23186 (Agente de Policia Judiciaria 2021 q32): lei estadual 2.148/1977, que nao esta em `leis/`.

## Dados das questoes que estao errados no banco
- Texto-base trocado: PF 2018 Agente, as do Nudetective, com o texto de Edgar Allan Poe; PF 2018 Papiloscopista com o de Marcelo Gleiser (e, em 5 delas, sem o comando "seriam preservadas se"). Aparece assim na tela.
- Sem texto-base: varias da PF 2018 (Raciocinio e Portugues), PM/AL 2017 e 2021, CBM/AL 2017 e 2021, TRF1 2017, DETRAN/AL 2026 (tabela), PF 2021 (o conjunto P). O caderno da PF 2018 Agente de Raciocinio nao esta no projeto: 8 itens ficaram sem explicacao.
- Texto de outra questao colado no enunciado: ids das provas da PCDF 2021 (cabecalho "Matriz_CE PCDF-ESC 2021"), Lei estadual 6.754/2006, um trecho do Manual de Redacao, um de estatistica.
- Materia errada: 5 de Raciocinio gravadas como Portugues; 7 de Penal/Processo Penal como Constitucional.
- Cerca de 20 itens de INGLES em "Lingua Estrangeira" (o radar treina espanhol): entram no Simulado e nas faixas de Espanhol.
- Itens repetidos (o mesmo item duas vezes): 4 pares em Informatica e Portugues.
- Figuras que nao vieram: a tirinha de Portugues, icones de Informatica, as lampadas de Raciocinio.

## Fonte de memoria, por conferir
- Umas 25 explicacoes de Direito citam sumula, tema ou decisao do STF/STJ (SV 11, 13 e 37; Temas 130, 362, 532, 784, 940; RE 669.367; ARE 654.432...): o item real depende delas e o texto nao esta guardado.
- 10 explicacoes do Manual de Redacao (regras classicas; o Manual nao esta em `leis/`).
- O `trecho_na_lei` so le `.htm`: os trechos das resolucoes do CONTRAN e da DUDH (`.txt`) nao sao conferidos e saem.

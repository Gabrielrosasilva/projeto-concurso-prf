# Estado - 26/11/2026

Etapas 0 a 5 feitas, com a classificacao do Cebraspe, os levantamentos 1 e 2 (PRF-26, PRF-30, PRF-32), a explicacao com a Revisao do simulado (PRF-33), a analise dos aprovados (PRF-34), o cronograma em dois ciclos (PRF-38), as fichas e resumos do Ciclo 1 (PRF-39) e o Certo/Errado da IA no Transito (PRF-40) e nas outras materias do Ciclo 1 (PRF-41); tudo espera o aval do Gabriel.

## O que roda
- `radar subir` na 8002, com "MODO PRF". Config em `PRF/config/` (pelo `.env`), sem Telegram.
- Diario zerado (PRF-4). Arvore do edital de 2021 + os 22 capitulos do CTB + os nos da classificacao: 638 (PRF-6, PRF-17, PRF-32).
- Questoes: 10.259. Da PRF/: 245 do alvo (com as 8 de espanhol, PRF-24) e 1.693 complementares (PRF-16, PRF-19); dos levantamentos do Cebraspe, 97 (PRF-26) e 758 (PRF-32, provas de policia) complementares. Herdadas da PMSC: ficaram 7.466 de 16.317 (PRF-21, PRF-23): 476 do Cebraspe (complementar) e 6.990 de outras bancas (fora: treinam, nao medem).
- Geradas por IA: 3.081. 1.677 de Certo/Errado com a explicacao (`radar gerar --pedido --certo-errado`): 889 do Transito (PRF-40) e 788 das outras materias do Ciclo 1 (PRF-41), toda aula com ficha com 35 itens de treino, menos 3 (em Falta); e 1.404 de multipla escolha herdadas da PMSC, que o botao "IA" da depois do C/E. Fichas 214: 79 das 80 aulas do Ciclo 1 com ficha e resumo (PRF-36, PRF-39); macetes 45, glossario 462. Explicacoes 734 (PRF-33).
- Certo/Errado (PRF-28, `docs/certo_errado.md`): em branco, nota liquida, chute fora do desempenho por assunto; Analises > Certo/Errado e `radar chute`. 2.018 itens C/E unicos (alvo + complementar).
- Cronograma (PRF-35, PRF-38, `docs/metodo.md`): 16 semanas, 04/01 a 24/04/2027, em `PRF/config/cronograma.yml`, gerado por `PRF/cronograma/gerar_cronograma.py`. Ciclo 1 (ate 27/02): Transito, Portugues e os Direitos; Ciclo 2: Espanhol, Informatica, Raciocinio, Fisica, Etica e Geopolitica, com manutencao do Ciclo 1 toda manha. Diagnostico em 09/01, fechamento em 24/04.
- Documentos: `docs/edital.md`, `docs/prioridade.md`, `docs/script_prf.md`, `docs/certo_errado.md`, `docs/dados_cronograma.md`, `docs/comparativo_pmsc_prf.md`, `docs/aprovados_prf.md`, `docs/metodo.md` e `docs/resolucoes_contran.md`. Redacao no criterio do Cebraspe, 10 temas (PRF-37, PRF-38). Leis locais em `leis/` (fora do git; os links nos dois manifestos).

## Para o Gabriel conferir
- O cronograma novo (Hoje: `/hoje?data=2027-01-04`, `2027-03-01`) e `docs/metodo.md`; a aba Redacao (10 temas, modelos, NC estimada).
- Os 1.677 itens C/E da IA (botao "IA · N" da faixa; "essa questao esta errada" tira do sorteio). Os 21 do MBFT usam a Parte Geral de 2022: os anexos da 1.009/2024 e da 1.012/2024 nao foram baixados.
- As fichas e os resumos (🟣 nao conferidos; `radar fichas --conferir <tema>` e `--conferir-resumo`). Jurisprudencia citada de memoria em 14 fichas, marcada "por conferir" em `por_que_estes_nos`. Na ficha de Regencia e crase (herdada), "assistir" e "visar" estao mais restritos que o Manual de Redacao; o resumo segue o Manual.
- As pendentes (Analises > Conferencia): 14 do alvo, 124 do complementar; 3 do alvo de lei mudada (PRF-33) e ~400 herdadas que ja eram pendentes na PMSC.
- Gabaritos suspeitos (nada trocado): 2023-q2215611 e 2023-q2048199 (Penal, Qconcursos herdado), CEBRASPE-2026-q4202899 (concussao x prevaricacao), CEBRASPE-2021-q58 (dispensa de exatamente R$ 100 mil), CEBRASPE-s/a-q90 (justificativa contradiz o gabarito). Classificacao: o 2021-q112 e da Lei 12.037, art. 3º, V (nao IV); a justificativa do CEBRASPE-2019-q80 cita o art. 89, § 4º, da Lei 9.099 (e o § 3º).

## Falta
- A Lei 10.826/2003 (aula de 28/01): salvar a pagina do texto compilado (Planalto ou Senado, a mao) em `leis/`, e eu faco a ficha.
- As fichas e os resumos do Ciclo 2 (57 aulas sem ficha), antes de 01/03.
- C/E da IA que faltou (PRF-41): Correspondencia oficial (8; o Manual de Redacao da Presidencia, salvo a mao em `leis/`), Poder constituinte (5) e Principios basicos (2), que o texto nao deu sem doutrina.
- Codigo ambiguo do complementar: o mesmo ano e numero em provas diferentes ("CEBRASPE-2021-q2" em 3 questoes; falta a `sigla` na lista de provas). Duas anotacoes do CONTRAN velhas (pelicula, medidor de velocidade).
- Leitor de C/E (PRF-32): comando sem "julgue", lixo da capa, itens de lingua dos cadernos de duas linguas, Petrobras 2023, cadernos sem recuo. Explicacao: o resto e a da multipla escolha. Sem no: 363 de multipla escolha do complementar e 1.128 herdadas.
- Ainda da PMSC/PP: o cartao "Sobre o chute" dos Macetes (letras A-E) e a frase da tela Certo ou Errado ("a prova da PMSC e de multipla escolha"). Concursos e Acompanhando vazias (PRF-22).

## Testes
- Leem um espelho do `data/` (PRF-9); `tests/test_cronograma_prf.py` le o `PRF/config/cronograma.yml` e o `data/fichas.json`. Falha desde antes (procura `pmsc/config/`): `test_simulado_da_semana::test_a_tela_do_dia_real_nao_manda_ao_qconcursos`.

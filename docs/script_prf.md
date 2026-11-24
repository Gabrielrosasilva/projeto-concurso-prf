# A pasta PRF/ e o script de 13/11/2026

Etapa 2, 24/11/2026. Os 15 `.py` de `PRF/` foram lidos (sem rodar nada); os
sites foram conferidos nesse dia.

## O que o script faz

Rodou de 13/11 21:08 a 14/11 04:19, em quatro frentes:

| Frente | Scripts | Como | O que trouxe |
|---|---|---|---|
| PDFs do Cebraspe | `baixar_arquivos.py`, com as filas de `montar_fila_bloco2/3.py` e `preparar_downloads_origens.py` | `requests` | 351 PDFs de cdn.cebraspe.org.br; até 39 consultas a apis.cebraspe.org.br/cebraspe/eventos/{slug} para achar os nomes dos arquivos |
| Lista de provas e metadados do Qconcursos | `listar_origens_qconcursos.py`, `listar_provas_fundatec.py`, `coletar_metadados.py` | navegador de verdade (Selenium + Chrome, perfil guardado) | ao menos ~1.085 páginas; 3.841 questões com ID, classificação e prova (sem enunciado) |
| PDFs pelo Qconcursos | `baixar_arquivos.py` com `fila_bloco4_*.json` | `requests` | 82 PDFs de arquivos.qconcursos.com (FUNDATEC, IBFC, IDECAN): a FUNDATEC respondeu HTTP 202 à leitura automática e o script trocou de fonte |
| Conferência local | `auditar_gabaritos.py`, `validar_entrega.py`, `gerar_relatorio.py` | sem rede | `RELATORIO.md`, `validacao_final.json` (437 PDFs válidos, 1 falha 403) |

## Respeita o robots.txt e os termos?

- **Nenhum script lê o robots.txt.** O `baixar_arquivos.py` se apresenta como
  "Mozilla/5.0" (linha 43) e não espera entre um download e outro (cerca de 1
  por segundo, pelos horários do inventário).
- **Cebraspe:** o robots.txt de www.cebraspe.org.br libera tudo (`Disallow:`
  vazio); cdn.cebraspe.org.br e apis.cebraspe.org.br não têm robots.txt (404),
  e então nada é proibido. O site não publica termos de uso: o sitemap tem 37
  páginas, e as de LGPD, perguntas frequentes e transparência não falam de
  reprodução nem de robô. 12 dos 115 cadernos importáveis dizem "É permitida a
  reprodução deste material apenas para fins didáticos, desde que citada a
  fonte"; os da PRF de 2019 e 2021 não trazem a frase.
- **Qconcursos:** a regra 4 do CLAUDE.md o tira de robô, e o site barra robô:
  responde 403 com o desafio da Cloudflare (nem o robots.txt sai). Dois
  scripts param para uma pessoa resolver o desafio na janela do Chrome e
  seguem automáticos depois.

## Dá para usar de novo?

- **A parte do Qconcursos: não.** É robô num site que a regra 4 proíbe e que
  barra robô. E nem roda aqui: os 4 scripts de navegador importam
  `coletar_questoes.py` e usam os perfis `.chrome-questoes` e
  `.chrome-prf-metadata`, que não estão nesta pasta.
- **A parte do Cebraspe: sim, mas pelo radar.** O manifesto `data/provas.json`
  guarda o link original de cada PDF importado, e o `radar baixar-provas`
  refaz o acervo pelo Buscador do radar, que se identifica, lê o robots.txt e
  espera entre os pedidos. Prova nova do Cebraspe entra pela lista
  `PRF/config/provas_de_outras_bancas.yml` (`radar provas --outras-bancas`,
  depois `radar questoes --banca CEBRASPE`).
- O `baixar_arquivos.py` só serviria trocando o "Mozilla/5.0" pelo User-Agent
  do radar e pondo a pausa e o robots.txt - que é o que o radar já faz.

## O que entrou no radar

Os cadernos do Cebraspe com gabarito DEFINITIVO, lidos pelo radar, sem rede
(os PDFs vieram de `PRF/` para `data/provas/manual/`, fora do git). As
contagens estão em `docs/estado.md` e na decisão PRF-12.

Ficaram de fora:
- os 23 cadernos de outras bancas que vieram pelo Qconcursos (regra 4: o
  `radar baixar-provas` iria buscá-los lá);
- os 10 sem gabarito definitivo (entre eles as 3 provas do Curso de Formação
  da PRF de 2021 e 2022, só com o preliminar);
- 26 do Cebraspe que o radar não leu ou cujo gabarito não casou: 19 num
  formato que o radar ainda não lê - múltipla escolha antiga, ou caderno que
  mistura os dois formatos (CESPE 2017–2023: juiz, promotor, defensor,
  delegado e prefeituras); DEPEN 2020 (três gabaritos para um
  caderno); PCDF 2020 básicos, sem o gabarito dele; PF 2025 blocos I e II e
  DETRAN-AL 2026 básicos (várias grades num PDF só); PC-PB 2021 agente e
  Polícia Penal PE 2021 (o gabarito não casou com 100 questões).

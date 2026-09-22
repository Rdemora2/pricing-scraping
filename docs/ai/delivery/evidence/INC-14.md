# Evidência INC-14 — profundidade por variante

## Escopo e estado

- Branch: `feature/inc-14-depth-per-variant`, empilhada sobre `70ca0ac`.
- Estado: `LOCAL_VERIFIED_WITH_EXTERNAL_GATE`.
- Objetivo: aumentar varejistas distintos por `(aparelho, capacidade, cor)`,
  sem relaxar identidade de variante e sem contornar política de acesso.

## Critérios de aceite

1. O teto de ofertas de agregador deixa de truncar a amostra onde ele morde.
2. Toda perda de coleta passa a ser contável e atribuível a uma etapa.
3. Pelo menos uma perda real identificada pela quarentena é recuperada.
4. Nenhuma alteração relaxa identidade de variante nem política de acesso.

## Implementação

### Teto de agregador e paginação (critério 1)

`MAX_AGGREGATE_OFFERS` passou de `20` para `60`
(`collection/real_sources.py`), valendo também para Zoom e Americanas. O
Buscapé passou a seguir até `BUSCAPE_MAX_OFFER_PAGES = 3` páginas do documento
público de ofertas, parando numa página curta. A decisão de paginar usa a
contagem de `hits` brutos, não de listagens mantidas: uma página cheia de
ofertas de outros modelos ainda pode preceder o varejista procurado.
`CLOSESPIDER_PAGECOUNT` do Buscapé foi reajustado de `80` para `160`
(4 buscas + 4×8 páginas de produto + 32×3 documentos de oferta + 2 robots.txt
= 134, com folga para redirects).

### Funil instrumentado (critério 2)

Antes, o único sinal por execução era `offers_observed`. Varejista perdido por
bloqueio HTTP, por markup alterado ou por título sem cor reconhecida virava uma
linha de log dentro de um subprocesso.

- nova tabela `listing_rejection` (migração `c3a71f5d8e04`) com estágio
  `access`/`extraction`/`matching`, motivo, URL, título bruto e atributos;
- `SkipLog` opcional nos extratores multi-oferta (Zoom, Buscapé, Samsung Shop,
  iPlace): a política fail-closed é idêntica, só deixa de ser invisível;
- spiders emitem `ListingRejectedItem` em recusa HTTP, falha terminal de
  extração e busca renderizada sem produto;
- o pipeline registra também a oferta que não casa com variante canônica, com
  assinatura e atributos;
- `get_run_stats` expõe `listings_rejected_access/extraction/matching`.

### Recuperação dirigida pela quarentena (critério 3)

A primeira execução instrumentada do Buscapé para o iPhone 17 Pro Max gravou 5
descartes com a mesma causa: `Laranja`, `Laranja-cósmica` e o inglês `Blue` não
resolviam, embora `prata` e `azul` já tivessem alias na mesma família. Cada um
desses termos corresponde a exatamente uma cor do catálogo deste modelo, logo o
alias normaliza grafia sem relaxar identidade.

## Evidência executada

Stack local via `docker compose`, Postgres com histórico preservado.

- migração aplicada: `alembic_version = c3a71f5d8e04`; `\d listing_rejection`
  confirma tipo `rejection_stage`, ambas as FKs `ON DELETE CASCADE` e os dois
  índices;
- **Buscapé / Galaxy S25 Ultra**, run `fcb06bba-c3d9-480b-b28e-8e065c7c540c`:
  `29` observações. Baseline do INC-09 para o mesmo par: exatamente `20`, que
  era o `pageSize` pedido — o teto mordia, e deixou de morder (**+45%**);
- **Buscapé / iPhone 17 Pro Max**, run `d046c0a0-2992-4dbf-ac4b-cf2d52010858`:
  `51` observações e `5` descartes de extração, todos por grafia de cor;
- mesmo par após os aliases, run `1b49ac3b-d0f5-47ab-8d80-1222858d6dcb`:
  `56` observações e `0` descartes — as 5 perdas recuperadas;
- leitura consolidada do iPhone 17 Pro Max com **uma única fonte**: cobertura
  `12/12` (100%), `56` ofertas, `17` varejistas distintos, amostra `strong`.
  A execução de referência registrada no README precisava de cinco fontes para
  chegar a `54` ofertas e `17` varejistas;
- runtime local: `uv run pytest` `194 passados`, `ruff check`,
  `ruff format --check` e `ty check` verdes;
- `docker compose --profile test run --rm test pytest tests/integration`:
  `2 passados`.

## Rota do Carrefour avaliada e descartada

O `robots.txt` do Carrefour proíbe `/busca/` e publica
`Sitemap: https://www.carrefour.com.br/sitemap.xml`. A implementação por
sitemap foi construída, testada e então **revertida** (`928e771`) após medição
do documento real: índice com `5305` documentos, `5290` deles `product-N.xml`
com `1000` URLs cada — cerca de `5,29` milhões de URLs sem ordenação por marca
ou categoria, misturando filtro de água, cooktop e conector RJ45 no mesmo
documento; e o marcador real de produto é `/p`, não `/produto/`. Localizar um
aparelho exigiria varredura de milhões de URLs. Sem consumidor viável, a
máquina genérica saiu junto, para não deixar subsistema morto. Próxima rota
candidata: navegação por categoria, que o `robots.txt` não proíbe.

## Riscos

- a paginação do Buscapé aumenta o volume de requisições por execução; o
  orçamento de páginas e o `CLOSESPIDER_TIMEOUT` de 300s continuam sendo o
  limite, e AutoThrottle segue ativo;
- `MAX_AGGREGATE_OFFERS = 60` é um limite defensivo contra payload hostil, não
  uma promessa de que a fonte publique 60 ofertas;
- aliases de cor são decisão de dado: cada entrada precisa corresponder a
  exatamente uma cor do catálogo daquele modelo. `Titânio Jetblack` do Galaxy
  S25 Ultra ficou **sem** alias e permanece na quarentena, porque o mapeamento
  para uma das cores do catálogo não é verificável localmente;
- títulos que não nomeiam cor continuam recusados por desenho; o volume deles
  agora é visível e não deve ser interpretado como falha da fonte.

## Rollback

Voltar ao commit anterior e reconstruir as imagens. A migração
`c3a71f5d8e04` possui `downgrade`, que remove `listing_rejection` e o tipo
`rejection_stage`; nenhum dado de oferta, observação ou evidência depende dela.

# INC-13 — corrigir teto de cores por busca de capacidade

## Readback remoto

- PR: [#15](https://github.com/Rdemora2/pricing-scraping/pull/15).
- `mergeable: MERGEABLE`, `mergeStateStatus: CLEAN` relidos imediatamente
  antes da decisão de merge.
- Método: squash-merge, `--match-head-commit`. Commit resultante em `main`:
  `341d9e8`.
- `main` local sincronizada via `python3 .codex/safe_git_sync.py sync-main`.

## Escopo e aceite

- Branch: `feature/inc-13-expand-color-capacity-discovery`.
- Baseline: `main` pós-INC-12 (`96277d2` + PR #14).
- Objetivo: investigar, com a stack local rodando de verdade, onde a
  diversidade de capacidade/cor está sendo perdida nas fontes já habilitadas
  (Zoom, Buscapé, KaBuM!, Americanas, Samsung Shop) e corrigir a causa real.
- Aceite: achado confirmado por leitura de código E por execução real do
  pipeline completo (antes/depois), correção com teste de regressão, sem
  tocar `robots.txt`, CAPTCHA, fingerprint ou qualquer das exclusões da ADR
  0001.

## Achado

`MAX_SEARCH_RESULTS_PER_CAPACITY = 3` (`collection/real_sources.py`) limita
quantas páginas de produto (uma por cor) `extract_product_search_urls` segue
por busca de uma capacidade de armazenamento. Consultando o catálogo real via
API (`GET /products` + `GET /products/{id}/variants`), **15 dos 18 aparelhos
têm mais de 3 cores** — a família Galaxy S26 tem 6. O teto de 3 corresponde
exatamente ao número de cores do iPhone 17 Pro Max (o caso de referência
histórico do projeto), sem nenhum comentário ou teste justificando o valor
para o restante do catálogo — nenhum teste existente exercitava mais de 3
URLs candidatas. Toda fonte que descobre produtos por busca (Zoom, Buscapé,
KaBuM!, Americanas, Bondfaro) usa essa mesma função; Samsung Shop não é
afetado (resolve o modelo canônico diretamente, sem busca).

## Correção

- `MAX_SEARCH_RESULTS_PER_CAPACITY`: `3` → `8` (máximo real do catálogo é 6,
  +2 de margem para crescimento próximo do catálogo).
- `CLOSESPIDER_PAGECOUNT` ajustado proporcionalmente em `ZoomSpider` (20→40),
  `BuscapeSpider` (32→80, tem uma requisição extra de documento de oferta por
  página de produto), `KabumSpider` (24→48) e `BondfaroSpider` (20→40, hoje
  `candidate`, mesma lógica) para o novo teto não ser cortado pelo orçamento
  de páginas antes de completar. `AmericanasSpider` (40→56) por segurança —
  seu teto anterior já estava próximo do necessário.
- `tests/unit/test_real_sources.py`: novo teste com uma busca listando as 6
  cores reais do Galaxy S26 Ultra, afirmando que todas as 6 URLs são
  retornadas (não mais truncadas em 3).

## Evidência real (pipeline completo, não só teste unitário)

Antes de qualquer coleta com a correção, Galaxy S26 Ultra nunca havia sido
coletado nesta stack. Sequência completa após rebuild do `worker`:

1. Zoom sozinho: `succeeded`, `offers_observed=4`. Inteligência do produto
   (`GET /products/043416ac.../intelligence`) já mostrou as **6 cores**
   (`Azul, Branco, Dourado, Prata, Preto, Violeta`) numa única fonte — com o
   teto antigo de 3, isso seria estruturalmente impossível independente de
   quantas fontes fossem consultadas.
2. Buscapé (+15), KaBuM! (+7), Samsung Shop (+6) — todos `succeeded`.
3. Estado final consolidado: `catalog_variant_count=18`,
   `observed_variant_count=11` (61%), `total_offer_count=25`,
   `retailer_count=11`, as 6 cores presentes. As combinações de 1TB ficaram
   com 0 ofertas em todas as cores — leitura mais provável é escassez real
   de mercado para o tier de armazenamento mais alto de um aparelho muito
   recente, não lacuna de coleta (256GB e 512GB têm cobertura real em todas
   as 6 cores).

## Revisão independente

Agente `reviewer` aprovou localmente. Confirmou por leitura direta do código:
sem off-by-one no corte (`results.append` ocorre antes do `break`, 8
resultados reais com `MAX=8`); nenhum spider fica estruturalmente limitado a
cortar a coleta pela metade no pior caso real do catálogo (Galaxy S26 Ultra,
3 capacidades × 8 = 24 páginas de produto, todos os orçamentos revisados têm
folga); as quatro exclusões da ADR 0001 intactas (`validate_reference_url`
continua chamado por URL, nenhuma mudança em `robots.txt`/CAPTCHA/fallback em
resposta a erro); teste novo é genuíno (teria falhado com o teto antigo de
3); Amazon/Carrefour corretamente fora de escopo (`status="candidate"` por
motivo não relacionado). Observação não bloqueante registrada: o fallback de
`AmericanasSpider` por falha de extração (pré-existente, não alterado por
este diff) poderia, em cenário patológico com todas as páginas falhando
extração, somar-se ao orçamento e ultrapassar `CLOSESPIDER_PAGECOUNT=56` —
risco proporcional ao aumento 3→8, não uma regressão desta entrega; fica
como acompanhamento futuro, não bloqueia esta correção de constante.

## Evidência local (suíte)

- `uv run pytest -q`: `180 passed, 2 skipped` (1 teste novo);
- `uv run ruff check .` / `uv run ruff format --check .`: verdes;
- `uv run ty check .`: verde.

## Riscos e rollback

- Risco classificado **Médio** (ajuste de constante/orçamento em adapters já
  revisados, sem novo host, dependência, egress ou mudança de política de
  bloqueio/robots.txt/CAPTCHA).
- Efeito colateral esperado e aceito: mais páginas por execução de coleta
  (até ~2,7x no pior caso por fonte) para aparelhos com mais de 3 cores;
  ainda bem abaixo de qualquer teto de paciência humana e dentro do
  orçamento de `CLOSESPIDER_PAGECOUNT` ajustado.
- Rollback: reverter `MAX_SEARCH_RESULTS_PER_CAPACITY` para `3` e os
  `CLOSESPIDER_PAGECOUNT` para os valores anteriores em
  `collection/spiders/retail.py`. Sem migração, sem dependência nova.

# INC-12 — iPlace via fallback de navegador; avaliação de Casas Bahia/Ponto/Extra/Magalu/TerabyteShop/Pichau

## Readback remoto

- PR: [#12](https://github.com/Rdemora2/pricing-scraping/pull/12).
- `reviewDecision` vazio, `mergeable: MERGEABLE`, `mergeStateStatus: CLEAN`
  relidos imediatamente antes da decisão de merge.
- Método: squash-merge, `--match-head-commit`. Commit resultante em `main`:
  `20a8e74`.
- `main` local sincronizada via `python3 .codex/safe_git_sync.py sync-main`.

## Escopo e aceite

- Branch: `feature/inc-12-iplace-browser-fallback` (a criar).
- Baseline: `335f2a5` (head de `main` após INC-11).
- Objetivo: usando o perfil HTTP do `INC-11`, avaliar se seis fontes hoje
  `candidate` (Casas Bahia, Ponto, Extra, Magalu, TerabyteShop, Pichau)
  passam a produzir preço real, e revalidar iPlace.
- Aceite: decisão por fonte sustentada por evidência reproduzível (não
  suposição), dentro das quatro exclusões da ADR 0001 (sem contornar
  `robots.txt`, sem CAPTCHA, sem fingerprint TLS/JA3, sem mascarar sinais de
  automação como `navigator.webdriver`).

## Investigação — fontes descartadas

Metodologia: para cada fonte, (1) checar `robots.txt` e sitemap com o
User-Agent real do `INC-11`; (2) inspecionar a página de categoria/produto
real, com URL real quando fornecida pelo usuário; (3) para as que pareciam
abrir, testar se o dado que falta (preço) está em algum endpoint alcançável;
(4) quando plausível, testar o Playwright já existente **sem nenhuma
modificação** contra a mesma URL.

- **Casas Bahia / Ponto / Extra** (mesma plataforma Next.js, mesmo
  `robots.txt`, mesma URL de categoria `/c/telefones-e-celulares?filtro=categoria-c38`):
  categoria abre (200, JSON real de SKU/título/marca em `__NEXT_DATA__`).
  Página de produto individual (`/p/...`) retorna 403 confirmado com SKUs
  reais fornecidos pelo usuário. `robots.txt` proíbe explicitamente
  `*/pdp-api`. O `initialState.price` da própria categoria chega
  `{"loading": true, "prices": [], "newPrices": []}` — preço é
  deliberadamente omitido do HTML e carregado por cliente.

  Dois experimentos ad-hoc distintos foram rodados contra Casas Bahia, **nenhum
  deles com a configuração de produção completa** (nenhum aplicou
  `install_browser_request_policy`, o guard fail-closed de host que o
  `IPlaceSpider` desta entrega usa de verdade):
  1. Captura de tráfego de rede (Playwright, sem bloqueio de host,
     deliberadamente desativado para observar tudo) durante o carregamento
     mostrou POSTs para endpoints ofuscados, característicos de telemetria
     comportamental Akamai (nomes de path aleatórios por sessão).
  2. Teste decisivo, separado: Playwright básico (`p.chromium.launch(headless=True)`,
     contexto só com `locale`/`timezone_id`, sem `install_browser_request_policy`
     e sem nenhuma tentativa de stealth) navegando para a mesma categoria
     retornou **HTTP 403 imediato**, com `navigator.webdriver: True` como o
     sinal — a flag padrão de qualquer framework de automação, e o primeiro
     sinal que WAFs decentes checam. Esse resultado independe de bloqueio de
     host (a flag é do browser, não da política de rede), então é
     representativo do que a configuração de produção também exibiria.
     Corrigir isso exigiria mascarar essa flag, o primeiro passo nomeado de
     "stealth scraping". Não feito.
- **Magalu**: raiz abre (200). URL real de busca por produto, obtida
  navegando o site de verdade (`/iphone-17-pro-max/celulares-e-smartphones/s/te/17pm/`),
  retorna 403 via requisição HTTP simples — página de erro com a marca
  "akamai-bot" própria da Magalu. Não é chute de URL errado (diferente de
  uma tentativa anterior nesta mesma investigação); é bloqueio confirmado na
  URL real.
- **TerabyteShop**: tecnicamente o mais aberto de todos (`robots.txt` permite
  `/produto/`, `/smartphones/`, tem regras dedicadas para bots de IA —
  GPTBot, ClaudeBot etc. — e nenhum bloqueio observado). Sitemap de produtos
  (3957 URLs) não contém nenhum iPhone/Galaxy como produto — só acessórios
  ("capa", "suporte para celular"). É varejista de hardware/PC, não vende os
  aparelhos do catálogo.
- **Pichau**: `robots.txt` proíbe busca por query (`Disallow: /*?*`).
  Categorias tentadas não existem. Mesma classe de loja que TerabyteShop —
  não vende os aparelhos do catálogo.

Nenhuma dessas seis fontes teve seu `adapter_name`/status alterado além do
texto em `docs/source-qualification.md`; nenhum código foi escrito para
elas.

## Implementação — iPlace

- iPlace não bloqueia automação (confirmado: Playwright sem modificação
  recebe HTTP 200, `navigator.webdriver` não é checado ali). A plataforma
  migrou para Oracle Commerce Cloud desde que `extract_iplace_listings` foi
  escrito: `id="root"` vazio em HTTP puro, `Product` JSON-LD só existe após
  render client-side — mas, uma vez renderizado, o JSON-LD tem exatamente a
  forma que `extract_iplace_listings` (inalterado) já espera.
- `IPlaceSpider` (`collection/spiders/retail.py`) ganha
  `browser_fallback_enabled = True` e `browser_allowed_domains =
  ("www.iplace.com.br",)` — testado com a política de bloqueio de host já
  em produção (`install_browser_request_policy`) e **nenhum host de
  terceiros liberado**; a página carregou dezenas de rastreadores de
  terceiros (Google Ads, Facebook, TikTok, Criteo, Hotjar etc.) que nossa
  allowlist já bloqueia por padrão.
- `/searchresults/` é proibido no `robots.txt` do iPlace — `start()` não
  busca; resolve `product_model` contra um mapa de slugs verificados um a
  um em `productSitemap.xml` (atualizado no dia da verificação). Modelo sem
  entrada verificada levanta `ValueError`, mesmo padrão de
  `SamsungShopSpider` para modelo não suportado — nunca um slug adivinhado.
- Seis modelos verificados: `iphone_16_plus`, `iphone_16_pro`,
  `iphone_16_pro_max`, `iphone_17_pro`, `iphone_17_pro_max`, `iphone_air`.
  `iphone_16`, `iphone_17` (base) e `iphone_18_pro`/`iphone_18_pro_max` não
  têm entrada `.../<id>PR` confirmada nesse sitemap no momento da
  verificação — podem não estar à venda no iPlace ainda, ou usar um padrão
  de URL diferente; não foram adivinhados.
- iPlace é revendedor autorizado Apple — não vende Android. Nenhum modelo
  Samsung/Motorola/Xiaomi será mapeado para esta fonte.

## Evidência local

- `uv run pytest -q`: `179 passed, 2 skipped` (8 testes novos: resolução de
  modelo verificado, rejeição de modelo não mapeado, escalada em falha de
  extração, sucesso HTTP sem escalada, bloqueio 401/403/429 sem escalada
  ×3, evidência de fallback no nome do extrator);
- `uv run ruff check .` / `uv run ruff format --check .`: verdes;
- `uv run ty check .`: verde;
- Verificação de campo (fora da suíte, não repetível em CI): requisições
  reais com o perfil de headers do INC-11 contra as 6 fontes descartadas e o
  iPlace. Contra Casas Bahia, um Playwright básico sem `install_browser_
  request_policy` (ver seção anterior) recebeu 403 imediato com
  `navigator.webdriver: True` — resultado independente de bloqueio de host,
  logo representativo da configuração de produção. Contra iPlace, a
  verificação **usou** a política de produção completa
  (`install_browser_request_policy` com `browser_allowed_hosts =
  ("www.iplace.com.br",)`) e obteve 200 com `Product` JSON-LD presente,
  nenhum host de terceiros liberado.

## Riscos e rollback

- `_PRODUCT_SLUGS` é um mapa estático; se o iPlace reestruturar URLs de
  produto, os modelos mapeados passam a falhar com `ExtractionError`
  (tratado) em vez de `ValueError` — comportamento seguro, mas silencioso
  até checar logs.
- Nenhuma promoção de status foi feita — todas as seis fontes descartadas
  permanecem `candidate` com o motivo registrado; iPlace permanece
  `candidate` até uma execução real pelo pipeline completo (worker +
  Postgres) gerar um `run_id` com observações, seguindo a mesma barra que
  toda fonte `enabled` já cumpriu.
- Rollback: reverter `collection/spiders/retail.py` (bloco `IPlaceSpider`) e
  `collection/browser.py` (`BROWSER_FALLBACK_ADAPTERS`). Sem migração, sem
  dependência nova, sem dado persistido.

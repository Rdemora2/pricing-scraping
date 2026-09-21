# INC-11 — perfil HTTP realista de navegador

## Readback remoto

- PR: [#10](https://github.com/Rdemora2/pricing-scraping/pull/10).
- Checks no head `b90724f`: `governance` (pass), `GitGuardian Security
  Checks` (pass) — únicos checks configurados neste repositório; não há
  workflow remoto de teste/lint/build (política local-only do projeto).
- `reviewDecision` vazio (sem review obrigatória configurada), `mergeable:
  MERGEABLE`, `mergeStateStatus: CLEAN` relidos imediatamente antes da
  decisão de merge.
- Método: squash-merge, `--match-head-commit` no SHA acima. Commit resultante
  em `main`: `f094500`.
- `main` local sincronizada via `python3 .codex/safe_git_sync.py sync-main`
  (fast-forward, worktree limpo).

## Escopo e aceite

- Branch: `feature/inc-11-browser-realistic-http-profile`.
- Baseline: `66cc9eb`.
- Objetivo: negociar o perfil HTTP como um Chrome/Windows atual (reduzindo
  bloqueio por sniffing simples de User-Agent/headers) e respeitar
  `Retry-After` em HTTP 429, sem contornar `robots.txt`, CAPTCHA, autenticação
  ou escalar bloqueio para o fallback de navegador.
- Decisão de negócio registrada em
  `docs/ai/decisions/0001-browser-realistic-http-profile.md` (reversão parcial
  do INC-07B, autorizada explicitamente pelo dono do repositório após
  apresentação escrita do trade-off).
- Aceite: `USER_AGENT`/`DEFAULT_REQUEST_HEADERS` realistas e mutuamente
  consistentes (mesma versão de Chrome no UA e no `Sec-CH-UA` no caminho
  HTTP), novo `RetryAfterMiddleware` testado com teto individual e agregado,
  testes/documentação atualizados sem afirmar o contrato antigo, nenhuma das
  quatro exclusões da ADR tocada, achados da revisão independente corrigidos.

## Invariantes

- `robots.txt` continua obedecido (`ROBOTSTXT_OBEY = True`, inalterado);
- 401/403/429/bloqueio de `robots.txt`/falha de transporte continuam sem
  escalar para o fallback Chromium. Cobertura reforçada nesta entrega após a
  revisão de segurança: além do
  `test_browser_fallback.py::test_access_control_error_does_not_trigger_browser_fallback`
  (pré-existente, inalterado), `AmazonSpider`/`CarrefourSpider`/
  `AmericanasSpider.parse_product` e `KabumSpider.parse_search` ganharam
  guarda explícita de status (antes dependiam só do `HttpErrorMiddleware`
  padrão do Scrapy nunca entregar não-2xx ao callback), com testes que
  alimentam 401/403/429 diretamente nos métodos e uma asserção de que
  `HTTPERROR_ALLOW_ALL`/`HTTPERROR_ALLOWED_CODES` não estão configurados;
  `RetryAfterMiddleware` só atua sobre 429, nunca converte outro status em
  retry (`test_retry_policy.py::test_process_request_ignores_retry_after_on_a_non_429_status`);
- nenhum CAPTCHA, fingerprint TLS/JA3 ou rotação de proxy/IP foi adicionado;
- User-Agent e `Sec-CH-UA` declaram a mesma versão de Chrome **no caminho
  HTTP direto**. No fallback Playwright, `user_agent` não é mais sobrescrito
  — corrigido após a revisão de segurança mostrar que overridar só a string
  UA deixava `Sec-CH-UA`/`navigator.userAgentData` (gerados pelo Chromium
  real do Playwright) discordando dela, um sinal de bot pior que não
  sobrescrever nada;
- `Retry-After` tem teto individual de 60s (`MAX_DELAY_SECONDS`) e teto
  agregado por crawl (`CLOSESPIDER_TIMEOUT = 300`, adicionado após a revisão
  de segurança apontar que um host hostil respondendo 429 repetidamente
  poderia, sem esse teto, estender um crawl a dezenas de minutos e travar
  toda a fila de coleta — worker roda uma coleta por vez);
- `parse_retry_after` só aceita `1*DIGIT` ASCII na forma em segundos (RFC
  9110 §10.2.3) — corrigido após a revisão apontar que `str.isdigit()`
  sozinho aceitava dígitos Unicode não decimais que `float()` rejeita;
- `Accept-Encoding` não é hardcodado — permanece delegado ao
  `HttpCompressionMiddleware` do Scrapy, que só anuncia codecs realmente
  decodificáveis por este processo.

## Evidência local

Suíte final, após aplicar as correções da revisão independente:

- `uv run pytest -q`: `171 passed, 2 skipped` (as duas puladas exigem
  `API_BASE_URL`, esperado sem container; 13 testes novos desde a primeira
  rodada: guardas de status em 4 spiders × 3 status + 1 asserção de settings);
- `uv run ruff check .`: `All checks passed!`;
- `uv run ruff format --check .`: `131 files already formatted`;
- `uv run ty check .`: `All checks passed!` (inclui a correção de um erro de
  tipo genuíno que a própria correção do achado M2 introduziu — `ty` recusou
  `"x" not in meta["playwright_context_kwargs"]` porque o valor é
  estaticamente `object`; resolvido removendo a asserção redundante, já
  coberta pela igualdade de dict acima dela).

## Revisão independente

Dois agentes (`reviewer`, `security-reviewer`) revisaram o diff de forma
independente nesta sessão — capacidade que o runtime Codex que produziu
`INC-06`/`INC-07B` não tinha. Ambos ficaram sem `Bash` (limitação do
ambiente do subagente) e por isso não puderam executar a suíte; a análise
foi estática.

**Falso positivo de ambos os agentes**: `except TypeError, ValueError:` sem
parênteses em `retry_policy.py:43`, lido como `SyntaxError` de Python 2.
Investigação direta (não só leitura) confirmou o oposto: `ast.parse` e
`compile()` aceitam o trecho no Python 3.14.7 deste ambiente (com teste de
controle negativo provando que a mesma checagem detecta sintaxe realmente
inválida), e os 12 testes de `test_retry_policy.py` rodam e passam com nomes
visíveis via `pytest -v`. É a forma que `ruff format` (target `py314`)
produziu a partir do código original com parênteses — reescrever de volta só
faria o formatter desfazer no próximo `ruff format .` e arriscaria quebrar
`ruff format --check` no CI. Detalhe completo em
`docs/ai/decisions/0001-browser-realistic-http-profile.md`. Nenhuma mudança
de código a partir deste achado — o restante da avaliação de ambos os
agentes (achado A1, dependente de B1) também não se sustenta.

**Achados reais, corrigidos** (ver "Invariantes" acima para o detalhe
técnico de cada um): teto agregado ausente para `Retry-After` (médio);
mismatch de fingerprint UA/`Sec-CH-UA` no caminho Playwright (médio);
`parse_retry_after` aceitando dígitos Unicode não-ASCII (baixo); lacuna de
defesa em profundidade em quatro métodos de spider que dependiam só do
middleware padrão do Scrapy (baixo); `CHROME_MAJOR_VERSION` desatualizada,
bump de `131` para `139` (informativo).

**Confirmado por ambos os agentes, sem achado**: as quatro exclusões da ADR
seguem íntegras no código, não só na documentação — nenhum caminho onde
401/403/429/`robots.txt` disparasse o fallback Playwright ou um retry
indevido; nenhuma dependência, egress, segredo ou arquivo de fronteira de
confiança (`.codex`, `.agents`, hooks, `compose.yaml`, `Dockerfile`,
`scripts/`) foi tocado.

Pendências que os próprios agentes registraram como não verificáveis sem
`Bash`/rede — não bloqueiam esta entrega, ficam como acompanhamento: prova
empírica dos headers reais emitidos pelo caminho Playwright contra uma fonte
de laboratório; leitura periódica de `CHROME_MAJOR_VERSION` para não
degradar ao longo do tempo.

## Riscos e rollback

- Risco residual não eliminado pela ADR: enviar UA/Client Hints que não
  correspondem à stack real (Scrapy/Twisted no caminho HTTP) é uma
  representação que diverge do cliente real, por decisão de negócio
  explícita — não uma correção técnica neutra. Risco de violação de Termos
  de Uso dos sites-alvo aumenta marginalmente frente ao INC-07B; não avaliado
  por jurídico.
- Efeito prático limitado: fontes bloqueadas por `robots.txt` (Carrefour,
  Fast Shop, Bondfaro) ou por WAF com fingerprint TLS/comportamental (causa
  provável de parte dos HTTP 403 reais em iPlace/Casas Bahia/Ponto/Mercado
  Livre) não mudam de estado só com esta entrega.
- `CHROME_MAJOR_VERSION` (`collection/browser.py`) é um valor fixo que precisa
  de atualização periódica manual; uma versão de Chrome muito desatualizada
  no UA é, em si, um sinal de automação. Não há mecanismo automático de
  atualização nesta entrega.
- Rollback: reverter `collection/browser.py`, `collection/settings.py`,
  `collection/spiders/retail.py`, remover `collection/retry_policy.py` e sua
  entrada em `DOWNLOADER_MIDDLEWARES`. Sem migração de dados, sem dependência
  nova, sem estado persistido — rollback é reversão pura de código.

# ADR 0001 — Perfil HTTP realista de navegador (reversão parcial do INC-07B)

**Data:** 2026-09-21
**Estado:** aceita
**Decisor:** dono do repositório (Roberto Moraes / Valiant Group), autorização
explícita em conversa, após apresentação escrita do trade-off por um agente e
confirmação em duas etapas (escolha entre alternativas com risco explicitado;
confirmação final para implementar).

## Problema

O coletor (`INC-07B`, `docs/ai/delivery/evidence/INC-07B.md`) declarava
identidade automatizada: `USER_AGENT` continha `bot`, sem `Sec-CH-UA`, sem
cabeçalhos de Client Hints, sem negociação equivalente a um navegador atual.
Vários varejistas reais recusam esse tráfego (`docs/source-qualification.md`):
iPlace, Casas Bahia, Ponto, Extra, Pichau, TerabyteShop, JáCotei e Magalu
retornam HTTP 403; Amazon retorna 503. Parte desses bloqueios pode ser
sniffing simples de User-Agent/headers — não todos; ver "Consequências".

O objetivo de negócio é aumentar a cobertura real de varejistas na
inteligência de preços, reduzindo bloqueios que resultam de o coletor
"parecer" automatizado por um perfil de headers incomum, sem contornar
controles de acesso que o site opôs deliberadamente (CAPTCHA, robots.txt,
autenticação).

## Decisão

1. `USER_AGENT` e `DEFAULT_REQUEST_HEADERS`
   (`src/pricing_intel/collection/settings.py`) passam a negociar como um
   Chrome/Windows atual: UA real, `Sec-CH-UA`/`Sec-CH-UA-Mobile`/
   `Sec-CH-UA-Platform` consistentes com a versão declarada no UA,
   `Sec-Fetch-*`, `Upgrade-Insecure-Requests`. `Accept-Encoding` continua
   delegado ao `HttpCompressionMiddleware` do Scrapy (não hardcodado), para
   nunca anunciar suporte a uma codificação que este processo não decodifica.
2. O contexto Playwright (`collection/browser.py`) **não** sobrescreve
   `user_agent` — o Chromium empacotado pelo Playwright gera `Sec-CH-UA` e
   `navigator.userAgentData` a partir do próprio binário; forçar um UA string
   diferente faria os dois discordarem entre si, um sinal de bot mais forte
   do que qualquer um dos dois isoladamente (achado da revisão de segurança,
   ver "Revisão independente"). `BROWSER_USER_AGENT` permanece a identidade
   apenas do caminho HTTP direto.
3. Novo `RetryAfterMiddleware` (`collection/retry_policy.py`) respeita o
   cabeçalho `Retry-After` em HTTP 429 antes do retry padrão do Scrapy, com
   teto individual de 60s e jitter — reduz a chance de um rate-limit
   temporário virar bloqueio permanente por insistência mal cadenciada.
   `CLOSESPIDER_TIMEOUT = 300` (`settings.py`) limita o teto *agregado*: sem
   isso, um host respondendo 429 repetidamente poderia estender um único
   crawl a dezenas de minutos e, como o worker roda uma coleta por vez
   (`compose.yaml`), travar toda a fila (achado da revisão de segurança).
4. `COMPRESSION_ENABLED: False` removido do `AmazonSpider` — a supressão
   deliberada de compressão contradizia o novo objetivo de parecer um
   navegador comum.
5. `parse_retry_after` aceita só `1*DIGIT` ASCII para a forma em segundos
   (RFC 9110 §10.2.3) — `str.isdigit()` sozinho aceita dígitos Unicode não
   decimais (ex. sobrescritos) que `float()` rejeita, o que vazava uma
   exceção não tratada a partir de um header hostil (achado da revisão de
   segurança).

## Fora de escopo (decisão explícita, não descuido)

- **`robots.txt`**: `ROBOTSTXT_OBEY` continua `True`. Não foi solicitado nem
  avaliado neste ciclo; uma mudança aqui precisaria de uma ADR própria.
- **Escalada de bloqueio para navegador**: o fallback Chromium continua
  nascendo somente de uma resposta HTTP *permitida* com evidência
  insuficiente (`test_browser_fallback.py::test_access_control_error_does_not_trigger_browser_fallback`).
  401/403/429/`robots.txt`/falha de transporte nunca acionam o browser.
- **CAPTCHA**: nenhum mecanismo de resolução (OCR, ML, serviço terceiro) foi
  adicionado ou avaliado para adição.
- **Fingerprint TLS/JA3** (`curl_cffi`, `tls-client` ou similares): não
  adotado. O handshake TLS continua o padrão da stack Twisted/OpenSSL do
  Scrapy — só os headers de aplicação (HTTP) mudaram.
- **Rotação de proxy/IP para evadir bloqueio**: não adotado; nenhuma
  dependência de proxy foi introduzida.

Essas quatro exclusões foram mantidas mesmo com a decisão de negócio
autorizando reverter o INC-07B, porque contornam um controle de acesso que o
site-alvo opôs deliberadamente contra automação — diferente de um cabeçalho
HTTP, que é negociação de representação, não uma barreira ativa. Uma extensão
futura para qualquer um desses quatro itens exige nova ADR e aprovação
humana explícita, não decorre desta.

## Alternativas consideradas

| Alternativa | Por que não |
| --- | --- |
| Manter o perfil transparente do INC-07B | Não ataca o problema relatado (sites recusando por parecer bot); mantida como opção B na conversa que originou esta ADR. |
| Reversão completa (headers + fingerprint TLS + rotação de proxy/IP + bypass de CAPTCHA/WAF) | Solicitada inicialmente pelo usuário; recusada pelo agente — contorna controles de acesso de terceiros sem autorização do site-alvo, risco de violação de Termos de Uso não avaliado por jurídico. Ver seção "Fora de escopo". |
| Apenas ampliar `BROWSER_FALLBACK_ADAPTERS` dentro da regra atual (sem tocar headers HTTP) | Ajuda menos o objetivo relatado (a maioria dos bloqueios reais listados é HTTP 403/503/robots.txt em nível de requisição simples, não de renderização JS); permanece como trabalho futuro independente. |
| **Escolhida**: headers/UA realistas + `Retry-After` + manter as quatro exclusões acima | Ataca o sintoma relatado (parecer automatizado) sem contornar controle de acesso deliberado; escopo pequeno, testável offline, reversível. |

## Consequências

- `tests/unit/test_request_profile.py` foi reescrito — o teste anterior
  (`..._without_impersonation`) afirmava o contrato antigo por design; o novo
  teste afirma o contrato atual. `tests/unit/test_browser_fallback.py` teve
  apenas a string literal do UA atualizada; todas as asserções de "sem
  escalada em bloqueio" permanecem inalteradas e verdes.
- `README.md`, `docs/architecture.md` e `docs/implementation-plan.md`
  atualizados para não afirmar mais "sem fingerprint falso de navegador".
- **Risco residual, não eliminado por este ADR**: enviar um User-Agent/Client
  Hints que não correspondem à stack real (Scrapy/Twisted, não Chromium)
  é, por definição, uma representação que diverge do cliente real. Isso é
  uma reversão deliberada e autorizada do princípio de transparência do
  INC-07B — não uma correção técnica neutra. Risco de violação de Termos de
  Uso dos sites-alvo aumenta marginalmente frente ao perfil anterior; não foi
  avaliado por jurídico. Se o volume de coleta crescer de laboratório para
  produção contínua em escala, recomenda-se essa revisão jurídica antes de
  ampliar o volume.
- **Efeito prático esperado é limitado**: `robots.txt` (Carrefour, Fast Shop,
  Bondfaro) continua bloqueando no nível do próprio Scrapy, não do site — só
  desativar `ROBOTSTXT_OBEY` mudaria isso, o que está fora de escopo. Bloqueios
  por WAF com fingerprint TLS/comportamental (causa provável de parte dos
  HTTP 403 reais) não são resolvidos por headers de aplicação — só a camada
  TLS/JA3 explicitamente excluída acima resolveria, e essa exclusão é
  deliberada.
- **Recomendação de maior alavancagem não implementada aqui**: para as fontes
  com API oficial (ex.: `mercado_livre_api` já está registrada como
  placeholder em `scripts/seed_catalog.py`), negociar credenciais é o caminho
  mais durável para ampliar cobertura sem tensão com Termos de Uso — requer
  decisão de negócio/operacional (obter credenciais), não uma mudança de
  código.

## Revisão independente

Este runtime (diferente do runtime Codex que produziu `INC-06`/`INC-07B`)
permite delegar revisão a um agente sem visibilidade do raciocínio de
implementação. Dois agentes (`reviewer`, `security-reviewer`) revisaram o
diff de forma independente, sem acesso a shell (limitação do ambiente, não
do escopo pedido) — leitura estática apenas.

**Achado descartado (falso positivo de ambos os agentes)**: `except
TypeError, ValueError:` sem parênteses em `retry_policy.py` foi lido como
sintaxe Python 2 inválida. Verificação direta (AST parse, `compile()` com
teste de controle negativo, e execução real da suíte — 12/12 testes desse
arquivo passando com nomes visíveis) confirmou que é sintaxe válida no
Python 3.14.7 deste ambiente (`requires-python = ">=3.14"`) e é exatamente a
forma que `ruff format` (visando `target-version = "py314"`) produz a partir
do código original com parênteses; reescrever manualmente só faria o
formatter desfazer de novo. Nenhuma mudança de código a partir deste achado.

**Achados reais, corrigidos nesta mesma entrega**:
- Ausência de teto agregado para `Retry-After` — `CLOSESPIDER_TIMEOUT = 300`
  adicionado (item 3 da Decisão).
- `Sec-CH-UA`/`navigator.userAgentData` do Chromium via Playwright discordando
  do `user_agent` sobrescrito — override removido (item 2 da Decisão).
- `parse_retry_after` aceitava dígitos Unicode não-ASCII e vazava `ValueError`
  — corrigido para `1*DIGIT` ASCII estrito (item 5 da Decisão).
- Lacuna de defesa em profundidade: `parse_product` (Amazon/Carrefour/
  Americanas) e `KabumSpider.parse_search` dependiam inteiramente do
  `HttpErrorMiddleware` padrão do Scrapy para nunca receber 401/403/429;
  ganharam guarda explícita de status, e `tests/unit/test_browser_fallback.py`
  ganhou testes que alimentam essas respostas diretamente nos métodos
  (contornando o middleware, como a revisão pediu) mais uma asserção de que
  `HTTPERROR_ALLOW_ALL`/`HTTPERROR_ALLOWED_CODES` não estão configurados.
- `CHROME_MAJOR_VERSION` estava com uma versão de Chrome de referência
  desatualizada (observação informativa da revisão); atualizado.

Achados confirmados como não-problema, sem mudança de código: as quatro
exclusões da seção anterior seguem íntegras no código (não só na
documentação) — ambos os agentes confirmaram isso independentemente, sem
encontrar nenhum caminho onde 401/403/429/`robots.txt` disparasse o fallback
Playwright ou um retry indevido; nenhuma dependência, egress, segredo ou
arquivo de fronteira de confiança foi tocado.

Evidência completa (achados, confiança, trechos) nas transcrições dos dois
agentes desta sessão; resumo consolidado em
`docs/ai/delivery/evidence/INC-11.md`.

## Rollback

Reverter `src/pricing_intel/collection/browser.py`,
`src/pricing_intel/collection/settings.py`,
`src/pricing_intel/collection/spiders/retail.py` e remover
`src/pricing_intel/collection/retry_policy.py` (e seu registro em
`DOWNLOADER_MIDDLEWARES`) restaura o perfil do INC-07B. Sem migração de dados
nem dependência nova — rollback é reversão pura de código/config.

# Evidência INC-06 — diversidade direta e fallback headless

- Data: `2026-09-20`
- Git root: `.`
- Branch: `feature/inc-06-direct-source-diversity`
- Baseline: `ce12c5c`
- Cápsula: `.codex/sessions/inc-06/TASK_CONTEXT.md`
- Fingerprint da cápsula: `07a6af1eb629621bc3badf21086c9bfef3c5eda84686fbf3ff1817ecdc2f66f5`
- Estado: `LOCAL_VERIFIED_WITH_EXTERNAL_GATE`
- Risco: alto

## Aceite demonstrado

- Amazon, Americanas e Carrefour possuem spiders e extratores dedicados. O
  vendedor efetivo, variante, disponibilidade, condição, base de preço e URL de
  evidência são preservados.
- A política é API oficial opcional; nenhuma API comercial está credenciada nesta
  entrega, então fontes habilitadas seguem automaticamente por HTTP, JSON-LD e
  DOM.
- Amazon, Americanas e Carrefour podem usar Chromium somente após HTTP permitido
  com evidência insuficiente. HTTP 401/403/429, `robots.txt` e falha de transporte
  não são transformados em navegação headless.
- A evidência headless recebe sufixo `_browser_fallback` no extrator. O browser
  restringe subrequests a hosts HTTPS revisados, pré-validados como públicos, e
  bloqueia imagem, mídia e fonte.
- O worker é a única imagem com Chromium. Executa sem root e capabilities, com
  `no-new-privileges`, raiz somente leitura, `/tmp` efêmero, um contexto, uma
  página e concorrência de worker igual a um.

## Coleta real reproduzida

Runs completos anteriormente persistidos no worker local:

| Fonte | Prefixo do run | Resultado |
| --- | --- | --- |
| Amazon Brasil | `68610d86` | 1 oferta |
| Americanas | `bbcf4e52` | 1 oferta |
| Carrefour — Loja iPlace | `627af2ac` | 1 oferta |
| Carrefour — MCS Variedades | `5c8de828` | 1 oferta |

O smoke final no container novo acionou o fallback real da Amazon e extraiu:

```text
seller=Amazon.com.br
price=5698.99 BRL
variant=Apple iPhone 17 / 256 GB / Preto
extractor=amazon_visible_buy_box_browser_fallback
```

A comparação focal persistida antes do rebuild reuniu seis varejistas em seis
canais: MCS Variedades (`R$ 5.669,10`), Magazine Luiza via Americanas
(`R$ 5.799,00`), KaBuM! via Zoom (`R$ 5.799,00`), Loja iPlace via Carrefour
(`R$ 6.029,10`), Amazon.com.br e Want Import via Buscapé. Preço Amazon varia por
resposta/buy box; o extrator registra o valor realmente observado e não usa seed.

## Gates locais

- `uv run ruff check .`: verde.
- `uv run ruff format --check .`: `110` arquivos formatados.
- `uv run ty check .`: verde.
- `uv run pytest`: `85` testes passaram.
- `uv build`: sdist e wheel construídos.
- `npm run check && npm run build`: verde; JS `219,29 kB` (`68,15 kB` gzip)
  e CSS `21,78 kB` (`5,44 kB` gzip).
- `POSTGRES_PASSWORD=local-validation-only docker compose config --quiet`: verde.
- `docker build --check .`: sem warnings.
- `docker compose build api worker frontend`: três imagens construídas.
- Playwright/Chromium abriu no worker endurecido e renderizou o título de smoke.
- Browser real em desktop e `390 x 844`: landing, workspace e fontes renderizaram
  sem overflow final. Screenshots: `/tmp/inc06-final-home.png`,
  `/tmp/inc06-final-sources-waterfall.png` e `/tmp/inc06-final-mobile.png`.

## Revisão, riscos e rollback

A revisão local funcional e de segurança teve duas rodadas. Foram corrigidos:
seletor de preço amplo, seller Amazon duplicado, resposta 200 não textual sem
fallback, hosts auxiliares sem pré-validação DNS e instalação Playwright fora do
lock. A segunda leitura não encontrou vulnerabilidade confirmada nem achado alto
remanescente.

O runtime atual proíbe delegar um novo subagente sem pedido explícito do usuário.
Logo, a revisão não é independente e nenhum recibo `reviewer` ou
`security-reviewer` é alegado. Esse é o gate externo restante antes do merge.

Riscos residuais: markup, buy box e disponibilidade externos variam; pré-validação
DNS não elimina rebinding entre resolução e conexão; Chromium usa o isolamento do
container porque o sandbox interno não funciona no perfil Docker padrão.

Rollback: voltar ao commit anterior e reconstruir API/worker/frontend. Não há
migração de schema. O histórico pode ser preservado; o seed idempotente desabilita
URLs antigas de uma fonte de mesmo nome.

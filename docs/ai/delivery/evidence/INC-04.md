# Evidência INC-04 — mercado real e portal

- Data: `2026-09-20`
- Git root: `.`
- Branch: `feature/increment-1-lab-pipeline`
- Cápsula: `.codex/sessions/inc-04/TASK_CONTEXT.md`
- Estado: `VERIFIED`
- Risco: alto

## Aceite demonstrado

- Backend permanece Python e o frontend React; ambos possuem imagem Docker.
- Seed idempotente contém 7 produtos, 76 variantes e 28 fontes/referências.
- Catálogo de mercado: iPhone 17, 17 Pro, 17 Pro Max, Galaxy S26, S26+ e
  S26 Ultra, com armazenamento e cor.
- Adaptadores reais habilitados: Fast Shop, Samsung Shop, KaBuM! e Zoom. iPlace
  permanece candidata após HTTP 403 ao user-agent declarado; não houve disfarce,
  CAPTCHA ou contorno de controle de acesso.
- A comparação aceita somente BRL, novo, disponível e sem condição comercial;
  deduplica varejista, consolida aliases e prefere evidência direta.
- O radar Brave é opcional, limitado, guarda candidatos e nunca os promove ou
  coleta automaticamente.
- Landing page e workspace oferecem seleção de aparelho/variante, coleta,
  comparação, cadastro de equipamento, fontes e radar.

## Evidência real

Uma rodada em containers one-shot concluiu `16/16` fontes reais com sucesso:

- Fast Shop: `1/1/1` ofertas para iPhone 17/Pro/Pro Max;
- KaBuM!: `1` oferta em cada uma das seis famílias, preservando o vendedor;
- Samsung Shop: `6/6/6` variantes para S26/S26+/S26 Ultra;
- Zoom: `6/5/6` ofertas Apple e `4` ofertas S26 Ultra.

Melhor cobertura por variante após deduplicação: iPhone 17 `2`, iPhone 17 Pro
`3`, iPhone 17 Pro Max `3`, S26 `2`, S26+ `1`, S26 Ultra `3` varejistas. O piso
de 6–8 é meta ainda não atingida e está documentado como próximo incremento.

## Gates locais

- `uv run ruff check .`: verde.
- `uv run ruff format --check .`: 105 arquivos formatados.
- `uv run ty check .`: verde.
- `uv run pytest`: 60 testes passaram.
- `npm run check && npm run build`: verde; JS `218.00 kB` (`67.72 kB` gzip) e
  CSS `21.53 kB` (`5.38 kB` gzip).
- `docker compose config --quiet`: verde.
- `docker compose build`: todas as imagens construídas.
- `docker compose run --rm --no-deps migrate`: migração idempotente e seed
  concluídos.
- Browser real em `1280 px` e `390 x 844`: landing/workspace carregaram seis
  aparelhos e 16 fontes reais habilitadas, sem erro de página e sem overflow
  horizontal (`scrollWidth = innerWidth`).

## Limitações, segurança e rollback

A validação de URL rejeita esquema/host/porta/IP privados e redirects passam pelo
mesmo middleware. Há limites de páginas, bytes, tempo, retry e concorrência, além
de no máximo 24 variantes ou 20 ofertas agregadas por página. O risco residual de
DNS TOCTOU está documentado; URLs executáveis continuam em
allowlist exata e não vêm diretamente do radar.

A política desta execução não permitiu recriar toda a stack com Compose. A stack
preexistente foi observada saudável; as imagens novas, migração, API e worker foram
exercitados separadamente contra o PostgreSQL do projeto.

Rollback: parar os serviços one-shot, retornar ao commit anterior e reconstruir
imagens. A migração de candidatos possui downgrade; o volume PostgreSQL é
preservado e nunca deve ser removido como parte do rollback normal.

## Revisão independente

- Reviewer: `APROVAR_LOCALMENTE`; nenhum defeito real remanescente. O achado
  inicial sobre hooks Scrapy foi retirado após verificar a API moderna do Scrapy
  2.19 e a evidência de 16/16 coletas.
- Security reviewer: `APROVAR_LOCALMENTE`; o risco médio de amplificação por
  ofertas externas foi corrigido com caps e teste. Restam riscos baixos de DNS
  TOCTOU e tags mutáveis herdadas nas imagens-base Python/PostgreSQL.
- Fingerprint revisado:
  `9f0da36d9093c3c0a91fb7c33793ff7ba3c9755074ca5cc72cd61b0a8f6a9450`.

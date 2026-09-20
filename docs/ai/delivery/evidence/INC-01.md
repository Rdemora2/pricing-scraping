# Evidência INC-01 — backend e laboratório

- Data: `2026-09-20`
- Git root: `.`
- Branch: `feature/increment-1-lab-pipeline`
- Baseline: `0fdfb1f`
- Estado: `LOCAL_VERIFIED_WITH_EXTERNAL_GATE`
- Risco: alto no conjunto do incremento

## Aceite e evidência

- Backend permanece Python: FastAPI, Scrapy, Procrastinate, Psycopg e Alembic.
- PostgreSQL persiste catálogo, runs, ofertas, observações, evidências e fila.
- Duas lojas HTTP sintéticas exercitam descoberta, paginação, extração e matching.
- Money, extração, matching, comparação e URLs possuem testes de invariantes.
- `Dockerfile` e `compose.yaml` constroem API, worker, migração, banco e lojas.

## Verificação

- `uv run ruff check .`: verde.
- `uv run ruff format --check .`: 88 arquivos formatados.
- `uv run ty check .`: verde.
- `uv run pytest`: 30 testes passaram.
- `uv build`: sdist e wheel gerados.
- `docker compose config --quiet`: verde.
- `docker compose build`: imagens construídas.

Smoke equivalente, usando PostgreSQL local e os mesmos processos da imagem:

- `/health`: HTTP 200;
- duas fontes habilitadas;
- uma coleta por fonte, ambas `succeeded`;
- três ofertas e três evidências por fonte;
- variante 128 GB preta: duas ofertas incluídas, mediana `3599.00` e duas
  exclusões justificadas (`used` e `out_of_stock`).

## Revisão, limitação e rollback

A revisão independente não encontrou defeito residual de backend. A revisão de
segurança anterior aprovou o laboratório sintético e manteve como pré-condição
para fontes reais a contenção SSRF e limites globais de crawl/resposta.

`docker compose up` é bloqueado pela política desta sessão. Portanto, build e
smoke equivalente estão verdes, mas a topologia simultânea em containers não foi
observada. Rollback: retornar ao commit anterior e reconstruir as imagens; não há
deploy nem migração irreversível.

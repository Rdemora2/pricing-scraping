# Evidência INC-09 — expansão governada de coletores

## Escopo e estado

- Branch: `feature/inc-09-collector-coverage`, empilhada sobre o snapshot local
  do INC-08.
- Estado: `BLOCKED_EXTERNAL`.
- Resultado local: normalização dos 17 aparelhos de mercado; 17 novas fontes
  habilitadas após validação pública e duas mantidas como candidatas.
- Gate: não existe oferta verificável suficiente para declarar ampla cobertura
  de todas as variantes de iPhone 18 Pro/Pro Max e Motorola Edge 70 Pro. A
  revisão independente do stack anterior também permanece pendente.

## Implementação

- Identidade de produto, armazenamento e cores passam a usar o catálogo
  canônico, com match pelo nome mais específico e falha fechada para cor ausente.
- iPlace e Samsung Shop reutilizam a mesma normalização em vez de regexes presas
  a iPhone 17 e Galaxy S26.
- Zoom e Buscapé cobrem páginas exatas de iPhone 16, iPhone Air e Galaxy S25.
- Samsung Shop cobre diretamente Galaxy S25, S25+ e S25 Ultra.
- As páginas Zoom/Buscapé de Galaxy S25+ permanecem `candidate`: o dado público
  observado não informa cor e, portanto, não sustenta match exato de variante.

## Evidência executada

- Validação HTTP com user-agent declarado, `robots.txt` e sem redirects externos:
  sete páginas Zoom e sete páginas Buscapé produziram ofertas canônicas; as três
  páginas Samsung Shop S25 produziram `2/2/4` variantes.
- Smokes completos na imagem nova, com persistência:
  - Zoom / iPhone 16: `6` ofertas e `6` evidências;
  - Buscapé / Galaxy S25 Ultra: `20` ofertas e `20` evidências;
  - Samsung Shop / Galaxy S25+: `2` ofertas e `2` evidências.
- `docker compose run --rm --no-deps test pytest tests/unit`: `119 passed`.
- `API_BASE_URL=http://127.0.0.1:8001 uv run pytest tests/integration -q`:
  `2 passed` contra API temporária construída do snapshot novo.
- `.codex/execution_control.py gates --run --task-id INC-09 ...`: testes, lint e
  typecheck aprovados.
- Imagens `api`, `worker`, `migrate` e `test` construídas; seed idempotente aplicado
  ao volume preservado: `18` produtos, `224` variantes incluindo laboratório e
  `63` fontes declaradas.

## Ambiente local

- `.env` ignorado foi criado com modo `600`; a senha local foi gerada sem
  exposição em logs e rotacionada no PostgreSQL sem apagar o volume.
- `docker compose up -d --build` foi concluído pelo operador sem remover volumes.
  PostgreSQL, lojas de laboratório, API e frontend ficaram `healthy`; o worker
  permaneceu em execução.
- Readback final: `GET /health` retornou `{"status":"ok"}`, frontend retornou
  HTTP `200` e `API_BASE_URL=http://127.0.0.1:8000 uv run pytest
  tests/integration -q` aprovou `2` testes contra a stack definitiva.

## Riscos e rollback

- Markup, seller e disponibilidade são externos e podem mudar; extratores falham
  fechados e observações expiram da visão atual após a janela configurada.
- Rollback de código: remover as novas entradas de seed e restaurar o normalizador
  anterior. O seed desabilita URL antiga pelo nome e não apaga histórico.
- Rollback de credencial: definir uma nova senha local no `.env`, rotacionar o
  papel PostgreSQL pelo socket local e reconstruir a stack; o volume não precisa
  ser removido.

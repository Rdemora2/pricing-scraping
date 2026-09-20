# Plano de implementação

## Estado atual

O laboratório e o primeiro incremento de mercado real estão implementados no
branch `feature/increment-1-lab-pipeline`. A fonte normativa de estados e
evidências é `docs/ai/delivery/`.

### Incremento 1 — laboratório ponta a ponta

Entregue localmente:

- schema e acesso a dados PostgreSQL;
- catálogo/seed idempotente;
- duas fontes HTTP sintéticas;
- Scrapy, fila Procrastinate e máquina de estados;
- matching e comparação explicável;
- API FastAPI;
- frontend React responsivo;
- imagens multi-stage e topologia Docker Compose;
- testes unitários e smoke local do fluxo completo.

O Compose local existente foi observado saudável. A política desta execução
impediu apenas recriar toda a stack; as novas imagens foram compiladas e os jobs
de migração/coleta rodaram em containers one-shot contra o PostgreSQL do projeto.

## Próximos incrementos propostos

### Incremento 2 — resiliência do laboratório

- alteração controlada de preço;
- falha transitória e retry observável;
- mudança de markup com fixtures de regressão;
- interrupção/reinício do worker;
- testes automatizados de integração banco/fila/Compose.

### Incremento 4 — mercado real e portal de inteligência

Entregue:

- catálogo canônico Apple e Samsung com capacidades e cores;
- adaptadores isolados para Fast Shop, Samsung Shop, KaBuM!, Zoom e iPlace;
- allowlist de origem, proteção SSRF/DNS/redirects e limites de crawl;
- distinção visual e operacional entre mercado real e laboratório;
- busca ampla opcional que persiste somente candidatos para revisão;
- comparação por varejista, consolidação de aliases e preferência por evidência
  direta;
- landing page e workspace responsivo com fluxos de aparelhos, fontes e radar.

### Incremento 5 — amplitude mínima e diagnóstico

- atingir 6–8 varejistas distintos nas variantes prioritárias com adaptadores
  revisados para Magalu, Casas Bahia, Ponto e integrações oficiais disponíveis;
- criar visão de cobertura por família, variante e fonte, com SLO de frescor;
- adicionar fixtures capturadas/sanitizadas por adaptador para regressão de markup;
- série temporal e mudança efetiva versus verificação recente;
- cobertura, idade e falhas por fonte;
- workflow rastreável de correção manual de matching;
- exportação de evidência sanitizada.

## Gates permanentes

Cada incremento exige diff focado, testes de comportamento, Ruff, formatação,
`ty`, build, revisão independente e evidência proporcional. Produção, cloud e
ações irreversíveis exigem autorização separada.

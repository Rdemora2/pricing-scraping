# Plano de implementação

## Estado atual

O primeiro incremento vertical está implementado no branch
`feature/increment-1-lab-pipeline`. A fonte normativa de estados e evidências é
`docs/ai/delivery/`.

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

Pendente de ambiente: a política desta execução bloqueou `docker compose up`,
portanto a topologia completa foi compilada/configurada, mas a subida simultânea
dos containers deve ser confirmada no terminal do desenvolvedor.

## Próximos incrementos propostos

### Incremento 2 — resiliência do laboratório

- alteração controlada de preço;
- falha transitória e retry observável;
- mudança de markup com fixtures de regressão;
- interrupção/reinício do worker;
- testes automatizados de integração banco/fila/Compose.

### Incremento 3 — primeira fonte real avaliada

Pré-condições:

- decisão de produto sobre categoria, geografia e frequência;
- análise de termos/robots;
- allowlist de origem, proteção SSRF/DNS rebinding e redirects;
- limites de resposta, crawl, evidência e recursos;
- fonte inicia como `candidate` e exige decisão revisada para `enabled`.

### Incremento 4 — histórico e diagnóstico

- série temporal e mudança efetiva versus verificação recente;
- cobertura, idade e falhas por fonte;
- workflow rastreável de correção manual de matching;
- exportação de evidência sanitizada.

## Gates permanentes

Cada incremento exige diff focado, testes de comportamento, Ruff, formatação,
`ty`, build, revisão independente e evidência proporcional. Fontes reais,
produção, cloud e ações irreversíveis exigem autorização separada.

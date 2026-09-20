# Evidência INC-03 — fechamento local

- Data: `2026-09-20`
- Git root: `.`
- Branch: `feature/increment-1-lab-pipeline`
- Estado: `LOCAL_VERIFIED_WITH_EXTERNAL_GATE`

## Reconciliação

- `README.md` documenta início em um comando, URLs, serviços, configuração, API,
  parada, rollback e reset destrutivo explicitamente sinalizado.
- `docs/product.md` fixa usuário, decisão, população comparável e fora de escopo.
- `docs/architecture.md` registra fluxo, invariantes, redes, confiança e recuperação.
- `docs/implementation-plan.md` separa incremento entregue e próximos passos.
- `docs/ai/context-map.md` aponta entrypoints, checks e proprietários reais.

## Estado de entrega

Não houve deploy ou mutação de produção. A branch permanece local e sem PR/merge
porque o reviewer exige o smoke real do Compose antes da entrega remota. Após essa
prova, repetir a revisão no mesmo head, publicar a branch, observar todos os checks
e somente então fazer merge conforme a política do repositório.

O rollback geral é parar os serviços com `docker compose down`, retornar ao commit
anterior e reconstruir. O volume é preservado por padrão; `--volumes` é destrutivo
e não faz parte do rollback normal.

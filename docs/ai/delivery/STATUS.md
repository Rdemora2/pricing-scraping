# Estado de execução

**Atualizado em:** `2026-09-20`
**Estado global:** `IN_PROGRESS`
**Unidade ativa:** `INC-04`

O roadmap foi adotado para concluir o primeiro incremento vertical do laboratório
local de inteligência de preços. A entrega permanece limitada ao ambiente local;
não inclui deploy, cloud ou coleta de fontes reais.

Código, testes, imagens, build do frontend e fluxo equivalente ponta a ponta estão
verdes. A política local bloqueia `docker compose up`; por isso, o runtime conjunto
dos containers e os headers Nginx observados no wire permanecem como gate externo.

O incremento `INC-04` evolui a demonstração para catálogo real de iPhone 17,
coleta permitida em fonte comercial pública e descoberta ampla por provedor oficial
opcional. O laboratório continua isolado e não entra em métricas de mercado real.

## Estados normativos

`WAITING` → `READY` → `IN_PROGRESS` → `IN_REVIEW` → `VERIFIED`

- `REOPENED`: regressão ou evidência inválida reabre unidade verificada.
- `STALE`: evidência depende de unidade reaberta e precisa ser revalidada.
- `BLOCKED_EXTERNAL`: acesso, decisão ou sistema fora do workspace impede aceite.
- `BLOCKED_TECHNICAL`: pré-requisito local falhou após alternativas seguras.
- `LOCAL_VERIFIED_WITH_EXTERNAL_GATE`: resumo de marco localmente verde com gate
  externo ainda pendente; não equivale a aprovação externa.

Existência de arquivo ou exit code zero não basta para `VERIFIED`. Registre em
`evidence/` critérios, baseline/commit, comandos, revisão independente, riscos e
rollback. Um bloqueio afeta somente unidades que dependem dele.

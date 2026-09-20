# Estado de execução

**Atualizado em:** `2026-09-20`
**Estado global:** `VERIFIED`
**Unidade ativa:** `—`

O roadmap conclui o laboratório e avança o portal local de inteligência de
preços com fontes reais. A entrega permanece limitada ao ambiente local; não
inclui deploy ou cloud.

Código, 60 testes, análise estática, imagens, migração, coleta real e browser
desktop/mobile estão verdes. A stack Compose preexistente foi observada saudável;
as imagens novas foram validadas por build e containers one-shot porque a política
local não permitiu recriar todo o conjunto.

O `INC-04` inclui 76 variantes Apple/Samsung, Fast Shop, Samsung Shop, KaBuM! e
Zoom, descoberta ampla governada e portal completo. A melhor variante observada
teve três varejistas distintos; o piso desejado de 6–8 permanece próximo
incremento explícito. O laboratório continua isolado das métricas reais.

Reviewer e security reviewer aprovaram localmente o fingerprint
`9f0da36d9093c3c0a91fb7c33793ff7ba3c9755074ca5cc72cd61b0a8f6a9450` sem
achado bloqueante. Permanecem somente os riscos baixos documentados de DNS TOCTOU
e tags mutáveis herdadas nas imagens-base Python/PostgreSQL.

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

# Estado de execução

**Atualizado em:** `YYYY-MM-DD`
**Estado global:** `NOT_ADOPTED`
**Unidade ativa:** `nenhuma`

`NOT_ADOPTED` significa que o repositório recebeu o contrato, mas ainda não criou
unidades reais. Não execute roadmap até substituir esse estado e preencher a fila.

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

# Checklist de revisão antes de PR/merge

## Escopo e intenção

| Pergunta | Evidência | OK? |
| --- | --- | --- |
| O requisito e os critérios de aceitação estão claros? | Ticket/spec |  |
| A mudança contém somente o escopo aprovado? | diff ou `delivery/BASELINE.md` |  |
| Todos os untracked foram incluídos quando não há HEAD? | `git status --short --untracked-files=all` |  |
| Mudanças pré-existentes foram preservadas e separadas? | `git status`, diff |  |
| A decisão arquitetural e os invariantes estão documentados? | Plano/ADR |  |

## Corretude e testes

| Pergunta | Evidência | OK? |
| --- | --- | --- |
| O teste novo/alterado captura o comportamento desejado? | Teste e assert |  |
| O teste falhava pela razão correta antes da correção, quando possível? | Execução registrada |  |
| Casos de erro, limites, autorização e repetição foram considerados? | Matriz de testes |  |
| Lint, typecheck, build e suíte relevante passaram? | Comandos/saídas |  |
| Falhas ou checks não executados estão explícitos? | Resumo da tarefa |  |

## Segurança, dados e operação

| Pergunta | Evidência | OK? |
| --- | --- | --- |
| Entradas são validadas e tratadas na trust boundary correta? | Código/testes |  |
| Auth e autorização estão corretas para cada caminho? | Testes/contratos |  |
| Não há segredos, PII ou logs indevidos no diff? | Scanner/diff |  |
| Migração, compatibilidade, observabilidade e rollback foram considerados? | Plano/ADR |  |
| Dependências novas foram justificadas e fixadas? | Lockfile/decisão |  |

## Decisão

A decisão é `APROVAR_LOCALMENTE`, `CORRIGIR` ou `BLOQUEAR`. Sem evidência, peça correção ou teste. A revisão é independente e read-only; aprovação permite ao `delivery-manager` prosseguir, e achado alto/bloqueante impede entrega. Depois do merge, confirme default branch sincronizada por fast-forward e worktree limpo.

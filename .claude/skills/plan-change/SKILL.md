---
name: plan-change
description: Planeje features, bugs não triviais, refactors, contratos, migrações e mudanças médias, altas ou transversais antes da implementação. Não aplique o patch durante esta skill.
---

# Plan change

## Gatilho

Use para features, bugs não triviais, refactors, mudanças cross-cutting, alteração de contrato, migração, integração externa ou qualquer tarefa média/alta.

## Procedimento

Leia a especificação, `AGENTS.md`, `docs/ai/delivery/STATUS.md` e `QUEUE.md` quando adotados, além de apenas os caminhos relevantes. Separe fatos observados, hipóteses, gates externos e decisões pendentes. Mapeie entrypoints, dependências, consumidores, invariantes, dados, Git roots e testes. Se a especificação estiver materialmente ambígua, transforme a ambiguidade em decisão explícita.

Escreva um plano com escopo incluído/excluído, arquivos candidatos, passos pequenos, estratégia de testes, riscos, telemetria, migração e rollback. Prefira um plano que possa ser implementado e revisado em um PR pequeno. Não aplique o plano nesta skill.

## Saída

Use este formato: `Goal`, `Acceptance criteria`, `Facts`, `Proposed change`, `Files`, `Invariants`, `Tests`, `Security/performance/data risks`, `Rollout/rollback`, `Open questions`, `Decision required`.

## Critério de parada

O plano termina quando a abordagem está executável ou há uma decisão material pendente. A tarefa de implementação autoriza entrega normal, mas nunca deploy, produção, segredo, dependência nova ou operação irreversível.

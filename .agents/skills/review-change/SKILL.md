---
name: review-change
description: Revise um diff estável em modo somente leitura antes de commit, PR ou merge, priorizando corretude, regressões, segurança, dados e testes. Não implemente correções durante a revisão.
---

# Review change

Use `docs/ai/review-protocol.md` para contexto por papel, checkpoint e recibo
JSON validado. Leia integralmente o contrato afetado, não todo o planejamento.
Provas que exigem execução pertencem ao verifier; não crie probes na worktree.

## Gatilho

Use antes de commit/PR e depois de qualquer mudança que altera comportamento, contrato, segurança, dados ou operação.

## Procedimento

Trabalhe em modo read-only. Leia requisito, `AGENTS.md`, mudança completa, testes, contratos afetados e histórico mínimo. Sem HEAD, aplique `docs/ai/delivery/BASELINE.md`, inclua os untracked do escopo e não aprove por `git diff` vazio. Analise corretude, regressões, segurança, autorização, dados, concorrência, idempotência, migração, performance, observabilidade, dependências, compatibilidade e qualidade dos testes.

Use fatos e dados em vez de preferência. Um achado precisa ter cenário, impacto e evidência. Comentários de estilo só são bloqueantes se violarem convenção documentada ou ocultarem risco. Não reescreva o patch nem aprove por ausência de achados.

## Saída

Ordene achados por severidade e forneça caminho/linha/símbolo, cenário, impacto, evidência e correção mínima. Depois liste checks não executados, riscos não comprovados, confiança e decisão `APROVAR_LOCALMENTE`, `CORRIGIR` ou `BLOQUEAR`. A aprovação alimenta o gate do `delivery-manager`; achado alto/bloqueante exige correção e nova revisão.

## Critério de parada

Pare se não houver diff estável, se o requisito não estiver disponível ou se a revisão exigir acesso a produção/segredos. Declare a limitação.

---
name: implement-small-change
description: Implemente e entregue uma mudança pequena, isolada e bem definida, com patch mínimo, testes proporcionais e commits atômicos. Não use para segurança, infraestrutura, migração irreversível ou trabalho transversal sem plano.
---

# Implement small change

## Gatilho

Use somente quando o objetivo, os critérios de aceitação, os arquivos relevantes e os comandos de verificação estiverem claros e quando a mudança puder ser isolada em uma branch/worktree.

Não use para auth, pagamentos, dados pessoais, migração irreversível, infraestrutura, produção, alteração de privilégio ou mudança cross-cutting sem plano.

## Procedimento

Confirme o Git root, `git status --short` e as instruções locais. Sem HEAD, aplique `docs/ai/delivery/BASELINE.md` e inclua todos os untracked do escopo. Examine implementação e testes existentes antes de editar. Faça um patch mínimo, preservando contratos e comportamento não relacionado. Se a mudança altera comportamento, escreva teste que expresse o requisito; quando possível, execute-o antes para confirmar que falha pela razão correta.

Depois, entregue a mudança ao `verifier`, aos revisores exigidos pelo risco e ao `delivery-manager`. Revise `git diff --check` e a mudança completa. Não adicione dependência, altere lockfile, habilite rede de shell ou leia segredo sem autorização ou perfil controlado. O worker não publica nem integra o próprio patch.

## Saída

Retorne comportamento, arquivos, evidência de testes, falhas, riscos, pendências e rollback. Se a implementação precisar ultrapassar o escopo, pare e peça atualização do plano.

## Critério de parada

Pare diante de requisito conflitante, falta de comando, mudança pré-existente, falha inexplicada, segredo, alteração de contrato não autorizada ou risco superior ao nível permitido.

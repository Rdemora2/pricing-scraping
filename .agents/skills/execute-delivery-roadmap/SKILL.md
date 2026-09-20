---
name: execute-delivery-roadmap
description: Inicie ou continue um roadmap governado por fila, dependências, estados e evidências, avançando unidades autorizadas sem confirmações intermediárias. Não use para planejamento read-only nem quando o repositório não adotou docs/ai/delivery/QUEUE.md.
---

# Execute delivery roadmap

## Pré-condições

Leia `AGENTS.md`, `docs/ai/delivery/STATUS.md`, `QUEUE.md`, o contrato da unidade e
`docs/ai/execution-contract.md`. Confirme o Git root proprietário, o marco e as
mudanças preexistentes. Não execute se o estado for `NOT_ADOPTED` ou a fila estiver
vazia. Se não houver HEAD, aplique `BASELINE.md`.

## Loop determinístico

1. Selecione a primeira unidade `READY` coberta pelo pedido e com dependências
   `VERIFIED`; mantenha no máximo uma unidade `IN_PROGRESS` por Git root.
2. Prepare ou reutilize a cápsula; a rota determina risco, papéis, modelo e gates.
3. Execute o loop mínimo do contrato sem reler fatos estáveis entre papéis.
4. Registre comandos, critérios, commits/PR, riscos e rollback em
   `docs/ai/delivery/evidence/` e atualize `STATUS.md`/`QUEUE.md` na mesma intenção.
5. Registre a métrica sanitizada e marque `VERIFIED` somente após entrega exigida pelo
   contrato. Então torne `READY` a próxima unidade elegível e continue dentro do
   marco autorizado.

Use `REOPENED` quando uma regressão invalidar evidência; dependentes verificados
viram `STALE`. Use `BLOCKED_EXTERNAL` ou `BLOCKED_TECHNICAL` sem converter bloqueio
em sucesso e continue apenas unidades independentes. Produção, deploy, segredo,
custo e ação irreversível continuam exigindo autorização específica.

## Saída

Informe unidade, estado anterior/final, resultado, evidências, branch/PR/merge,
riscos, bloqueios, próxima unidade elegível e rollback. Não despeje logs.

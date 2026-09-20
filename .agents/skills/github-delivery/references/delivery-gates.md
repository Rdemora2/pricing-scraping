# Gates de entrega remota

## Estado mínimo antes de publicar

- repositório e branch base confirmados;
- nenhuma alteração alheia incluída;
- nenhuma credencial, PII, `.env` ou artefato temporário;
- commit convencional, coeso e independentemente reversível;
- checks locais proporcionais ao risco executados ou limitação declarada.

## Estado mínimo antes do merge

- PR aberto, não draft e apontando para a base autorizada;
- head SHA relido imediatamente antes da decisão;
- todos os required checks concluídos com sucesso;
- todo check extra observado no mesmo head também concluído com sucesso; falha,
  cancelamento, pendência ou estado desconhecido bloqueia;
- nenhuma falha, conflito ou revisão com changes requested;
- threads bloqueantes tratadas, sem autoaprovação;
- branch protection e merge queue respeitadas sem bypass;
- risco, testes, observabilidade e rollback documentados;
- nenhuma etapa de deploy ou produção embutida sem autorização específica.

Use `merge_pull_request` com `expected_head_sha` igual ao SHA recém-verificado. Leia
listas paginadas quando a plataforma as fornecer e rejeite resposta incompleta ou
contraditória. Se o head mudar, aborte, releia mudança, reviews e checks; nunca
repita cegamente.

## CI e tentativas

Classifique a falha antes de agir:

- transitória de infraestrutura: reexecute o menor job possível;
- determinística de código, teste, lint ou build: corrija em novo commit atômico;
- permissão, secret, environment ou produção: pare e registre o bloqueio;
- duas reexecuções sem sucesso: pare; não crie loop automático.

## Operações fora da autoridade

- `update_ref` com `force=true`;
- alteração ou exclusão remota direta fora do tree revisado;
- fechar ou retargetar PR para mascarar falha;
- dispensar review ou remover reviewer/label para liberar merge;
- alterar branch protection, Actions secrets, environments ou runners;
- executar workflow de produção, deploy ou migração irreversível;
- rebase, reset, clean, amend publicado ou qualquer reescrita de histórico.

# Evidências de entrega

Crie `UNIDADE.md` somente para trabalho real. Registre de forma sanitizada:

- unidade, data, Git root, risco e estado;
- baseline, branch, commits e PR quando aplicáveis;
- critérios de aceite e evidência correspondente;
- comandos executados e resultado compacto;
- decisões do verifier/reviewers;
- dependências, bloqueios e riscos residuais;
- observabilidade e rollback;
- próximo estado e unidade elegível.

A cápsula local em `.codex/sessions/` evita redescoberta durante a execução, mas
não substitui a evidência final. Métricas operacionais ficam em `.codex/metrics/` e
não devem ser copiadas para este diretório.

Não cole logs extensos, prompts, tokens, segredos, PII ou conteúdo de produção.
Uma evidência invalidada marca a unidade `REOPENED` e seus dependentes `STALE`.

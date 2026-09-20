# Melhoria contínua do kit

Projetos canários podem revelar melhorias genéricas. Ao encontrar uma, registre a
evidência, remova nomes/contratos de domínio, preserve compatibilidade
multiplataforma e atualize regra, automação, teste e documentação como uma única
capacidade revisável.

Não copie requisitos específicos do produto. Integrações, dados regulados,
modelos financeiros e decisões comerciais permanecem no repositório de origem.

Capacidades promovidas atualmente:

- Git bruto para o fluxo normal, com operações destrutivas ainda bloqueadas;
- commits convencionais e atômicos com hooks versionados;
- `pre-push` contra default branch, exclusão e non-fast-forward;
- `.codex/safe_git_sync.py sync-main` para fechamento local pós-merge;
- cadeias POSIX lineares, decompostas e avaliadas comando a comando pelo Codex;
- roteamento de agentes e gates proporcionais ao risco.

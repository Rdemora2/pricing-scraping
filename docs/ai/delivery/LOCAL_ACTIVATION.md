# Ativação local da governança

Após clonar, mover ou renomear o repositório:

1. execute novamente o bootstrap universal contra a raiz exata;
2. confirme `.codex/config.toml`, agentes, skills, regras, hooks e documentos;
3. confirme `core.hooksPath=.githooks` quando não houver política preexistente;
4. execute os testes de governança e o self-test dos launchers usados;
5. valide origin/default branch e preserve customizações não gerenciadas;
6. não copie caches, binários, credenciais ou configuração do host anterior.

Em produtos multi-root, repita por root e registre ownership em `MULTI_ROOT.md`.

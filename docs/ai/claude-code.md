# Adapter Claude Code

`AGENTS.md`, `.agents/skills/`, scripts e gates são canônicos. O bootstrap gera:

- `CLAUDE.md` com `@AGENTS.md`, preservando texto customizado existente;
- `.claude/settings.json` com `opus/high`, desenvolvimento autônomo e bypass desabilitado;
- `.claude/agents/*.md` a partir de `.codex/agents/*.toml`;
- `.claude/skills/` como espelho das skills canônicas;
- `.claude/hooks/policy.py` para aceitar wrappers seguros e bloquear apenas riscos objetivos.

Papéis críticos usam `opus/high`; execução previsível usa `sonnet/medium` ou
`sonnet/low`. O manifesto `.claude/.valiant-managed.json` impede que atualizações
sobrescrevam customizações locais. O plano de controle usa perfil read-only; o
repositório usa `acceptEdits`.

Não use `--dangerously-skip-permissions`: o adapter o desabilita. O hook bloqueia
segredos, destruição, produção, bypass Git e Codex Security, e pede aprovação
somente para dependências/ferramentas novas.

Baseline: Claude Code `>= 2.1.219`; validado localmente com `2.1.222`.

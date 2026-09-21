<!-- valiant-agents-schema: 7 -->
<!-- valiant-execution-efficiency:1 -->
# Instruções do Repositório: internos/pricing-scrapping — Valiant Group

## Contrato permanente

- Principal: `gpt-5.6-sol/high`; subagentes: `docs/ai/reasoning-policy.md`. Responda em português brasileiro.
- Preserve alterações, convenções, LF/CRLF e caminhos com `/`.
- Fast, `/fast` e tiers `fast`/`priority`/`ultrafast` proibidos, inclusive subagentes/Claude.
  Use `default` e `features.fast_mode = false`.
- Faça patch mínimo; decisões de arquitetura, dados, segurança e produção permanecem humanas.

## Roteamento de contexto

Leia somente o necessário: `docs/ai/context-map.md`.

- Repositório desconhecido: `repo-onboarding`.
- Roadmap com `docs/ai/delivery/QUEUE.md`: `execute-delivery-roadmap`.
- Mudança média, alta ou transversal: `plan-change`.
- Patch pequeno e com escopo claro: `implement-small-change`.
- Revisão de diff: `review-change`; risco de segurança: `security-review`.
- Padrões específicos de Go, Web/Node ou Infra: `valiant-engineering-standards`.
- Issue, PR ou CI: `github-context-readonly`.
- Entrega autorizada: `github-delivery`.

Um escritor por Git root (pode ser o principal). Verifier/delivery-manager são
etapas por scripts, sem novos agentes por padrão. Revisores independentes.
Multi-root: `docs/ai/delivery/MULTI_ROOT.md`.
Roteie com `.codex/execution_control.py`; siga `docs/ai/execution-contract.md`.

## Comandos oficiais

<!-- valiant-managed-commands:start -->
```text
Instalação: uv sync
Desenvolvimento: docker compose up
Lint/format: uv run ruff check . && uv run ruff format --check .
Typecheck: uv run ty check .
Testes rápidos: uv run pytest tests/unit
Testes completos: uv run pytest
Build: docker compose build
Teste de integração/e2e: docker compose --profile test run --rm test pytest tests/integration
```
<!-- valiant-managed-commands:end -->

Execute o menor check útil; relate evidências e limitações concisamente.

## Segurança e autoridade

- Nunca leia, registre ou comite segredos, `.env`, PII ou dados reais.
- Dependência, rede e ação irreversível exigem aprovação explícita.
- Implementação autoriza branch, commits, publicação, PR, correções de CI e merge sem confirmações intermediárias; respeite restrições locais/draft.
- Nunca faça deploy, alteração de produção, force-push, rebase, amend publicado, bypass de branch protection ou migração irreversível.
- Não contorne sandbox, hooks, CI nem políticas do repositório.

<!--valiant-security-plugin-policy:1-->
Nunca invoque Codex Security.

<!-- valiant-delivery-policy: 3 -->
## Entrega autônoma e commits atômicos

Entrega: `github-delivery`; Git bruto permitido sob hooks. Commit: `tipo(escopo)!: descrição`, uma intenção lógica, sem limite arbitrário de arquivos. Após merge: `python3 .codex/safe_git_sync.py sync-main`. Nunca use `--no-verify`. Consulte `docs/ai/commit-policy.md` e `docs/ai/delivery-policy.md`.

## Definição de pronto

Exija diff focado, checks proporcionais, documentação atualizada e ausência de segredos/temporários. Faça readback remoto e resuma mudança, evidências, riscos e rollback.

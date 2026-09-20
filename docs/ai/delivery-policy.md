# Política de entrega autônoma

## Autorização persistente

Ao solicitar uma implementação, o usuário autoriza o agente daquele repositório a concluir branch, commits, publicação, Pull Request, acompanhamento/correção de CI e merge sem pedir confirmação a cada etapa. Uma instrução explícita de manter local, não publicar ou deixar draft prevalece.

O Tech Lead da raiz do portfólio permanece read-only: ele prepara pacotes isolados, mas nunca escreve nos filhos nem executa a entrega.

## Gates proporcionais ao risco

Verifier e delivery-manager indicam etapas operacionais do orquestrador por
scripts, não agentes adicionais por padrão. Delegação exige ambiguidade concreta;
as revisões independentes permanecem, conforme `execution-contract.md`.

| Risco | Evidência mínima antes do PR/merge |
| --- | --- |
| Baixo | mudança revisada, check direcionado e verifier quando houver comportamento |
| Médio | lint/typecheck/testes afetados, verifier e revisão independente |
| Alto | plano, verifier, revisão funcional e de segurança, suíte ampliada, rollback e CI completo |
| Crítico | não delegado: produção, segredo, privilégio ou migração irreversível exigem operação humana específica |

CI obrigatório e branch protection nunca são dispensados. Todos os checks observados no head precisam estar verdes, não apenas os required checks. Falha transitória pode ser reexecutada no máximo duas vezes; falha determinística exige correção em novo commit atômico.

## Limites técnicos

- Git bruto é permitido para branch, commit, fetch e push no fluxo normal;
- o conector GitHub permanece preferencial para PR, review, checks, Actions e merge;
- `default_tools_enabled=false`: somente ferramentas nominadas estão disponíveis;
- `update_ref` sempre fast-forward, com `force` omitido ou `false`;
- merge usa o head SHA recém-verificado e respeita reviews/checks;
- sem autoaprovação, force-push, rebase, amend publicado ou bypass;
- sem secrets, environments, runners, release, deploy ou produção.

O hook `pre-push` aceita somente `origin`, bloqueia push direto em `main`/`master`, exclusão remota e non-fast-forward. Após o merge, `python3 .codex/safe_git_sync.py sync-main` exige Git root exato, worktree limpo e uma única URL de `origin`, então retorna à default branch e aplica apenas fast-forward.

Comandos independentes e simples podem ser agrupados por `&&`, `||`, `;` ou `|`. Evite wrappers opacos (`sh -c`, `bash -lc`, substituições, redirecionamentos, globs ou controle de fluxo) quando a mesma operação puder ser expressa como cadeia linear verificável.

O procedimento executável está na skill `github-delivery`.

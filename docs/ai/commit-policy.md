# Política obrigatória de commits

## Contrato

Todo commit deve ser convencional, atômico, coeso e independentemente reversível.

Formato obrigatório:

```text
tipo(escopo)!: descrição
```

Tipos aceitos: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore` e `revert`.

## Atomicidade

- Um commit representa exatamente uma intenção lógica.
- Não misture feature, correção, refactor, formatação ou manutenção não relacionada.
- Testes e documentação diretamente necessários fazem parte da mesma intenção.
- Mudanças maiores devem ser divididas por contrato, camada, migração ou comportamento observável.
- Quantidade de arquivos é um sinal, não um limite; um commit com muitos arquivos só é válido quando todos são indispensáveis à mesma intenção e reversíveis em conjunto.
- Não use `--no-verify`; contornar os hooks viola a política.

## Aplicação

Os hooks versionados em `.githooks/` validam a mensagem e impedem caminhos sensíveis. O bootstrap configura `core.hooksPath=.githooks` sem substituir hooks preexistentes. O CI revalida cada commit; atomicidade semântica é confirmada na revisão do diff.

Uma tarefa de implementação autorizada inclui branch, commits, publicação, PR, tratamento de CI e merge sem nova confirmação. Rebase, force-push, amend publicado, bypass de branch protection, produção e reescrita de histórico continuam proibidos.

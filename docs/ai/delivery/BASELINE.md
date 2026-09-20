# Protocolo de baseline Git

Use este protocolo quando o Git root ainda não possuir `HEAD` ou quando a tarefa
começar sobre uma árvore preexistente sem baseline confiável.

## Regra

- `git diff` vazio não prova ausência de mudança antes do primeiro commit.
- Liste todos os itens com `git status --short --untracked-files=all` sem abrir
  segredos, `.env`, credenciais ou dados privados.
- Atribua cada path ao escopo da tarefa, a trabalho preexistente ou a artefato
  indevido. Não absorva trabalho alheio por conveniência.
- Reviewer e verifier consideram todos os arquivos atribuídos ao escopo, inclusive
  untracked, e registram a baseline na evidência.
- O primeiro commit continua atômico por intenção; uma baseline grande deve ser
  dividida por contratos reversíveis, não por contagem arbitrária.

Em produtos com múltiplos Git roots, repita a inspeção em cada root e mantenha um
único worker por root.

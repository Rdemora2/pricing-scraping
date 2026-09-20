---
name: repo-onboarding
description: Mapeie de forma somente leitura um repositório, serviço ou módulo desconhecido, seus entrypoints, comandos, contratos e riscos. Evite quando uma alteração pequena já tem contexto suficiente.
---

# Repo onboarding

## Gatilho

Use quando o repositório, serviço ou módulo for desconhecido, quando a documentação estiver incompleta ou quando a tarefa atravessar mais de uma área.

Não use para uma alteração pequena em um módulo já conhecido; nesse caso, leia o contexto local e prossiga pelo prompt de implementação.

## Objetivo

Produzir um mapa curto do sistema sem editar arquivos, sem varrer tudo por hábito e sem carregar conteúdo irrelevante para a sessão principal.

## Procedimento

1. Descubra todos os Git roots envolvidos, identifique o proprietário da tarefa e leia `AGENTS.md`, README e instruções locais.
2. Verifique `git status --short` sem alterar a árvore.
3. Identifique entrypoints, scripts, configuração, módulos chamados e testes próximos.
4. Siga referências de símbolos e imports somente até o limite necessário para a tarefa.
5. Consulte histórico recente da área se ele esclarecer uma decisão; não despeje histórico completo.
6. Registre comandos oficiais, dependências relevantes, contratos, ownership e riscos. Se houver `docs/ai/delivery/`, identifique unidade, estado e evidência sem carregar toda a fila.

## Saída

Retorne `Facts`, `Relevant paths`, `Execution commands`, `Invariants`, `Risks`, `Unknowns` e `Suggested next step`. Cada afirmação deve citar caminho, símbolo ou comando. Mantenha a resposta compacta e não inclua logs completos.

## Critério de parada

Pare quando houver contexto suficiente para um humano aprovar ou rejeitar o plano. Se faltar requisito, permissão ou comando verificável, declare o bloqueio em vez de adivinhar.

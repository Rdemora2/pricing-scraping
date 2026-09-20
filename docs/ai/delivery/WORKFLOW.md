# Fluxo autônomo de desenvolvimento

Uma solicitação para implementar, corrigir, construir ou continuar autoriza as
unidades cobertas da fila e o fluxo normal de branch, commits, PR, CI, merge e
sincronização, sem confirmações intermediárias. Análise, revisão e planejamento
permanecem read-only.

## Loop por unidade

Verifier/delivery-manager são etapas do orquestrador por scripts; só delegar por
ambiguidade concreta. Reviewer/security-reviewer permanecem independentes do autor.

1. Tech Lead/orquestrador escolhe a primeira unidade elegível e prepara a cápsula
   conforme `docs/ai/execution-contract.md`; a rota classifica risco e gates.
2. Explorer e test-designer entram somente quando a rota ou matriz de testes
   justificarem seu custo.
3. Um único `worker` escreve fontes por Git root.
4. `verifier` executa o teste falsificador e os gates proporcionais.
5. `reviewer` e, quando exigido, `security-reviewer` decidem de forma independente.
6. Achados altos/bloqueantes retornam ao worker e repetem verificação/revisão.
7. `delivery-manager` cria commits atômicos, publica, acompanha CI, integra e
   sincroniza a default branch.
8. Evidência, fila e status são atualizados; registre a métrica sanitizada e avance.

## Paradas legítimas

Pare somente por decisão material de produto, produção/deploy, segredo/PII, custo,
ação irreversível, conflito sem solução segura ou bloqueio externo/técnico real.
Uma falha em uma unidade não interrompe trabalho local independente já autorizado.

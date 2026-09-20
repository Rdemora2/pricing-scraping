# Contrato para produtos com múltiplos Git roots

Use somente quando um produto possuir dois ou mais repositórios locais coordenados.

| Root | Responsabilidade | Default branch | Comandos/gates | Owner |
| --- | --- | --- | --- | --- |

Tabela vazia significa produto de root único ou contrato ainda não adotado.

Regras:

- cada root mantém histórico, origin, hooks, CI e entrega independentes;
- somente um worker escreve em cada root por vez;
- o Tech Lead de produto pode escrever apenas no control plane que lhe pertence;
- artefatos não atravessam roots sem contrato e impacto rastreados;
- uma unidade cross-root possui subtarefas e evidência por root, com ordem explícita;
- o Tech Lead de portfólio externo permanece read-only.

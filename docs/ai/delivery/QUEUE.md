# Fila determinística de entrega

Preencha uma linha por unidade executável. Backlog detalhado pode permanecer na
ferramenta ou documentação do produto; esta fila é o índice operacional local.

| Ordem | Unidade | Resultado/aceite | Git root | Depende de | Estado |
| ---: | --- | --- | --- | --- | --- |

Fila vazia significa governança ainda não adotada; não invente unidades.

## Regras

- Somente uma unidade pode estar `IN_PROGRESS` por Git root.
- Torne `READY` a primeira unidade coberta pelo pedido cujas dependências estejam
  `VERIFIED`; em empate, use a ordem da tabela.
- `REOPENED` torna dependentes verificados `STALE` até revalidação topológica.
- Bloqueio externo ou técnico nunca vira sucesso e só pode ser pulado quando a
  próxima unidade não depender dele.
- Atualize fila, estado e evidência junto da mudança que provoca a transição.
- Frases amplas como “continue o roadmap” avançam apenas o marco já autorizado;
  nunca inferem produção, deploy ou ampliação material do produto.

# Fila determinística de entrega

Preencha uma linha por unidade executável. Backlog detalhado pode permanecer na
ferramenta ou documentação do produto; esta fila é o índice operacional local.

| Ordem | Unidade | Resultado/aceite | Git root | Depende de | Estado |
| ---: | --- | --- | --- | --- | --- |
| 1 | `INC-01` | Backend Python estabilizado, documentado e coberto por testes úteis; stack de API, worker, PostgreSQL e fontes sintéticas executa via Docker Compose | `.` | — | `LOCAL_VERIFIED_WITH_EXTERNAL_GATE` |
| 2 | `INC-02` | Frontend React responsivo e acessível permite disparar coleta, acompanhar execução e consultar comparações reais da API | `.` | `INC-01` | `LOCAL_VERIFIED_WITH_EXTERNAL_GATE` |
| 3 | `INC-03` | Fluxo completo local validado, documentação reconciliada e evidência/rollback registrados | `.` | `INC-02` | `LOCAL_VERIFIED_WITH_EXTERNAL_GATE` |
| 4 | `INC-04` | Catálogo Apple/Samsung, fontes reais governadas, descoberta ampla, proteção de rede e portal responsivo separando mercado real do laboratório | `.` | — | `VERIFIED` |
| 5 | `INC-05` | Cobertura real ampliada para piso de 6–8 varejistas distintos nas variantes prioritárias Apple/Samsung, com rastreabilidade, UX e evidência reproduzível | `.` | `INC-04` | `LOCAL_VERIFIED_WITH_EXTERNAL_GATE` |

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

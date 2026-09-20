# Go

Defaults para código novo quando o repositório não documentar outra escolha:

- Go 1.22+ e Fiber v2 para APIs; preserve `net/http` quando ele já for contrato do projeto.
- PostgreSQL com `pgx/v5`; use `sqlc` para queries complexas e GORM apenas quando já adotado.
- Redis com `go-redis/v9`; Asynq para filas Redis-backed.
- Logs estruturados com `zerolog`; não introduza `fmt.Println` em produção.
- Estrutura preferida: `cmd/server`, `internal/handler`, `internal/service`, `internal/repository`, `internal/domain` e `internal/middleware`.
- Trate todos os erros; use `errors.Is`/`errors.As` e evite `panic` em handlers.
- Serviços long-running devem encerrar graciosamente após sinal do sistema.

Não adicione biblioteca, altere versão ou reorganize pacotes sem escopo e aprovação correspondentes.

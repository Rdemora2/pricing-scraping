# Mapa de contexto do projeto

Este arquivo é um índice, não uma cópia do código. O objetivo é apontar onde o Codex deve olhar primeiro para uma classe de tarefa.

| Necessidade | Fonte primária | Teste/check | Proprietário |
| --- | --- | --- | --- |
| Inicialização da aplicação | `compose.yaml`, `Dockerfile`, `frontend/Dockerfile` | `docker compose config --quiet && docker compose build` | Plataforma |
| Rotas/endpoints | `src/pricing_intel/api/main.py`, `api/routers/` | `uv run pytest tests/unit` | Backend |
| Autenticação/autorização | modo local sem auth; bind loopback em `compose.yaml` | inspeção do Compose e browser same-origin | Plataforma |
| Modelo e migrações de dados | `domain/models.py`, `migrations/versions/` | Alembic + testes de domínio | Backend |
| Jobs e integrações externas | `jobs/`, `collection/`, `lab/sources/` | smoke API/worker/labs | Coleta |
| Tratamento de erros | `collection/extraction.py`, `jobs/tasks.py`, routers | testes de entradas inválidas e estados | Backend |
| Observabilidade | `logging.py`, `CollectionRun`, `/runs/{id}` | logs estruturados + smoke | Backend |
| Testes unitários | `tests/unit/` | `uv run pytest tests/unit` | Backend |
| Testes integração/e2e | `tests/integration/`, `docs/ai/delivery/evidence/` | serviço Compose `test` + browser | Plataforma |
| Deploy e rollback | somente local: `README.md`, `compose.yaml` | build/smoke; sem deploy | Plataforma |

## Convenções estáveis

Registre somente convenções que são verdadeiras para todo o projeto. Para regras de um serviço ou domínio, crie um `AGENTS.md` mais próximo do código ou uma skill específica.

## Termos de domínio

| Termo | Significado no produto | Fonte |
| --- | --- | --- |
| `fonte` | domínio conhecido que pode ser candidato, habilitado ou desabilitado | `domain/enums.py` |
| `oferta` | anúncio de um vendedor em uma fonte | `domain/models.py` |
| `observação` | estado temporal de preço e condições de uma oferta | `domain/models.py` |
| `evidência` | excerpt/hash/versionamento que sustenta uma extração | migration inicial |

## Decisões importantes

Use `docs/ai/decisions/` para ADRs. Não copie longos históricos para este mapa. Uma decisão deve indicar problema, decisão, alternativas, consequências e data.

## Como manter

Atualize este índice quando um entrypoint, contrato, comando, integração ou procedimento de rollback mudar. Uma mudança de código não precisa atualizar este documento se o mapa continuar correto.

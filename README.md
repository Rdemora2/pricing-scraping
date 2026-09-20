# Signal Price

Laboratório local de inteligência de preços. A aplicação descobre ofertas em
fontes HTTP sintéticas, extrai dados estruturados, associa anúncios a variantes
canônicas e apresenta comparações explicáveis.

O projeto prioriza profundidade de backend: coleta assíncrona, idempotência,
histórico, evidências, matching determinístico e regras explícitas de
comparabilidade. Nenhum serviço pago, cloud ou site de terceiro é necessário.

## Demonstração rápida

Requisitos: Docker com Compose v2 e aproximadamente 2 GB livres de memória.

```bash
docker compose up --build
```

Acesse:

- frontend: <http://localhost:3000>;
- API e OpenAPI: <http://localhost:8000/docs>;
- healthcheck: <http://localhost:8000/health>.

Na interface, escolha uma variante e use **Atualizar mercado**. A API cria uma
execução por fonte, o worker coleta as lojas sintéticas e o painel atualiza a
distribuição, as ofertas incluídas e as exclusões justificadas.

As portas publicadas ficam presas a `127.0.0.1`. PostgreSQL e lojas sintéticas não
são expostos no host.

## Serviços

| Serviço | Papel | Exposição |
| --- | --- | --- |
| `frontend` | React/Vite compilado e servido por Nginx; proxy same-origin da API | `127.0.0.1:3000` |
| `api` | FastAPI para fontes, execuções, catálogo e comparações | `127.0.0.1:8000` |
| `worker` | Procrastinate + subprocessos Scrapy | sem porta publicada |
| `postgres` | domínio, histórico, evidências e fila persistida | sem porta publicada |
| `migrate` | Alembic, schema Procrastinate e seed idempotente | job one-shot |
| `lab-store-a`, `lab-store-b` | páginas HTTP sintéticas realmente coletadas | rede interna do Compose |

## Comandos de desenvolvimento

Backend:

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run ty check .
uv run pytest
uv build
```

Frontend local, quando necessário:

```bash
cd frontend
npm install
npm run check
npm run build
```

Validação de containers:

```bash
docker compose config --quiet
docker compose build
```

## Configuração

Os defaults locais funcionam sem `.env`. Para trocar portas ou credenciais do
banco local, copie `.env.example` para `.env` e ajuste somente valores locais.
Nunca comite `.env` ou credenciais reais.

Variáveis principais:

- `API_PORT` e `FRONTEND_PORT`: portas no loopback do host;
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`: banco local;
- `LOG_LEVEL`: nível de log dos processos Python.

## API

| Método | Rota | Finalidade |
| --- | --- | --- |
| `GET` | `/sources` | lista fontes habilitadas |
| `POST` | `/sources/{source_id}/collect` | cria ou reutiliza uma coleta idempotente |
| `GET` | `/runs/{run_id}` | acompanha estado e estatísticas |
| `GET` | `/products` | lista produtos canônicos |
| `GET` | `/products/{product_id}/variants` | lista variantes |
| `GET` | `/variants/{variant_id}/comparison` | retorna população, faixa e exclusões |

## Parada, rollback e dados locais

Para parar mantendo o banco:

```bash
docker compose down
```

Rollback de código consiste em voltar ao commit anterior e reconstruir as imagens.
A migração atual possui `downgrade`, mas apagar ou retroceder dados não é parte
do fluxo normal.

Para reinicializar **deliberadamente** todos os dados sintéticos, remova também o
volume nomeado:

```bash
docker compose down --volumes
```

Esse último comando é destrutivo para o banco local. Não o execute quando quiser
preservar histórico de coletas.

## Limites atuais

- somente fontes sintéticas revisadas estão habilitadas;
- a API não possui autenticação e deve permanecer restrita ao loopback;
- recomendação de preço, demanda, elasticidade e automação comercial estão fora
  do escopo;
- antes de habilitar uma fonte real, é obrigatório adicionar contenção de destino
  contra SSRF e limites globais de crawl/resposta.

Consulte [produto](docs/product.md), [arquitetura](docs/architecture.md) e
[plano incremental](docs/implementation-plan.md) para contratos e estado atual.

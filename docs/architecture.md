# Arquitetura

## Visão geral

O sistema é um monólito modular Python executado em processos separados. API,
worker, migração e spiders compartilham o mesmo artefato e banco; Nginx serve o
frontend e faz proxy same-origin para a API.

```text
Browser -> Nginx/React -> FastAPI -> PostgreSQL
                               \-> Procrastinate job
                                    -> Worker -> Scrapy subprocess
                                                -> lab-store-a / lab-store-b
                                                -> PostgreSQL
```

PostgreSQL armazena domínio, histórico, evidências e a fila Procrastinate. Redis,
RabbitMQ e serviços cloud não são necessários no volume do MVP.

## Componentes e propriedade

- `api`: valida comandos, cria runs idempotentes e entrega read models;
- `jobs`: traduz o job persistido na máquina de estados da coleta;
- `collection`: busca HTML, extrai/normaliza e persiste observações/evidências;
- `matching`: associa a oferta a variante existente sem criar catálogo a partir de
  texto não confiável;
- `pricing`: filtra a população comparável e calcula estatísticas descritivas;
- `frontend`: representa estados reais da API, sem dados decorativos.

## Fluxo de dados

1. `POST /sources/{id}/collect` verifica que a fonte está habilitada.
2. Uma chave `source + minuto` converge cliques repetidos no mesmo run.
3. O job persistido move o run de `pending` para `running`.
4. Scrapy visita a categoria, pagina e descobre páginas de produto.
5. O extrator valida JSON-LD, separa vendedor, oferta, termos e variante.
6. A observação e sua evidência são persistidas; replay do mesmo run não duplica
   a observação.
7. O run termina em `succeeded`, `partial` ou `failed`.
8. A consulta usa somente a observação mais recente por oferta ativa.

## Persistência e invariantes

- dinheiro: inteiro em unidades mínimas + moeda ISO de três letras;
- observação: única por `(offer_id, collection_run_id)`;
- oferta: única por `(source_id, external_listing_id)`;
- página descoberta: única por `(source_id, canonical_url)`;
- match: no máximo um ativo por oferta; histórico anterior é preservado;
- evidência: hash do HTML, extrator/versão e excerpt limitado, com retenção por
  URL;
- GTIN presente é autoritativo: um GTIN desconhecido não cai para atributos.

SQL explícito é compartilhado entre acesso assíncrono (API/jobs) e síncrono
(pipeline Scrapy). Migrations Alembic controlam o schema.

## Redes e fronteiras de confiança

O Compose define:

- rede `application`: frontend, API, worker e PostgreSQL;
- rede `laboratory`, marcada `internal`: worker e lojas sintéticas;
- somente frontend/API publicam portas e apenas em `127.0.0.1`;
- imagens Python executam como usuário sem privilégio.

A API local não possui autenticação. Esse contrato depende do bind em loopback.
CORS permite apenas o servidor/preview Vite; no Docker, Nginx usa proxy same-origin.

URLs e HTML são entrada não confiável. No incremento atual, apenas duas fontes
sintéticas com links relativos e finitos estão habilitadas. Antes de qualquer fonte
real, bloquear destinos privados/link-local, restringir origem/protocolo e redirects,
limitar tamanho de resposta, profundidade, páginas, tempo e captura de logs.

## Recuperação

A fila é persistida no PostgreSQL. Reiniciar o worker não perde jobs pendentes.
Reprocessar um job já iniciado não repete efeitos. O sistema não promete exactly
once: garante convergência nos limites definidos pelas constraints e estados.

Falha de spider marca o run como `failed`; páginas descobertas que não chegaram a
uma observação mantêm o run `partial`. Dados anteriores continuam consultáveis e
identificados por timestamp.

## Observabilidade

Logs estruturados incluem `run_id`, fonte, spider, estado e estatísticas. A API
expõe healthcheck do banco e a consulta de run informa início, fim, contagens e
causa de falha. Métricas externas não são exigidas para a demonstração local.

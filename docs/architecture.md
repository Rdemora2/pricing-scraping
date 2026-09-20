# Arquitetura

## Visão geral

O sistema é um monólito modular Python executado em processos separados. API,
worker, migração e spiders compartilham o mesmo artefato e banco; Nginx serve o
frontend e faz proxy same-origin para a API.

```text
Browser -> Nginx/React -> FastAPI -> PostgreSQL
                               \-> Procrastinate job
                                    -> Worker -> Scrapy subprocess
                                                -> Fast Shop / Samsung Shop
                                                -> KaBuM! / Zoom
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
4. Scrapy visita somente a página revisada e limitada daquela fonte.
5. O extrator específico valida JSON-LD, separa vendedor, oferta, termos e
   variante; marketplaces preservam o vendedor efetivo.
6. A observação e sua evidência são persistidas; replay do mesmo run não duplica
   a observação.
7. O run termina em `succeeded`, `partial` ou `failed`.
8. A consulta usa somente a observação mais recente por oferta ativa e uma
   observação por varejista; evidência direta precede uma cópia agregada.

A descoberta ampla é um fluxo paralelo: a API consulta um provedor oficial de
busca, salva URLs como `source_candidate` e atribui um nível inicial de confiança.
Nenhum candidato é promovido automaticamente a `source`.

## Persistência e invariantes

- dinheiro: inteiro em unidades mínimas + moeda ISO de três letras;
- observação: única por `(offer_id, collection_run_id)`;
- oferta: única por `(source_id, external_listing_id)`;
- página descoberta: única por `(source_id, canonical_url)`;
- match: no máximo um ativo por oferta; histórico anterior é preservado;
- evidência: hash do HTML, extrator/versão e excerpt limitado, com retenção por
  execução e URL;
- GTIN presente é autoritativo: um GTIN desconhecido não cai para atributos.

## Estratégia de fontes

- **direta**: Fast Shop, Samsung Shop e KaBuM! fornecem a página que sustenta o
  preço; têm precedência na deduplicação;
- **agregadora**: Zoom adiciona amplitude, mas cada oferta é atribuída ao
  `offeredBy` publicado e não ao comparador;
- **referência**: Apple Brasil e Samsung Brasil sustentam catálogo/especificações,
  sem serem automaticamente tratadas como preço coletável;
- **candidata**: radar Brave ou cadastro manual grava URL, confiança e motivo;
  nenhuma URL descoberta executa spider automaticamente;
- **laboratório**: as fontes Nimbus validam o pipeline, mas nunca entram na visão
  de mercado real.

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

URLs e HTML são entrada não confiável. Adaptadores externos aceitam somente HTTPS,
host exato em allowlist, porta 443 e resolução pública; destinos privados,
loopback, link-local, multicast e reservados são rejeitados. Redirects passam pela
mesma política. Scrapy respeita robots.txt e impõe limites de resposta, redirect,
tempo, concorrência e páginas. Extratores aceitam no máximo 24 variantes ou 20
ofertas agregadas por página, limitando também a multiplicação de evidências. O
laboratório opta explicitamente por HTTP e rede privada. CAPTCHA, login e bloqueios
não são contornados.

A validação DNS anterior ao request reduz SSRF, mas não elimina completamente
DNS rebinding entre validação e conexão; execução local, allowlist exata e ausência
de URLs arbitrárias habilitadas reduzem esse risco residual.

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

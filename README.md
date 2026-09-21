# Signal Price

Plataforma local de inteligência de preços. A aplicação coleta ofertas públicas
em fontes reais revisadas, mantém um laboratório separado para regressão, associa
anúncios a variantes canônicas e apresenta comparações explicáveis.

O projeto prioriza profundidade de backend: coleta assíncrona, idempotência,
histórico, evidências, matching determinístico e regras explícitas de
comparabilidade. O fluxo principal não exige cloud; a descoberta ampla na web é
opcional e usa uma chave de provedor configurada somente no backend.

## Demonstração rápida

Requisitos: Docker com Compose v2 e aproximadamente 2 GB livres de memória.

Crie a configuração local e troque o placeholder de senha antes da primeira
execução:

```bash
cp .env.example .env
```

```bash
docker compose up --build
```

Acesse:

- frontend: <http://localhost:3000>;
- API e OpenAPI: <http://localhost:8000/docs>;
- healthcheck: <http://localhost:8000/health>.

Na interface, entre em **Inteligência de mercado**, escolha aparelho, capacidade
e cor e use **Atualizar mercado**. A API cria uma execução por fonte aplicável; o
worker pesquisa o aparelho dentro de cada fonte, descobre páginas compatíveis e
o painel atualiza varejistas distintos, canais de evidência, faixa de preço e
exclusões justificadas. A leitura executiva
do aparelho consolida as variantes e compara armazenamentos, custo por GB e o
efeito relativo das cores sem misturar capacidades diferentes.

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

## Estratégia de aquisição

Cada adaptador segue um waterfall explícito, sem exigir que uma integração
comercial esteja conectada:

1. **API oficial opcional**: quando a loja oferece a integração e suas
   credenciais estão configuradas, ela é a primeira opção. A ausência da
   conexão não interrompe a coleta.
2. **HTTP + JSON-LD**: o scraper busca primeiro `Product`, `ProductGroup` e
   `Offer`, preservando SKU, vendedor, disponibilidade e condição.
3. **HTML/DOM**: seletores específicos completam ou substituem campos que não
   estão estruturados, como o buy box visível ou o preço Pix.
4. **Chromium headless**: fica restrito a adaptadores revisados. Americanas e
   Carrefour podem usá-lo quando uma página permitida não contém evidência
   suficiente; a busca da KaBuM! pode usá-lo quando a grade de resultados
   depende de JavaScript. O adapter Amazon existe, mas permanece candidato após
   a homologação receber HTTP 503 sem produzir observações.

O fallback de navegador não resolve CAPTCHA, não autentica e não contorna HTTP
403. Ele bloqueia imagens, mídia, fontes e hosts não revisados; sua origem fica
registrada no nome versionado do extrator. No Docker, apenas o `worker` carrega o
runtime Chromium — API e migração continuam na imagem Python enxuta. O worker
executa sem root e sem capabilities, com `no-new-privileges`, raiz somente
leitura e `/tmp` isolado.

Nesta entrega, nenhuma API comercial está credenciada: as fontes habilitadas
entram diretamente no passo 2. Respostas de controle de acesso não acionam o
browser; ele só é elegível após uma resposta HTTP permitida cuja evidência ainda
seja insuficiente.

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
npm ci
npm run check
npm run build
```

Validação de containers:

```bash
docker compose config --quiet
docker compose build
docker compose --profile test run --rm test pytest tests/integration
```

O serviço `test` usa um estágio próprio com dependências de desenvolvimento e
não é iniciado no fluxo normal. API, migração e laboratório usam o estágio
Python enxuto; somente o worker usa o estágio com Chromium.

## Configuração

O Compose exige `POSTGRES_PASSWORD` para não incorporar senha no histórico. Copie
`.env.example` para `.env`, defina uma senha exclusivamente local e nunca comite
esse arquivo ou credenciais reais. As demais variáveis possuem defaults locais.

Variáveis principais:

- `API_PORT` e `FRONTEND_PORT`: portas no loopback do host;
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`: banco local;
- `LOG_LEVEL`: nível de log dos processos Python.
- `COMPARISON_MAX_AGE_HOURS`: janela da visão atual; padrão de 72 horas.
- `BRAVE_SEARCH_API_KEY`: opcional; habilita o radar de candidatos na internet.

## API

| Método | Rota | Finalidade |
| --- | --- | --- |
| `GET` | `/sources` | lista fontes habilitadas |
| `POST` | `/sources/{source_id}/collect` | pesquisa o `product_id` informado na fonte e cria ou reutiliza uma coleta idempotente |
| `GET` | `/runs/{run_id}` | acompanha estado e estatísticas |
| `GET` | `/products` | lista produtos canônicos |
| `GET` | `/products/{product_id}/variants` | lista variantes |
| `GET` | `/products/{product_id}/intelligence` | consolida inteligência por armazenamento e cor |
| `GET` | `/variants/{variant_id}/comparison` | retorna população, faixa e exclusões |
| `GET` | `/discovery/candidates` | lista referências encontradas para revisão |
| `POST` | `/discovery/search` | pesquisa a web sem habilitar novas fontes |
| `POST` | `/discovery/candidates` | cadastra uma referência para revisão |

## Catálogo e cobertura

O seed contém 17 aparelhos de mercado e 221 variantes canônicas, com proveniência
oficial versionada no código: linha iPhone 16, iPhone 17, iPhone Air e iPhone 18
Pro; Galaxy S25 e S26; e Motorola Edge 70 Pro. O laboratório adiciona somente
três variantes Nimbus isoladas. O cadastro amplo não é apresentado como cobertura
de preço. O seed possui 33 definições de fonte: Zoom, Buscapé, KaBuM!,
Americanas, Carrefour e Samsung Shop estão habilitadas como coletores de
mercado; duas lojas sintéticas ficam isoladas no laboratório; as demais raízes
são candidatas ou referências até que seu fluxo completo seja homologado.

O coletor é configurado pela identidade e raiz da fonte, nunca por uma URL de
produto. Ao receber o aparelho canônico, Zoom, Buscapé, KaBuM!, Americanas e
Carrefour geram buscas por capacidade, filtram modelo/capacidade exatos e seguem
um conjunto limitado de páginas descobertas. A Samsung Shop deriva a rota
oficial a partir do modelo canônico e extrai o grupo público de variantes. A URL
de produto passa a ser evidência da execução, não configuração permanente.
Marketplaces e comparadores preservam o vendedor efetivo de cada oferta.

O portfólio de qualificação inclui grandes redes nacionais, marketplaces,
varejistas especializados, fabricantes, operadoras, comparadores e comunidades
de promoção. Cadastro não significa integração: operadoras precisam separar
aparelho avulso de preço vinculado a plano; Shopee e AliExpress exigem produto
novo, estoque nacional, seller e garantia; Promobit e Pelando são sinais de
oportunidade cujos cupons nunca viram preço-base silenciosamente.
A decisão fonte a fonte, com run ou impedimento observado, está registrada em
[`docs/source-qualification.md`](docs/source-qualification.md).

A meta de produto é atingir **no mínimo 6–8 varejistas distintos por aparelho e
variante**, e continuar crescendo além disso. A interface não transforma essa
meta em dado: ela mostra a cobertura realmente coletada. Uma oferta repetida no
site direto e em comparador conta uma vez; aliases conhecidos, como Magalu e
Magazine Luiza, também são consolidados. Em uma execução local de referência em
`2026-09-21`, as buscas de raiz de Zoom, Buscapé e KaBuM! produziram,
respectivamente, `25`, `49` e `11` observações brutas para o iPhone 17 Pro Max;
Americanas e Carrefour acrescentaram runs homologados com `6` e `3`
observações. Após matching e deduplicação, a inteligência registrou `54` ofertas de `17`
varejistas e cobertura `12/12`: as três cores canônicas de `256 GB`, `512 GB`,
`1 TB` e `2 TB` passaram a ter evidência. A diversidade por configuração exata
variou de `3` a `11` varejistas; portanto a meta de 6–8 ainda não é declarada
como universalmente atingida.

## Inteligência por aparelho

A central parte das comparações exatas de cada variante e só depois agrega o
modelo. O preço representativo de um armazenamento é a mediana das variantes de
cor observadas; o custo-benefício é o menor preço representativo por GB. Ele só é
declarado com duas cores por capacidade, duas capacidades elegíveis e três
varejistas. O índice de cor compara cada cor com a mediana das cores do mesmo
armazenamento e consolida os desvios percentuais. A resposta informa cobertura do catálogo,
tamanho da amostra e metodologia. Quando faltam duas capacidades ou combinações
equivalentes de cor, a recomendação correspondente permanece explicitamente em
formação. Por padrão, somente observações das últimas 72 horas influenciam a visão
atual; registros mais antigos continuam no histórico e aparecem como exclusões.

## Parada, rollback e dados locais

Para parar mantendo o banco:

```bash
docker compose down
```

Rollback de código consiste em voltar ao commit anterior e reconstruir as imagens.
A migração atual possui `downgrade`, mas apagar ou retroceder dados não é parte
do fluxo normal.

Para reinicializar **deliberadamente** todos os dados locais, remova também o
volume nomeado:

```bash
docker compose down --volumes
```

Esse último comando é destrutivo para o banco local. Não o execute quando quiser
preservar histórico de coletas.

## Limites atuais

- o Galaxy S26 base ainda está em cinco varejistas distintos na variante Dourado
  observada; a limitação externa de oferta está registrada em
  `docs/ai/delivery/evidence/INC-05.md`, e ampliar fontes diretas continua
  necessário para fechar o piso sem contar aliases ou misturar variantes;
- iPlace, Magalu, Casas Bahia, Ponto, Extra, Pichau, TerabyteShop, JáCotei e Vivo
  permanecem candidatas após HTTP 403 na homologação local. Ofertas desses
  vendedores podem aparecer em agregadores quando
  variante, condição, seller e preço forem verificáveis;
- Apple Brasil é referência canônica, não fonte automatizada; seus termos vedam
  automação da página;
- iPhone 18 Pro/Pro Max e Motorola Edge 70 Pro já podem ser pesquisados pelos
  coletores genéricos, mas permanecem sem evidência suficiente para declarar
  cobertura brasileira; o portal não simula preço quando a busca volta vazia;
- ofertas do Galaxy S25+ que omitem a cor continuam excluídas pelo matching; a
  busca mais ampla não relaxa identidade de variante para preencher cobertura;
- Mercado Livre ainda exige homologação de sua integração oficial. Sem essa
  conexão, o sistema continua operando com os scrapers habilitados; Casas Bahia
  e Ponto permanecem candidatos a adaptadores diretos dedicados;
- Amazon permanece candidata: o adapter de busca está coberto por testes, mas a
  execução completa recebeu HTTP 503 e não produziu evidência. Bondfaro foi
  rebaixado porque o `robots.txt` recusou a busca; Fast Shop também não autoriza
  sua busca automatizada;
- candidatos da busca ampla exigem revisão humana e adaptador dedicado antes de
  qualquer coleta;
- requests HTTP declaram o coletor e negociam HTML em português com cabeçalhos
  estáveis de representação; não enviam fingerprint de Chrome nem perfil de
  usuário autenticado;
- a API não possui autenticação e deve permanecer restrita ao loopback;
- recomendação de preço, demanda, elasticidade e automação comercial estão fora
  do escopo;
- CAPTCHA, autenticação, paywall e bloqueios de acesso não são contornados.

Consulte [produto](docs/product.md), [arquitetura](docs/architecture.md) e
[plano incremental](docs/implementation-plan.md) para contratos e estado atual.

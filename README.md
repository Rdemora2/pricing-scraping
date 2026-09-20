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
worker coleta as páginas revisadas e o painel atualiza varejistas distintos,
canais de evidência, faixa de preço e exclusões justificadas. A leitura executiva
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
4. **Chromium headless**: somente Amazon, Americanas e Carrefour estão
   autorizadas a usá-lo quando a resposta HTTP não contém evidência suficiente.

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
| `POST` | `/sources/{source_id}/collect` | cria ou reutiliza uma coleta idempotente |
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
de preço: coletores permanecem habilitados apenas para as páginas efetivamente
revisadas. Fontes habilitadas para as seis famílias prioritárias:

- Samsung Shop, com variantes estruturadas dos três Galaxy;
- Fast Shop, com páginas diretas dos três iPhones;
- KaBuM!, incluindo identificação do vendedor quando a página é marketplace;
- Zoom, como canal agregador que preserva o varejista efetivo de cada oferta;
- 2aFinder, por documento Markdown público, com vendedor, canal, condição, frete,
  variante, timestamp e identificador de oferta;
- Buscapé, pela página pública e pelo documento de ofertas que ela própria
  consome, sem seguir redirecionamentos comerciais;
- Amazon Brasil, pelo buy box visível da página de produto;
- Americanas, preservando o vendedor efetivo publicado no marketplace;
- Carrefour, preservando vendedor e preço à vista no Pix — inclusive ofertas
  de MCS Variedades e Loja iPlace;
- duas lojas sintéticas isoladas, usadas somente para regressão do pipeline.

A meta de produto é atingir **no mínimo 6–8 varejistas distintos por aparelho e
variante**, e continuar crescendo além disso. A interface não transforma essa
meta em dado: ela mostra a cobertura realmente coletada. Uma oferta repetida no
site direto e em comparador conta uma vez; aliases conhecidos, como Magalu e
Magazine Luiza, também são consolidados. Em uma coleta real de referência em
`2026-09-20`, as variantes prioritárias observaram `9/11/9/5/6/6` varejistas
para iPhone 17/Pro/Pro Max e Galaxy S26/S26+/Ultra, respectivamente. Cinco das
seis famílias atingem o piso. Além dessa matriz, o iPhone 17 256 GB Preto abre
como variante principal com `6` varejistas em `6` canais após a inclusão direta
de Amazon, Americanas e Carrefour. O Galaxy S26 base Dourado permanece em cinco: a
própria Samsung classifica Dourado/Prata como cores exclusivas da loja oficial, e
a coleta pública atual não expõe um sexto vendedor novo, disponível e exato sem
duplicar a Samsung ou misturar variante.

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
- iPlace e Magalu permanecem candidatos diretos porque suas páginas responderam
  HTTP 403 ao user-agent declarado do coletor. Ofertas desses vendedores podem
  aparecer quando Americanas ou Carrefour as publicam com variante e preço
  verificáveis;
- Apple Brasil é referência canônica, não fonte automatizada; seus termos vedam
  automação da página;
- os modelos recém-cadastrados das linhas iPhone 16/18, Galaxy S25 e Motorola
  ainda não possuem coletores habilitados; o portal mostra esse estado e orienta
  a descoberta/qualificação, sem simular preço ou cobertura;
- Mercado Livre ainda exige homologação de sua integração oficial. Sem essa
  conexão, o sistema continua operando com os scrapers habilitados; Casas Bahia
  e Ponto permanecem candidatos a adaptadores diretos dedicados;
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

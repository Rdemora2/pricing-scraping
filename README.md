# Signal Price

Plataforma local de inteligência de preços. A aplicação coleta ofertas públicas
em fontes reais revisadas, mantém um laboratório separado para regressão, associa
anúncios a variantes canônicas e apresenta comparações explicáveis.

O projeto prioriza profundidade de backend: coleta assíncrona, idempotência,
histórico, evidências, matching determinístico e regras explícitas de
comparabilidade. O fluxo principal não exige cloud; a descoberta ampla na web é
opcional e usa uma chave de provedor configurada somente no backend.

## Início rápido com Docker

O caminho recomendado não exige Python, Node.js nem PostgreSQL instalados no
host. Todos os serviços, migrações, seed e o Chromium do coletor ficam nos
containers.

### Requisitos por sistema operacional

| Sistema | Requisito | Observação |
| --- | --- | --- |
| macOS | Docker Desktop 4+ com Compose v2 | Apple Silicon e Intel são suportados pelas imagens base multiarch. |
| Windows 10/11 | Docker Desktop 4+ usando o backend WSL 2 | Execute os comandos no PowerShell ou em uma distribuição WSL 2; mantenha o repositório no filesystem do WSL para melhor desempenho. |
| Linux | Docker Engine 24+ e plugin Docker Compose v2 | O usuário precisa acessar o daemon Docker; não use `sudo` se sua instalação já estiver configurada para o grupo `docker`. |

Reserve ao menos 4 GB de memória para o Docker e cerca de 5 GB de disco para
imagens, cache de build e banco local. Git é necessário apenas para clonar o
repositório.

### 1. Configure o ambiente

No macOS, Linux ou WSL:

```bash
cp .env.example .env
```

No PowerShell:

```powershell
Copy-Item .env.example .env
```

Edite `.env` e substitua o placeholder de `POSTGRES_PASSWORD` por uma senha
exclusivamente local. O arquivo é ignorado pelo Git e nunca deve receber uma
credencial real ou de produção.

### 2. Suba a plataforma

```bash
docker compose up --build -d
docker compose ps
```

Na primeira execução, o Compose constrói as imagens, aplica o schema, cria a fila
persistida e popula o catálogo idempotentemente. Aguarde os serviços `api`,
`frontend`, `postgres` e lojas de laboratório ficarem `healthy`; o `migrate`
termina com estado `Exited (0)` por ser um job one-shot.

### 3. Acesse e valide

- frontend: <http://localhost:3000>;
- API e OpenAPI: <http://localhost:8000/docs>;
- healthcheck: <http://localhost:8000/health>.

Checks rápidos, iguais em macOS, Windows e Linux:

```bash
docker compose ps
docker compose logs --tail=100 api worker
docker compose --profile test run --rm test pytest tests/integration
```

Na interface, entre em **Inteligência de mercado**, escolha aparelho, capacidade
e cor e use **Atualizar mercado**. A API cria uma execução por fonte aplicável; o
worker pesquisa o aparelho dentro de cada fonte, descobre páginas compatíveis e
o painel atualiza varejistas distintos, canais de evidência, faixa de preço e
exclusões justificadas. Durante a execução, a interface acompanha o progresso
por fonte e preserva resultados parciais quando uma delas não encontra ofertas.
A leitura executiva do aparelho consolida as variantes, mostra a escada de preço
entre capacidades adjacentes e mede o efeito relativo das cores sem misturar
configurações diferentes.

As portas publicadas ficam presas a `127.0.0.1`. PostgreSQL e lojas sintéticas não
são expostos no host.

## Solução de problemas local

- **`POSTGRES_PASSWORD_required`**: confirme que `.env` existe na raiz e contém
  `POSTGRES_PASSWORD` sem o placeholder original.
- **porta 3000 ou 8000 ocupada**: altere `FRONTEND_PORT` ou `API_PORT` em `.env`
  e recrie os serviços com `docker compose up -d`.
- **frontend abriu antes do backend**: consulte `docker compose ps`; o frontend
  só inicia depois do healthcheck da API. Use `docker compose logs api migrate`
  para identificar a causa.
- **worker consome muita memória**: confirme que o Docker possui ao menos 4 GB
  disponíveis. O Chromium existe somente no worker e é iniciado sob demanda.
- **mudança de código não apareceu**: execute `docker compose up --build -d` para
  reconstruir e recriar as imagens.
- **Windows lento em `/mnt/c`**: clone o projeto dentro do filesystem da
  distribuição WSL 2 e execute o Compose a partir dali.

Não use `docker compose down --volumes` como tentativa genérica de correção: ele
apaga todo o histórico local. A seção de rollback explica quando esse reset é
apropriado.

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

Cada execução informa, além das observações e evidências, quantas listagens
foram descartadas e em qual etapa: `access` quando a fonte recusou a página,
`extraction` quando o adaptador não leu a página como oferta, e `matching`
quando a oferta foi lida mas não corresponde a nenhuma variante canônica. Os
descartes ficam em `listing_rejection` com motivo e título bruto. A política
continua fail-closed — um anúncio que não nomeia a cor segue fora da
comparação, porque identidade de variante não é relaxada para preencher
cobertura — mas o custo de falhar fechado passou a ser mensurável, e é o que
permite distinguir "a fonte não tem oferta" de "nós descartamos".

O fallback de navegador não resolve CAPTCHA, não autentica e não contorna HTTP
403 — ele só nasce de uma resposta HTTP permitida cuja evidência é insuficiente,
nunca de um bloqueio. Ele bloqueia imagens, mídia, fontes e hosts não revisados; sua origem fica
registrada no nome versionado do extrator. No Docker, apenas o `worker` carrega o
runtime Chromium — API e migração continuam na imagem Python enxuta. O worker
executa sem root e sem capabilities, com `no-new-privileges`, raiz somente
leitura e `/tmp` isolado.

Nesta entrega, nenhuma API comercial está credenciada: as fontes habilitadas
entram diretamente no passo 2. Respostas de controle de acesso não acionam o
browser; ele só é elegível após uma resposta HTTP permitida cuja evidência ainda
seja insuficiente.

## Comandos de desenvolvimento

O fluxo abaixo é opcional e destinado a quem deseja executar ferramentas fora
dos containers. Use Python 3.14, `uv` 0.12+, Node.js 26 e npm compatível com o
`package-lock.json`; PostgreSQL 17 pode continuar no Compose. No Windows, prefira
esse fluxo dentro do WSL 2. Não atualize versões ou lockfiles apenas para iniciar
o projeto.

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
| `GET` | `/runs/{run_id}` | acompanha estado e estatísticas, incluindo o funil de descartes |
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
Americanas e Samsung Shop estão habilitadas como coletores de
mercado; duas lojas sintéticas ficam isoladas no laboratório; as demais raízes
são candidatas ou referências até que seu fluxo completo seja homologado.

O coletor é configurado pela identidade e raiz da fonte, nunca por uma URL de
produto. Ao receber o aparelho canônico, Zoom, Buscapé, KaBuM! e Americanas
geram buscas por capacidade, filtram modelo/capacidade exatos e seguem
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
Americanas e Carrefour acrescentaram runs históricos com `6` e `3`
observações. Após matching e deduplicação, a inteligência registrou `54` ofertas de `17`
varejistas e cobertura `12/12`: as três cores canônicas de `256 GB`, `512 GB`,
`1 TB` e `2 TB` passaram a ter evidência. A diversidade por configuração exata
variou de `3` a `11` varejistas; portanto a meta de 6–8 ainda não é declarada
como universalmente atingida.

Em `2026-09-22`, a paginação do documento público de ofertas do Buscapé e a
correção de aliases de cor mudaram essa escala. O Galaxy S25 Ultra, que estava
preso em `20` observações por bater no teto de ofertas de agregador, passou a
`29`. O iPhone 17 Pro Max passou a registrar, **em uma única fonte**, cobertura
`12/12`, `56` ofertas e `17` varejistas distintos — o que a execução de
referência anterior só alcançava somando cinco fontes. A diversidade por
configuração exata continua variando de `3` a `11` varejistas nessa fonte
isolada, então a meta de 6–8 segue sem ser declarada universalmente atingida.

## Inteligência por aparelho

A central parte das comparações exatas de cada variante e só depois agrega o
modelo. O preço representativo de um armazenamento é a mediana das variantes de
cor observadas. Em vez de declarar a maior capacidade como melhor compra por
diluição de custo por GB, a escada informa quanto o preço mediano sobe, em reais
e em percentual, entre capacidades adjacentes. Cada salto exige duas cores
observadas em cada ponta e três varejistas entre as duas capacidades. O índice de cor compara
cada cor com a mediana das cores do mesmo armazenamento e consolida os desvios
percentuais. A resposta informa cobertura do catálogo,
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
- Carrefour continua candidata por dois caminhos medidos, não por suposição: o
  `robots.txt` proíbe `/busca/`, rota do coletor orientado por aparelho, e o
  sitemap que ele publica não é navegável por aparelho — `5305` documentos no
  índice, `5290` deles com `1000` URLs cada, cerca de `5,29` milhões de URLs
  sem ordenação por marca ou categoria. Navegação por categoria, que o
  `robots.txt` não proíbe, é a próxima rota candidata e ainda não foi
  homologada;
- Amazon permanece candidata: o adapter de busca está coberto por testes, mas a
  execução completa recebeu HTTP 503 e não produziu evidência. Bondfaro foi
  rebaixado porque o `robots.txt` recusou a busca; Fast Shop também não autoriza
  sua busca automatizada. Carrefour também voltou a candidato em `2026-09-21`:
  páginas de produto continuam públicas, mas o `robots.txt` atual proíbe
  `/busca/`, rota necessária ao coletor orientado pelo aparelho;
- candidatos da busca ampla exigem revisão humana e adaptador dedicado antes de
  qualquer coleta;
- requests HTTP negociam HTML em português com um perfil de cabeçalhos
  realista de Chrome/Windows atual (ver [decisions/0001](docs/ai/decisions/0001-browser-realistic-http-profile.md));
  não enviam cookie de sessão nem perfil de usuário autenticado, e o fallback
  de navegador nunca é acionado para contornar um bloqueio;
- a API não possui autenticação e deve permanecer restrita ao loopback;
- recomendação de preço, demanda, elasticidade e automação comercial estão fora
  do escopo;
- CAPTCHA, autenticação, paywall e bloqueios de acesso não são contornados.

Consulte [produto](docs/product.md), [arquitetura](docs/architecture.md) e
[plano incremental](docs/implementation-plan.md) para contratos e estado atual.

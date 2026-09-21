# Evidência INC-10 — busca por fonte e experiência de pricing

## Escopo e estado

- Branch: `feature/inc-10-pricing-experience`, derivada do snapshot local do
  INC-09.
- Estado: `LOCAL_VERIFIED_WITH_EXTERNAL_GATE`.
- Objetivo: substituir coletores vinculados a páginas por coletores de fonte
  orientados pelo aparelho e reduzir a seleção de variantes a um fluxo claro de
  armazenamento e cor.
- Gate externo: a revisão independente não está disponível nesta execução. A
  diversidade de 6–8 varejistas também continua uma meta por configuração, não
  um aceite artificialmente preenchido.

## Implementação

- `POST /sources/{source_id}/collect` exige `product_id`; a idempotência passa a
  considerar fonte, aparelho e minuto.
- O worker resolve nome, modelo e capacidades canônicas e os entrega ao spider.
- Zoom, Buscapé, KaBuM!, Americanas e Carrefour são semeados uma única vez pela
  raiz. Cada adapter cria
  uma busca por capacidade, aceita somente páginas do mesmo host com modelo e
  capacidade exatos e segue no máximo três resultados por capacidade.
- A KaBuM! tenta HTTP primeiro e usa Chromium limitado à própria origem apenas
  quando a grade de busca depende de JavaScript. CAPTCHA, login e controle de
  acesso não são contornados.
- URLs específicas legadas são desabilitadas pelo seed. Páginas descobertas são
  evidência da execução, não configuração do coletor.
- A inteligência inclui as variantes canônicas ainda sem oferta, permitindo à
  UI distinguir lacuna de cobertura de preço zero.
- A tela principal mostra primeiro armazenamento e depois cor, com contagem de
  ofertas, mediana e estado vazio. A comparação da configuração vem antes da
  visão consolidada do aparelho.

## Evidência funcional real

Produto focal: `Apple iPhone 17 Pro Max`.

- Zoom, run `c7461e5f-9f78-422b-bde8-e194ff2f6d23`: `succeeded`, `25`
  observações e `65` evidências.
- Buscapé, run `42ba3f21-f4bb-4984-8854-1103ec6aa5fa`: `succeeded`, `49`
  observações e `49` evidências.
- KaBuM!, run `315b10cc-e684-41b5-a0a2-5325bb7ddd81`: `succeeded`, `11`
  observações e `11` evidências após descoberta JavaScript limitada.
- Americanas, run `1df5115e-f6d4-4ae2-8f28-67cd410a0868`: `succeeded`, `6`
  observações e `6` evidências.
- Carrefour, run `fb3a4497-6d71-4796-aa5b-bb15a91772f8`: `succeeded`, `3`
  observações e `3` evidências.
- Samsung Shop, produto `Samsung Galaxy S26 Ultra`, run
  `605b782f-966f-4777-a7c9-588e2c847e09`: `succeeded`, `6` observações e `6`
  evidências.
- Amazon, run `b1cfb06e-aad0-46c3-b06a-fc7cc3d76d24`: `failed`, sem
  observações após HTTP 503; Bondfaro, run
  `5836dd68-5d46-4ce0-8d4a-37b647945baa`: `failed`, recusado pelo
  `robots.txt`. Ambas voltaram a `candidate`.
- Readback da inteligência: `12/12` configurações observadas, cobertura `100%`,
  `54` ofertas deduplicadas e `17` varejistas. 256 GB, 512 GB, 1 TB e 2 TB
  possuem as três cores canônicas; a diversidade exata varia de `3` a `11`
  varejistas.
- Readback de fontes habilitadas: Zoom, Buscapé, KaBuM!, Americanas, Carrefour e
  Samsung Shop como mercado, todos com URL raiz, mais as duas fontes isoladas de
  laboratório. O seed mapeia
  33 fontes no total; as demais ficam explicitamente candidatas ou referências,
  incluindo varejo geral, marketplaces, especialistas, fabricantes, operadoras,
  comparadores e comunidades de promoção.

## Verificação

- `uv run pytest`: `144 passed`, `2 skipped` sem `API_BASE_URL`.
- `uv run ruff check .` e `uv run ruff format --check .`: aprovados.
- `uv run ty check .`: aprovado.
- `uv build`: sdist e wheel construídos.
- `npm --prefix frontend run check` e `npm --prefix frontend run build`:
  aprovados.
- `docker compose config --quiet` e build de `api`, `worker`, `frontend` e
  `test`: aprovados.
- `docker compose --profile test run --rm test pytest tests/integration`:
  `2 passed`.
- Stack final: PostgreSQL, duas lojas de laboratório, API e frontend saudáveis;
  worker em execução; API respondeu `{"status":"ok"}`.
- Browser desktop: iPhone 17 Pro Max exibiu 512 GB, 1 TB e 2 TB com três cores;
  as comparações de 512 GB e 2 TB foram alternadas e renderizadas sem erro.
- Browser final: iPhone mostra cinco coletores aplicáveis e Samsung Galaxy S26
  Ultra mostra seis, incluindo Samsung Shop. O aviso do Brave Search foi movido
  da sidebar colapsável para o formulário do Radar, com quebra responsiva.
- Browser mobile em `390x844`: sem overflow horizontal, sem erros de página e
  zero violações WCAG A/AA automatizadas. O axe manteve apenas verificações
  manuais inconclusivas onde o fundo usa gradiente.
- A revisão local em dois ciclos corrigiu mistura potencial entre modelos
  vizinhos, limite insuficiente de páginas, estado visual obsoleto na troca de
  aparelho e contraste do registro de fontes. Não restaram achados locais; por
  restrição do runtime, esse parecer não é tratado como revisão independente.

## Riscos e rollback

- Markup, disponibilidade e vendedores são externos; a busca falha fechada e
  limita URLs/páginas, mas exige manutenção quando a fonte muda.
- Agregadores podem publicar a mesma oferta; a leitura atual consolida aliases e
  mantém uma observação por varejista.
- As configurações com três ou quatro varejistas ainda não cumprem o piso de
  amostragem solicitado e devem orientar a próxima homologação de raízes.
- Rollback de código: reverter o incremento. O seed torna fontes legadas
  desabilitadas sem apagar o histórico existente; não é necessário remover o
  volume PostgreSQL.

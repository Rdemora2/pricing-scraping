# Arquitetura

## Visão geral

O sistema é um monólito modular Python executado em processos separados. API,
worker, migração e spiders compartilham o mesmo artefato e banco; Nginx serve o
frontend e faz proxy same-origin para a API.

```text
Browser -> Nginx/React -> FastAPI -> PostgreSQL
                               \-> Procrastinate job
                                    -> Worker -> Scrapy subprocess
                                                -> busca por fonte e aparelho
                                                -> Zoom / Buscapé / KaBuM!
                                                -> lab-store-a / lab-store-b
                                                -> PostgreSQL
```

PostgreSQL armazena domínio, histórico, evidências e a fila Procrastinate. Redis,
RabbitMQ e serviços cloud não são necessários no volume do MVP.

## Componentes e propriedade

- `api`: valida comandos, cria runs idempotentes e entrega read models;
- `jobs`: traduz o job persistido na máquina de estados da coleta;
- `collection`: busca HTML, extrai/normaliza e persiste observações/evidências;
- `catalog`: mantém identidade, variantes e proveniência oficial sem armazenar
  preços ou habilitar fontes;
- `matching`: associa a oferta a variante existente sem criar catálogo a partir de
  texto não confiável;
- `pricing`: filtra a população comparável e calcula estatísticas descritivas;
- `pricing/intelligence`: agrega comparações exatas em indicadores explicáveis de
  armazenamento, cor, cobertura e diferença entre capacidades adjacentes;
- `frontend`: representa estados reais da API, sem dados decorativos.

## Fluxo de dados

1. `POST /sources/{id}/collect` recebe `product_id` e verifica que produto e
   fonte estão habilitados.
2. Uma chave `source + product + minuto` converge cliques repetidos no mesmo run.
3. O job persistido move o run de `pending` para `running`.
4. O worker resolve nome, modelo e capacidades do catálogo. O adapter constrói
   uma busca interna para cada capacidade na raiz da fonte; URLs de produto não
   fazem parte da configuração persistida do coletor.
5. O resultado da busca só é seguido quando pertence ao host permitido, contém
   todos os tokens do modelo e a capacidade exata. Cada capacidade segue no
   máximo três páginas, limitando amplitude e duplicação.
6. A coleta das páginas descobertas prioriza JSON-LD e usa seletores DOM
   específicos para campos ausentes. A busca da KaBuM! pode repetir a descoberta
   em Chromium headless quando a resposta permitida depende de JavaScript;
   Americanas preserva o fallback de página já implementado. O
   adapter Amazon permanece disponível, mas não é executável enquanto a
   homologação pública responder HTTP 503. Carrefour permanece candidato porque
   a política pública atual proíbe a rota `/busca/`. A evidência identifica o extrator.
7. O extrator separa vendedor, oferta, termos e variante; marketplaces preservam
   o vendedor efetivo.
8. A observação e sua evidência são persistidas; replay do mesmo run não duplica
   a observação.
9. O run termina em `succeeded`, `partial` ou `failed`.
10. A consulta usa somente a observação mais recente por oferta ativa e uma
   observação por varejista; evidência direta precede uma cópia agregada.
11. A inteligência de aparelho carrega todas as ofertas atuais em uma consulta,
    calcula cada variante isoladamente e somente então agrega dimensões.

A descoberta ampla é um fluxo paralelo: a API consulta um provedor oficial de
busca, salva URLs como `source_candidate` e atribui um nível inicial de confiança.
Nenhum candidato é promovido automaticamente a `source`.

## Persistência e invariantes

- dinheiro: inteiro em unidades mínimas + moeda ISO de três letras;
- condição comercial: base do preço, parcelas, desconto, cupom e vínculo ficam
  explícitos; preço condicionado não entra silenciosamente como preço-base;
- observação: única por `(offer_id, collection_run_id)`;
- oferta: única por `(source_id, external_listing_id)`;
- página descoberta: única por `(source_id, canonical_url)`;
- match: no máximo um ativo por oferta; histórico anterior é preservado;
- evidência: hash do HTML, extrator/versão e excerpt limitado, com retenção por
  execução e URL;
- GTIN presente é autoritativo: um GTIN desconhecido não cai para atributos.

## Estratégia de fontes

- **coletor homologado**: Zoom, Buscapé, KaBuM! e Americanas são
  registrados uma vez pela raiz e pesquisam o aparelho selecionado. Samsung
  Shop resolve a rota pública a partir do modelo canônico. A URL de produto
  descoberta é evidência efêmera da execução, não uma nova fonte;
- **adapter candidato**: Carrefour mantém extração de páginas de produto e
  histórico auditável, mas não oferece execução enquanto o `robots.txt` proibir
  a rota de busca necessária à descoberta por aparelho;
- **direta**: a KaBuM! fornece a página que sustenta o preço e tem precedência na
  deduplicação. Em marketplaces, canal e vendedor efetivo permanecem identidades
  separadas;
- **agregadora**: Zoom e Buscapé adicionam amplitude, mas cada oferta é atribuída
  ao vendedor publicado e não ao comparador. Lead/afiliado nunca é seguido; a
  evidência permanece na página ou documento público de comparação;
- **raiz candidata**: grandes redes, marketplaces, varejistas especializados,
  operadoras e comparadores permanecem cadastrados sem execução até que sua
  busca interna e semântica comercial sejam homologadas. Páginas históricas
  específicas são desabilitadas pelo seed;
- **sinal promocional**: Promobit e Pelando podem descobrir oportunidades, mas
  cupom, Pix, clube e validade precisam permanecer condições explícitas;
- **preço condicionado**: Claro, Vivo e TIM exigem identificar aparelho avulso
  e excluir preço que dependa de plano, portabilidade ou fidelização;
- **referência**: Apple Brasil, Samsung Brasil e Motorola Brasil sustentam
  catálogo/especificações, sem serem automaticamente tratadas como preço
  coletável;
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

O perfil HTTP negocia representação como um Chrome/Windows atual: user-agent,
`Sec-CH-UA`/`Sec-Fetch-*` e `Accept-Language` priorizando `pt-BR` — decisão
registrada em [`decisions/0001`](ai/decisions/0001-browser-realistic-http-profile.md)
após reversão do perfil transparente anterior (INC-07B). Cookie de sessão,
autenticação e resolução de CAPTCHA continuam fora do coletor; um bloqueio
(401/403/429/`robots.txt`) nunca aciona o fallback de navegador — ver abaixo.

O browser é opt-in por request e roda com um único contexto e uma página por
worker. Sua política própria bloqueia recursos visuais e qualquer subrequest fora
da allowlist HTTPS da fonte; os hosts auxiliares também passam por pré-validação
DNS pública, porque tráfego do Playwright não atravessa os
middlewares do downloader Scrapy. O sandbox de namespace interno do Chromium é
desabilitado no container; a fronteira externa compensa isso com usuário não-root,
capabilities removidas, `no-new-privileges`, limite de processos, raiz somente
leitura e `/tmp` efêmero. API, migração e frontend não carregam Chromium.
HTTP 401, 403, 429, bloqueio por `robots.txt` e falhas de transporte não são
convertidos em navegação headless; o fallback nasce somente de uma resposta
permitida que não forneceu os campos comerciais exigidos.

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

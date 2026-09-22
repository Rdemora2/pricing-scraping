# Estado de execução

**Atualizado em:** `2026-09-22`
**Estado global:** `IN_REVIEW`
**Unidade ativa:** `INC-13` — corrige teto de cores por busca de capacidade (3→8), validado com execução real do pipeline completo

O roadmap conclui o laboratório e avança o portal local de inteligência de
preços com fontes reais. A entrega permanece limitada ao ambiente local; não
inclui deploy ou cloud.

No snapshot atual, 146 testes locais passaram e dois testes de integração foram
corretamente ignorados sem `API_BASE_URL`; os mesmos dois passaram no container
dedicado. Ruff, formatação, `ty`, pacote Python, frontend, imagens Docker, health,
coleta real e navegação desktop/mobile estão verdes. API, worker e frontend foram
reconstruídos e executados no Compose local.

O `INC-04` inclui 76 variantes Apple/Samsung, Fast Shop, Samsung Shop, KaBuM! e
Zoom, descoberta ampla governada e portal completo. O `INC-05` adiciona 2aFinder
e Buscapé, separa URL comercial de evidência e mede `9/11/9/5/6/6` varejistas nas
variantes prioritárias. Cinco famílias atingem o piso; o Galaxy S26 Dourado
permanece sob gate externo exato de oferta. O laboratório continua isolado das
métricas reais.

O `INC-06` adiciona Amazon, Americanas e duas ofertas Carrefour ao caso iPhone 17
256 GB Preto, que passa a seis varejistas em seis canais. A aquisição documenta
API oficial opcional e, sem conexão, segue por JSON-LD/DOM HTTP; somente resposta
permitida e insuficiente pode acionar Chromium. Respostas de controle de acesso
não acionam browser.

O `INC-07A` entrega a primeira central de inteligência por aparelho. Ela calcula
primeiro cada variante exata e depois agrega cobertura, faixa, diferenças entre
capacidades adjacentes e diferenças de cor normalizadas por armazenamento. Insights permanecem
ausentes quando a amostra não sustenta a comparação. Testes, análise estática,
build, imagens Docker e navegação desktop/mobile estão verdes; a revisão
independente permanece como gate externo.

O `INC-07B` torna explícita a negociação HTTP de HTML em português, preservando
o user-agent declarado do coletor. Fingerprint de Chrome, cookies de usuário,
rotação de identidade e contorno de CAPTCHA permanecem fora do contrato. A suíte
de 93 testes, lint, typecheck e build estão verdes; revisão independente segue
como gate externo.

O `INC-08` reabre a superfície completa antes da entrega final. A revisão inicial
identificou preço zero aceito em uma fronteira, estágio Docker incorreto para
serviços sem browser, comando de teste em container não reproduzível e catálogo
menor que as famílias oficialmente disponíveis. O catálogo agora centraliza 17
aparelhos e 221 variantes de mercado com proveniência oficial; modelos ainda sem
adapter permanecem explicitamente sem coleta, sem preços fictícios. As correções
são entregues em commits independentes e revalidadas no snapshot consolidado.
O snapshot final soma 102 testes unitários verdes, 2 integrações executadas no
container dedicado, 72% de cobertura global, pacote e imagens construídos, stack
completa saudável e auditoria WCAG sem violações confirmadas em mobile. O gate de
revisão independente permanece externo e impede declarar merge concluído.

O `INC-09` torna a identidade e a normalização de cores/capacidades dirigidas
pelo catálogo completo de 17 aparelhos de mercado. Sete páginas Zoom, sete
Buscapé e três Samsung Shop adicionais passaram por coleta pública; o seed agora
possui 51 fontes habilitadas, incluindo as duas lojas de laboratório. Os
collectors cobrem 14 famílias com ao menos uma página homologada. Galaxy S25+
permanece candidato nos agregadores porque suas ofertas omitem a cor; iPhone 18
Pro/Pro Max e Motorola Edge 70 Pro ainda não apresentam matriz pública brasileira
estável e ampla. A unidade permanece `BLOCKED_EXTERNAL`: não seria correto
declarar cobertura de 6–8 varejistas por variante nesses casos, e a revisão
independente do stack anterior continua pendente.

O `INC-10` corrige o vínculo conceitual entre fonte e página. Zoom, Buscapé,
KaBuM!, Americanas, Carrefour e Samsung Shop ficam cadastrados uma única vez
pelas respectivas raízes; a API
exige o aparelho, o worker resolve o catálogo e cada spider pesquisa as
capacidades dentro da fonte antes de seguir páginas exatas do mesmo host. URLs
específicas passam a ser evidência da execução. No caso focal iPhone 17 Pro Max,
as execuções de Zoom/Buscapé/KaBuM!/Americanas/Carrefour registraram
`25/49/11/6/3` observações brutas e a leitura atual chegou a `12/12`
configurações, `54` ofertas deduplicadas e `17` varejistas. Samsung Shop também
concluiu com `6` observações para o Galaxy S26 Ultra. O registro governado mapeia
33 fontes; cinco fontes de mercado ficam ativas. Carrefour voltou a candidato
após a revalidação do iPhone 16 registrar três recusas por `robots.txt` na rota
`/busca/`; o histórico permanece auditável, sem justificar novas execuções. As
demais exibem seu estado de qualificação. A UX troca a lista plana por
armazenamento e cor em duas etapas,
substitui a recomendação enganosa por custo/GB pela escada incremental de preço
e acompanha a coleta com progresso vivo. Uma fonte vazia não invalida os
resultados das demais;
512 GB, 1 TB e
2 TB foram exercitados em browser, sem erro de página, overflow mobile ou
violação WCAG automatizada. A diversidade exata ainda varia de `3` a `11`
varejistas e a revisão independente permanece como gate externo.

O `INC-11` reverte parcialmente o `INC-07B` por decisão de negócio explícita
(`docs/ai/decisions/0001-browser-realistic-http-profile.md`): o perfil HTTP
passa a negociar como um Chrome/Windows atual (User-Agent, Client Hints,
Sec-Fetch-*) e um novo `RetryAfterMiddleware` respeita `Retry-After` em HTTP
429 antes do retry. `robots.txt`, a ausência de escalada de bloqueio para o
fallback de navegador, e a ausência de CAPTCHA/fingerprint TLS/rotação de
proxy permanecem inalterados — decisão explícita, não descuido. Efeito
esperado é limitado às fontes bloqueadas por sniffing simples de headers;
fontes bloqueadas por `robots.txt` ou WAF com fingerprint TLS/comportamental
não mudam de estado só com esta entrega. Revisão funcional e de segurança
independentes (agentes `reviewer`/`security-reviewer` neste runtime, capaz
de delegar revisão diferente do runtime Codex do `INC-06`/`INC-07B`)
descartaram um falso positivo (sintaxe reportada como inválida por ambos os
agentes sem `Bash`; confirmada válida no Python 3.14.7 real via `compile()`
com controle negativo) e confirmaram as quatro exclusões da ADR íntegras no
código. Corrigiram teto agregado ausente em `Retry-After`
(`CLOSESPIDER_TIMEOUT`), mismatch de fingerprint UA/`Sec-CH-UA` no fallback
Playwright, parsing de dígito Unicode não-ASCII e uma lacuna de defesa em
profundidade em quatro métodos de spider. Runtime local final: `uv run
pytest` 171 passados e 2 integrações puladas sem `API_BASE_URL`; `ruff
check`, `ruff format --check` e `ty check` verdes. `PR #10` publicado,
checks remotos (`governance`, GitGuardian) verdes, sem review obrigatória
pendente, `mergeStateStatus=CLEAN`; squash-merge no SHA `f094500` com o head
relido imediatamente antes da decisão. `main` local sincronizada via
`.codex/safe_git_sync.py sync-main`.

O `INC-12` investigou ampliação de cobertura usando o perfil do `INC-11`.
Casas Bahia, Ponto e Extra (mesma plataforma Next.js) têm página de categoria
acessível, mas `initialState.price` chega `{"loading": true, "prices": []}`
no próprio HTML — preço é deliberadamente carregado por cliente atrás de
telemetria comportamental Akamai ativa (capturada em tráfego de rede real).
Um teste controlado confirmou: o Playwright já existente, sem nenhuma
modificação, recebe HTTP 403 imediato nesses hosts, com `navigator.webdriver`
como o sinal — contornar isso exigiria mascarar essa flag, evasão de WAF
nomeada, fora de escopo. Magalu tem o mesmo padrão confirmado com URL real de
produto. TerabyteShop e Pichau são tecnicamente acessíveis mas não vendem os
aparelhos do catálogo (varejistas de hardware/PC). Essas cinco fontes
permanecem `candidate` sem novo trabalho de adapter — evidência em
`docs/source-qualification.md` e na investigação desta sessão.

iPlace, em contraste, não bloqueia automação: o mesmo Playwright sem
modificação carrega a página de produto normalmente e expõe `Product`
JSON-LD idêntico ao que `extract_iplace_listings` (inalterado) já espera — a
plataforma migrou para Oracle Commerce Cloud e passou a renderizar no
cliente, então HTTP puro nunca mais será suficiente. `IPlaceSpider` passa a
usar o fallback de navegador já existente como caminho normal (mesmo
invariante de Amazon/Carrefour: só escala após HTTP permitido e insuficiente,
nunca em bloqueio), com allowlist restrita a `www.iplace.com.br` (testada sem
nenhum host de terceiros liberado). A resolução de URL usa um mapa
model→slug verificado contra `productSitemap.xml`, não busca — `/searchresults/`
é proibido no `robots.txt` do iPlace. Seis modelos verificados (iPhone 16
Plus/Pro/Pro Max, 17 Pro/Pro Max, Air); iPhone 16/17 base e 18 Pro/Pro Max
ainda sem página confirmada nesse sitemap. Runtime local: `uv run pytest`
179 passados (8 novos), `ruff check`, `ruff format --check` e `ty check`
verdes. Revisão funcional e de segurança independentes aprovaram localmente,
sem achado bloqueante/alto/médio; três achados baixos corrigidos no mesmo
commit (guarda de status em `parse_browser_product`, asserção da allowlist
restrita, precisão no relato dos experimentos contra Casas Bahia). `PR #12`
publicado e mesclado (squash, `20a8e74`), checks remotos verdes, head relido
imediatamente antes da decisão. Aguarda execução real pelo pipeline completo
para promoção do iPlace a `enabled`.

Fora do escopo do INC-12: uma tentativa de validar iPlace de verdade pelo
pipeline completo (worker Docker) falhou duas vezes consecutivas — todas as
requisições receberam `DownloadTimeoutError` de 15s. Diagnóstico isolou uma
incompatibilidade de rede entre o cliente Twisted do Scrapy e o edge Akamai
do iPlace especificamente de dentro da rede Docker deste ambiente (o mesmo
container coleta Zoom normalmente, e `urllib` puro do Python no mesmo
container alcança o iPlace instantaneamente). Revertido para `candidate`
(PR #14) — sem observação real, sem promoção, mantendo a política do
projeto.

O `INC-13` usou a stack local rodando de verdade para investigar diversidade
de capacidade/cor nas fontes habilitadas. Achado: `MAX_SEARCH_RESULTS_PER_
CAPACITY = 3` (`collection/real_sources.py`) truncava a busca de produto a 3
cores por capacidade — mas 15 dos 18 aparelhos do catálogo têm mais de 3
cores (Galaxy S26 tem 6). Elevado para 8 (máximo real do catálogo é 6, +2 de
margem), com `CLOSESPIDER_PAGECOUNT` reajustado em Zoom/Buscapé/KaBuM!/
Bondfaro/Americanas para acomodar o novo teto. Validado com execução real:
Galaxy S26 Ultra, nunca antes coletado nesta stack, passou a mostrar as 6
cores reais numa única fonte (Zoom) logo na primeira coleta pós-correção;
consolidado final com 4 fontes chegou a 61% de cobertura de variantes, 25
ofertas e 11 varejistas. Runtime local: `uv run pytest` 180 passados (1
novo), `ruff check`, `ruff format --check` e `ty check` verdes.

O reviewer independente aprovou localmente o ciclo 2 do INC-05 no fingerprint
`fadb3ec6d99b17b80386d1296655a3ef65be8f3523e59bd2760133dcb64d0b75`, sem
achados remanescentes. Permanecem os riscos documentados de mudança externa de
markup/oferta, DNS TOCTOU e tags mutáveis das imagens-base.

A revisão local funcional e de segurança do INC-06 corrigiu escopo de preço,
identidade duplicada de seller, resposta HTTP não textual, pré-validação DNS e
origem da dependência Playwright. O runtime desta tarefa proíbe delegar um novo
revisor; portanto esse parecer não é registrado como independente e o merge
permanece sob gate externo.

## Estados normativos

`WAITING` → `READY` → `IN_PROGRESS` → `IN_REVIEW` → `VERIFIED`

- `REOPENED`: regressão ou evidência inválida reabre unidade verificada.
- `STALE`: evidência depende de unidade reaberta e precisa ser revalidada.
- `BLOCKED_EXTERNAL`: acesso, decisão ou sistema fora do workspace impede aceite.
- `BLOCKED_TECHNICAL`: pré-requisito local falhou após alternativas seguras.
- `LOCAL_VERIFIED_WITH_EXTERNAL_GATE`: resumo de marco localmente verde com gate
  externo ainda pendente; não equivale a aprovação externa.

Existência de arquivo ou exit code zero não basta para `VERIFIED`. Registre em
`evidence/` critérios, baseline/commit, comandos, revisão independente, riscos e
rollback. Um bloqueio afeta somente unidades que dependem dele.

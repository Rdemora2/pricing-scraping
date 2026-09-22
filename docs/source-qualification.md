# Matriz de homologação de fontes

Snapshot local de `2026-09-22`. Esta matriz registra o resultado observável do
fluxo completo — acesso, descoberta, extração, persistência e readback — e não
promete disponibilidade futura de terceiros. Uma fonte só fica `enabled` quando
produz observações reais sem autenticação, CAPTCHA ou contorno de política.

| Fonte | Estado | Evidência ou impedimento atual |
|---|---|---|
| Amazon Brasil | candidate | Adapter e busca cobertos; execução final recebeu HTTP 503 e produziu zero observações. |
| Americanas | enabled | Run `1df5115e-f6d4-4ae2-8f28-67cd410a0868`: 6 observações e 6 evidências. |
| Carrefour | candidate | Run `3e0388a3-1a1f-4839-baad-ce84f104d670`: a busca do iPhone 16 foi recusada três vezes por `robots.txt`; a política atual proíbe `/busca/`. Rota alternativa por sitemap avaliada e descartada com medição (INC-14): o `robots.txt` publica `Sitemap: https://www.carrefour.com.br/sitemap.xml` e o índice responde 200, mas traz 5305 documentos, dos quais 5290 são `product-N.xml` com 1000 URLs cada — cerca de 5,29 milhões de URLs sem ordenação por marca ou categoria, e o marcador real de produto é `/p`, não `/produto/`. Localizar um aparelho exigiria varredura de milhões de URLs. Próxima rota candidata: navegação por categoria, que o `robots.txt` não proíbe, ainda sem homologação. |
| iPlace | candidate | Perfil realista de headers (INC-11) removeu o HTTP 403 anterior visto de fora do Docker; código de extração (INC-12) verificado correto contra páginas reais buscadas do host. Execução real pelo pipeline completo (worker/Postgres) tentada duas vezes: todas as 8 requisições (robots.txt + página de produto) deram `DownloadTimeoutError` de 15s em ambas as tentativas — falha consistente, não passageira. Diagnóstico isolou a causa a uma incompatibilidade de rede entre o cliente Twisted do Scrapy e o edge Akamai do iPlace especificamente de dentro da rede Docker deste ambiente: o mesmo container alcança o Zoom (atrás de CloudFront) normalmente, e `urllib`/`ssl` puro do Python no mesmo container alcança o iPlace instantaneamente — não é bloqueio nem código, é a pilha de rede Twisted/Docker/Akamai específica. Sem observação real produzida; sem promoção a `enabled`. |
| Fast Shop | candidate | Produto estruturado validado, mas `robots.txt` não autoriza a busca automatizada. |
| Zoom | enabled | Run `c7461e5f-9f78-422b-bde8-e194ff2f6d23`: 25 observações. |
| Buscapé | enabled | Run `42ba3f21-f4bb-4984-8854-1103ec6aa5fa`: 49 observações. |
| Samsung Shop | enabled | Run `605b782f-966f-4777-a7c9-588e2c847e09`: 6 observações e 6 evidências. |
| 2aFinder | candidate | Busca pública não discriminou de forma estável o modelo solicitado. |
| KaBuM! | enabled | Run `315b10cc-e684-41b5-a0a2-5325bb7ddd81`: 11 observações e 11 evidências. |
| Loja Aurora (lab) | enabled | Fonte sintética isolada; não entra na leitura de mercado. |
| Mercado Boreal (lab) | enabled | Fonte sintética isolada; não entra na leitura de mercado. |
| Apple Brasil | reference | Referência oficial de catálogo; não é tratada como cotação automatizada. |
| Samsung Brasil | reference | Referência institucional; a cotação vem da Samsung Shop. |
| Motorola Brasil | reference | Referência oficial; busca ainda sem oferta exata estável para o catálogo focal. |
| Mercado Livre | candidate | Integração oficial não credenciada; endpoint público respondeu HTTP 403. |
| Casas Bahia | candidate | Categoria abre (200) com o perfil do INC-11; página de produto individual recusada (403) mesmo com SKU e URL reais. `robots.txt` proíbe `*/pdp-api`. `initialState.price` da própria categoria chega `{"loading": true, "prices": []}` — preço é carregado por cliente atrás de telemetria comportamental Akamai ativa (confirmada em tráfego de rede real). Playwright de produção sem nenhuma modificação recebe 403 imediato ali, com `navigator.webdriver` como sinal; contornar exigiria mascarar essa flag, fora de escopo. Ver `docs/ai/delivery/evidence/INC-12.md`. |
| Ponto | candidate | Mesma plataforma e mesmo impedimento da Casas Bahia (confirmado com SKU e URL reais próprios). |
| Extra | candidate | Mesma plataforma e mesmo impedimento da Casas Bahia. |
| Shopee Brasil | candidate | Falta validar no fluxo público produto novo, seller, garantia e estoque nacional. |
| AliExpress Brasil | candidate | Falta provar em conjunto envio do Brasil, produto novo, seller e garantia. |
| Pichau | candidate | Tecnicamente acessível com o perfil do INC-11, mas é varejista de hardware/PC gamer — não vende os aparelhos do catálogo. `robots.txt` também proíbe busca por query (`Disallow: /*?*`). |
| TerabyteShop | candidate | O mais aberto tecnicamente (`robots.txt` permite `/produto/`, `/smartphones/`, regras dedicadas para bots de IA); sitemap de produtos (3957 URLs) não contém iPhone/Galaxy como produto — só acessórios. Varejista de hardware/PC, não vende os aparelhos do catálogo. |
| Xiaomi Brasil | reference | Referência oficial mapeada para expansão futura do catálogo. |
| Realme Brasil | reference | Referência oficial mapeada para expansão futura do catálogo. |
| Claro Loja Online | candidate | Rota de busca não homologada; preço precisa ser separado de plano e fidelização. |
| Vivo Loja Online | candidate | HTTP 403; preço condicionado não pode virar preço-base. |
| TIM Loja Online | candidate | Probe excedeu o timeout; preço condicionado ainda sem contrato verificável. |
| JáCotei | candidate | HTTP 403 no acesso declarado. |
| Bondfaro | candidate | Adapter validado, mas o `robots.txt` recusou a execução da busca. |
| Promobit | candidate | Rota pública não homologada; cupom e validade exigem semântica própria. |
| Pelando | candidate | Rota pública não homologada; cupom e validade exigem semântica própria. |
| Magalu | candidate | Raiz abre (200); URL real de busca por produto (obtida navegando o site) recusada com HTTP 403 — página de erro com a marca "akamai-bot" própria da Magalu. Não é chute de URL errado: confirmado com URL real. |

Fontes candidatas continuam visíveis para governança, mas não oferecem botão de
coleta. Mudança de estado exige novo run completo e evidência persistida; uma
resposta HTTP 200 isolada ou um parser de fixture não basta para habilitação.

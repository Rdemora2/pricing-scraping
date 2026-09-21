# Matriz de homologação de fontes

Snapshot local de `2026-09-21`. Esta matriz registra o resultado observável do
fluxo completo — acesso, descoberta, extração, persistência e readback — e não
promete disponibilidade futura de terceiros. Uma fonte só fica `enabled` quando
produz observações reais sem autenticação, CAPTCHA ou contorno de política.

| Fonte | Estado | Evidência ou impedimento atual |
|---|---|---|
| Amazon Brasil | candidate | Adapter e busca cobertos; execução final recebeu HTTP 503 e produziu zero observações. |
| Americanas | enabled | Run `1df5115e-f6d4-4ae2-8f28-67cd410a0868`: 6 observações e 6 evidências. |
| Carrefour | candidate | Run `3e0388a3-1a1f-4839-baad-ce84f104d670`: a busca do iPhone 16 foi recusada três vezes por `robots.txt`; a política atual proíbe `/busca/`. Runs históricos permanecem auditáveis, mas não justificam nova execução. |
| iPlace | candidate | HTTP 403 no acesso declarado. |
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
| Casas Bahia | candidate | HTTP 403 no acesso declarado. |
| Ponto | candidate | HTTP 403 no acesso declarado. |
| Extra | candidate | HTTP 403 no acesso declarado. |
| Shopee Brasil | candidate | Falta validar no fluxo público produto novo, seller, garantia e estoque nacional. |
| AliExpress Brasil | candidate | Falta provar em conjunto envio do Brasil, produto novo, seller e garantia. |
| Pichau | candidate | HTTP 403 no acesso declarado. |
| TerabyteShop | candidate | HTTP 403 no acesso declarado. |
| Xiaomi Brasil | reference | Referência oficial mapeada para expansão futura do catálogo. |
| Realme Brasil | reference | Referência oficial mapeada para expansão futura do catálogo. |
| Claro Loja Online | candidate | Rota de busca não homologada; preço precisa ser separado de plano e fidelização. |
| Vivo Loja Online | candidate | HTTP 403; preço condicionado não pode virar preço-base. |
| TIM Loja Online | candidate | Probe excedeu o timeout; preço condicionado ainda sem contrato verificável. |
| JáCotei | candidate | HTTP 403 no acesso declarado. |
| Bondfaro | candidate | Adapter validado, mas o `robots.txt` recusou a execução da busca. |
| Promobit | candidate | Rota pública não homologada; cupom e validade exigem semântica própria. |
| Pelando | candidate | Rota pública não homologada; cupom e validade exigem semântica própria. |
| Magalu | candidate | HTTP 403 no acesso declarado. |

Fontes candidatas continuam visíveis para governança, mas não oferecem botão de
coleta. Mudança de estado exige novo run completo e evidência persistida; uma
resposta HTTP 200 isolada ou um parser de fixture não basta para habilitação.

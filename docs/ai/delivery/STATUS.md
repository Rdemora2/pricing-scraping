# Estado de execução

**Atualizado em:** `2026-09-20`
**Estado global:** `LOCAL_VERIFIED_WITH_EXTERNAL_GATE`
**Unidade ativa:** `INC-08` — auditoria e endurecimento em andamento

O roadmap conclui o laboratório e avança o portal local de inteligência de
preços com fontes reais. A entrega permanece limitada ao ambiente local; não
inclui deploy ou cloud.

Código, 85 testes, análise estática, pacote, imagens, coleta real, Chromium no
worker e browser desktop/mobile estão verdes. API, worker e frontend foram
reconstruídos; smokes one-shot provaram o runtime headless e a coleta Amazon com
proveniência de fallback.

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
primeiro cada variante exata e depois agrega cobertura, faixa, custo por GB e
diferenças de cor normalizadas por armazenamento. Recomendações permanecem
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

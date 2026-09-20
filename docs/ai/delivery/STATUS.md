# Estado de execução

**Atualizado em:** `2026-09-20`
**Estado global:** `LOCAL_VERIFIED_WITH_EXTERNAL_GATE`
**Unidade ativa:** `—`

O roadmap conclui o laboratório e avança o portal local de inteligência de
preços com fontes reais. A entrega permanece limitada ao ambiente local; não
inclui deploy ou cloud.

Código, 60 testes, análise estática, imagens, migração, coleta real e browser
desktop/mobile estão verdes. A stack Compose preexistente foi observada saudável;
as imagens novas foram validadas por build e containers one-shot porque a política
local não permitiu recriar todo o conjunto.

O `INC-04` inclui 76 variantes Apple/Samsung, Fast Shop, Samsung Shop, KaBuM! e
Zoom, descoberta ampla governada e portal completo. O `INC-05` adiciona 2aFinder
e Buscapé, separa URL comercial de evidência e mede `9/11/9/5/6/6` varejistas nas
variantes prioritárias. Cinco famílias atingem o piso; o Galaxy S26 Dourado
permanece sob gate externo exato de oferta. O laboratório continua isolado das
métricas reais.

O reviewer independente aprovou localmente o ciclo 2 do INC-05 no fingerprint
`fadb3ec6d99b17b80386d1296655a3ef65be8f3523e59bd2760133dcb64d0b75`, sem
achados remanescentes. Permanecem os riscos documentados de mudança externa de
markup/oferta, DNS TOCTOU e tags mutáveis das imagens-base.

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

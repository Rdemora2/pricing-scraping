# INC-08 — auditoria integral e endurecimento

## Escopo e aceite

- Branch: `feature/inc-08-quality-hardening`.
- Objetivo: revisar requisitos, código, arquitetura, containers, documentação e
  frontend como uma entrega única, sem confundir checks locais com cobertura real.
- Aceite: achados corrigidos em commits atômicos; suíte, análise estática, build,
  migração limpa, Compose e navegador desktop/mobile verdes; limites externos
  declarados sem dados fictícios.

## Achados da primeira revisão

1. `Money`, JSON-LD genérico e alguns adapters aceitavam preço zero, apesar do
   contrato documentar preço estritamente positivo.
2. O estágio final do Dockerfile era o runtime com Chromium; API, migração e
   laboratório não fixavam o estágio enxuto declarado na arquitetura.
3. A imagem de produção não contém testes ou `pytest`, tornando o comando de
   integração em container não reproduzível.
4. O catálogo não cobria todas as famílias oficiais solicitadas e exigia
   centralização antes de crescer com rastreabilidade.
5. A documentação ainda continha estado antigo de branch e descrevia a opção de
   API comercial como se já houvesse um conector credenciado.

## Correções entregues

- regressões para preço zero falharam antes do patch;
- validação estritamente positiva aplicada em domínio, extratores e banco;
- testes direcionados de dinheiro, JSON-LD e fontes reais: `45 passed`;
- Ruff e `ty` verdes no primeiro ciclo.
- os estágios `runtime`, `browser-runtime` e `test-runtime` ficaram explícitos;
- imagens locais: API/laboratório com aproximadamente 153 MB e worker com
  Chromium com aproximadamente 638 MB;
- o primeiro smoke do serviço de teste revelou `pytest` fora do `PATH` e os
  arquivos de contrato ausentes; ambos foram corrigidos e revalidados;
- Compose isolado `pricing-intel-inc08`: migração limpa, API saudável,
  `2 passed` de integração e `97 passed` unitários executados dentro do
  container dedicado.
- catálogo extraído do script para classes imutáveis em
  `pricing_intel.catalog`, com 17 aparelhos, 221 variantes de mercado, três
  variantes de laboratório e URL oficial por família;
- linhas iPhone 16/17/18 Pro e Air, Galaxy S25/S26 e Motorola Edge 70 Pro
  cadastradas sem produzir preços fictícios para aparelhos sem adapter;
- inteligência limitada, por padrão, às últimas 72 horas; evidência anterior
  continua preservada e é excluída com motivo explícito;
- painel de inteligência extraído do `App.tsx`; aparelhos sem coletor mostram
  estado vazio honesto e não oferecem uma atualização sem efeito;
- contraste dos rótulos de catálogo e cartões claros corrigido após falha real
  do auditor de acessibilidade.

## Snapshot consolidado

- `uv run ruff check .`: verde;
- `uv run ruff format --check .`: 123 arquivos formatados;
- `uv run ty check .`: verde;
- `uv run pytest --cov=pricing_intel`: 102 passaram, 2 integrações foram
  corretamente ignoradas fora do Compose, cobertura global de 72%;
- `uv build`: sdist e wheel construídos;
- `npm run check && npm run build`: Biome, TypeScript e Vite verdes;
- gates oficiais `full`: `test_fast`, `lint`, `typecheck` e `build` verdes;
- `docker compose --profile test build`: API, migração, worker, laboratório,
  frontend e runtime de testes construídos;
- stack isolada em banco limpo: 18 produtos, 17 de mercado, 224 variantes totais,
  todos os serviços saudáveis e `2 passed` de integração dentro do container;
- navegador desktop `1440x1000` e mobile `390x844`: landing, navegação, catálogo,
  fontes aplicáveis e estados vazios renderizados, sem overlay, erro de página ou
  overflow horizontal;
- axe-core WCAG A/AA: zero violações; a única verificação inconclusiva decorre do
  fundo em gradiente e foi inspecionada visualmente;
- revisão local de segurança: nenhum segredo, nova dependência, relaxamento de
  allowlist, origem/host, privilégio ou isolamento; somente o worker carrega
  Chromium.

## Parecer local

`APROVAR_LOCALMENTE`. Os achados funcionais, arquiteturais, de documentação e
acessibilidade encontrados nesta auditoria foram corrigidos. Este parecer não é
independente; a revisão independente obrigatória permanece como gate externo
antes de merge.

## Entrega remota

- Branch publicada: `feature/inc-08-quality-hardening`;
- PR draft: `#8`, empilhado sobre `feature/inc-07b-transparent-http-profile`;
- checks observados no head publicado: `governance` e
  `GitGuardian Security Checks`, ambos verdes;
- PR permanece draft e sem merge porque não há revisão independente aprovada.

## Segurança e rollback

- Não há segredo, produção ou nova dependência.
- URLs/HTML continuam não confiáveis e delimitados pelas políticas existentes.
- Cada commit é reversível de forma independente; a migração de preço possui
  downgrade para a restrição anterior.
- Os stacks e volumes temporários `pricing-intel-inc08*` foram removidos após a
  prova; nenhum volume do projeto original foi alterado.

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

## Evidência em andamento

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

## Segurança e rollback

- Não há segredo, produção ou nova dependência.
- URLs/HTML continuam não confiáveis e delimitados pelas políticas existentes.
- Cada commit é reversível de forma independente; a migração de preço possui
  downgrade para a restrição anterior.

# INC-07A — inteligência consolidada por aparelho

## Escopo e aceite

- Branch: `feature/inc-07a-product-intelligence`.
- Objetivo: transformar comparações exatas de variante em uma leitura executiva
  de armazenamento, cor, cobertura e custo por GB.
- Aceite: contrato `GET /products/{id}/intelligence`, interface responsiva,
  ausência explícita de recomendação com dados insuficientes e checks aplicáveis
  verdes.

## Invariantes

- uma cor só é comparada com outras cores do mesmo armazenamento;
- o preço de armazenamento é a mediana das variantes observadas;
- custo-benefício significa menor preço representativo por GB;
- ofertas condicionais, indisponíveis, usadas ou duplicadas continuam excluídas
  antes da agregação;
- nenhuma recomendação é fabricada quando faltam alternativas comparáveis.

## Evidência local

- `uv run pytest -q`: `91 passed`;
- `uv run ruff check .` e `uv run ty check .`: verdes;
- `npm run check` e `npm run build`: Biome, TypeScript e Vite verdes;
- `python3 .codex/execution_control.py gates --run --level full --task-id INC-07A`:
  testes rápidos, lint, typecheck e build verdes;
- `docker compose build`: imagens de frontend, API, worker, migração e
  laboratório construídas;
- stack Compose isolada em `127.0.0.1:3001/8001`: migração, seed, Nginx, health,
  OpenAPI e contrato de inteligência exercitados;
- navegador real desktop e mobile: iPhone 17 Pro exibiu capacidades e cores do
  catálogo, sem erro de console ou overflow horizontal;
- revisão local funcional e de segurança: sem achados remanescentes. A consulta
  é parametrizada por UUID, não adiciona egress ou segredo e reutiliza os
  filtros de comparabilidade existentes.

O comando documentado `docker compose run --rm api pytest tests/unit` não é
executável na imagem de produção, que intencionalmente não inclui `pytest` nem a
pasta de testes. A suíte equivalente foi executada no ambiente `uv`; o runtime da
aplicação foi validado separadamente no Compose.

O runtime desta tarefa não permite delegar um revisor independente. Por isso a
unidade permanece `LOCAL_VERIFIED_WITH_EXTERNAL_GATE`, sem fabricar recibo de
aprovação externa.

## Riscos e rollback

- A cobertura real continua dependente de cada variante coletada; a UX expõe a
  razão observada/catálogo.
- O índice de cor é descritivo e não infere preferência ou demanda.
- A consulta foi comprovada ao vivo em banco limpo; o caso populado é coberto por
  testes de domínio e contrato, não por uma coleta externa reproduzível nesta
  unidade.
- Rollback: remover rota, módulo de inteligência e painel; nenhuma migração ou
  transformação de dados foi introduzida.

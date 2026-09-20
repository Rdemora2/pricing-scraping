# Evidência INC-05 — piso de cobertura real

- Data: `2026-09-20`
- Git root: `.`
- Branch: `feature/inc-05-coverage-floor`
- Baseline: `53ed401caedb6ffe5ba1791c1c160848de705502`
- Cápsula: `.codex/sessions/inc-05/TASK_CONTEXT.md`
- Estado: `LOCAL_VERIFIED_WITH_EXTERNAL_GATE`
- Risco: médio

## Aceite demonstrado

- Novos adaptadores de coleta pública para 2aFinder Markdown e Buscapé, com
  allowlist exata, robots, limites globais já existentes e no máximo 20 ofertas.
- Nenhum lead, afiliado, CAPTCHA, login ou controle de acesso é seguido ou
  contornado.
- Só entram na comparação ofertas novas, BRL, sem condição comercial e com
  disponibilidade explicitamente confirmada. `stock` ausente no Buscapé vira
  `unknown`; uma página 2aFinder sem a declaração de “ofertas ativas” falha.
- O link comercial e a URL do documento realmente extraído são persistidos em
  campos distintos. O hash/excerpt corresponde à URL de evidência.
- Aliases e repetição entre canal direto e agregador contam uma única vez.

## Coleta real reproduzida

As 12 fontes novas concluíram com sucesso no worker local:

| Fonte | Runs | Ofertas observadas |
| --- | --- | ---: |
| 2aFinder — iPhone 17 / Pro / Pro Max | `fca849a9`, `3929aa08`, `e7ceb90c` | `10 / 10 / 10` |
| 2aFinder — Galaxy S26 / S26+ / Ultra | `d14a59d7`, `06cf842c`, `66b2b753` | `9 / 10 / 9` |
| Buscapé — iPhone 17 / Pro / Pro Max | `e1e67b47`, `bfe9ad2d`, `7d5aadbd` | `20 / 15 / 15` |
| Buscapé — Galaxy S26 / S26+ / Ultra | `7f313d51`, `8983f6c9`, `a5aefd83` | `1 / 3 / 7` |

Matriz após matching exato, disponibilidade, condição, aliases e deduplicação:

| Aparelho | Variante prioritária | Varejistas | Canais | Incluídas | Excluídas |
| --- | --- | ---: | ---: | ---: | ---: |
| iPhone 17 | 256 GB Lavanda | 9 | 1 | 9 | 2 |
| iPhone 17 Pro | 256 GB Prateado | 11 | 3 | 11 | 6 |
| iPhone 17 Pro Max | 1 TB Prateado | 9 | 1 | 9 | 1 |
| Galaxy S26 | 256 GB Dourado | 5 | 2 | 5 | 5 |
| Galaxy S26+ | 512 GB Violeta | 6 | 1 | 6 | 4 |
| Galaxy S26 Ultra | 1 TB Preto | 6 | 1 | 6 | 3 |

A consulta de rastreabilidade confirmou, em observações Buscapé recentes, a URL
comercial `www.buscape.com.br/...` no anúncio e a URL efetivamente extraída
`api-v1.zoom.com.br/sale-condition/...` na evidência persistida.

## Gate externo específico — Galaxy S26

Cinco das seis famílias atingem o piso. O Galaxy S26 256 GB Dourado fica em
cinco vendedores novos e disponíveis depois de consolidar Samsung Shop,
`SAMSUNGLOJAOFICIAL` e o nome societário da Samsung. Isso não é arredondado para
sucesso.

O bloqueio é oferta externa da variante exata na data da coleta:

- a Samsung declara Dourado e Prata como cores exclusivas da loja oficial:
  <https://news.samsung.com/br/samsung-anuncia-galaxy-s26-o-galaxy-ai-phone-mais-intuitivo>;
- o documento público exato coletado é
  <https://2afinder.com/produto/galaxy-s-galaxy-s26-2026-985394.md>;
- a coleta observou nove linhas, mas somente cinco identidades permaneceram
  comparáveis após excluir condição desconhecida e aliases do mesmo varejista.

Fechar o sexto valor exige que outro vendedor publique essa mesma variante como
nova e disponível, ou que uma nova fonte direta revisável passe a expô-la. Nem
misturar cor/armazenamento nem contar a Samsung duas vezes é aceitável.

## Gates locais

- `uv run ruff check .`: verde.
- `uv run ruff format --check .`: `107` arquivos formatados.
- `uv run ty check .`: verde.
- `uv run pytest`: `73` testes passaram.
- `npm run check && npm run build`: verde; JS `218,61 kB` (`67,88 kB`
  gzip) e CSS `21,64 kB` (`5,40 kB` gzip).
- `POSTGRES_PASSWORD=ci-local-placeholder docker compose config --quiet`: verde.
- `docker compose build api worker frontend`: três imagens construídas.
- Browser real em `1440 x 1000` e `390 x 844`: landing/workspace sem erros,
  `scrollWidth = innerWidth`; iPhone 17 abriu com 9 ofertas e Galaxy S26+ com
  6 ofertas na variante prioritária 512 GB Violeta.
- Screenshots locais: `/tmp/inc05-final-home.png`,
  `/tmp/inc05-final-desktop.png` e `/tmp/inc05-final-mobile.png`.

## Revisão, riscos e rollback

O primeiro ciclo independente bloqueou disponibilidade não confirmada,
rastreabilidade do Buscapé e ausência de evidência do bloqueio externo. Os três
itens foram corrigidos. O ciclo 2 resultou em `APROVAR_LOCALMENTE`, sem achados
remanescentes, no fingerprint
`fadb3ec6d99b17b80386d1296655a3ef65be8f3523e59bd2760133dcb64d0b75`.

Riscos residuais: fontes externas podem mudar markup, disponibilidade e oferta;
por isso falham de forma fechada, guardam evidência e não prometem cobertura
permanente. A quantidade de canais é exibida separadamente da quantidade de
varejistas.

Rollback: retornar ao commit anterior e reconstruir API/worker/frontend. Não há
migração de schema; o histórico de coletas pode ser preservado. Em instalações
já semeadas, o seed desabilita a URL anterior de uma fonte de mesmo nome antes
de habilitar o alvo revisado.

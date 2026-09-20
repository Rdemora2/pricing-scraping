# Evidência INC-02 — dashboard React

- Data: `2026-09-20`
- Git root: `.`
- Branch: `feature/increment-1-lab-pipeline`
- Head revisado: `876955a`
- Cápsula: `.codex/sessions/inc-02/TASK_CONTEXT.md`
- Fingerprint: `4bc1833ef5dea2441a363b9f76ad16270e87fbc5c08c6befa8a3d485b1441f8d`
- Estado: `LOCAL_VERIFIED_WITH_EXTERNAL_GATE`
- Risco: médio

## Aceite e evidência

- React/Vite consome somente dados reais da API e representa loading, erro,
  ausência de dados, coletas em andamento, ofertas incluídas e exclusões.
- Nginx serve o bundle e encaminha a API same-origin.
- Layout validado em `1280 px` e `390 x 844`; no mobile, `scrollWidth` e viewport
  permaneceram em `390 px`.
- Browser sem erros de console; ação **Atualizar mercado** iniciou as duas coletas,
  acompanhou os runs e atualizou a comparação.
- Evidências visuais: `signal-price-desktop.png` e `signal-price-mobile.png` no
  diretório de visualizações desta execução.

## Build e segurança

- Build Docker executou Biome, TypeScript e Vite com sucesso.
- Bundle: JavaScript `202.84 kB` (`63.87 kB` gzip) e CSS `11.14 kB`
  (`3.37 kB` gzip).
- Lockfile, `npm ci`, imagens por digest e `.dockerignore` tornam o build delimitado
  e reproduzível.
- Nginx rejeita hosts desconhecidos; API valida `Host` e `Origin` para o POST.
- CSP não exige `unsafe-inline`; o marcador variável usa atributos SVG.

## Revisões e gate pendente

- Security reviewer: `APROVAR_LOCALMENTE`; sem achados médios/altos. Residual baixo:
  runtime Nginx sem hardening adicional de filesystem/capabilities.
- Reviewer: nenhum achado funcional, de acessibilidade ou de segurança; decisão
  `BLOQUEAR` exclusivamente por falta do smoke do Nginx dentro do Compose.
- Recibos foram validados por `.codex/review_result.py` no fingerprint acima.

Gate externo: executar `docker compose up --build`, verificar `/`, proxy
`/products`, coleta, comparação e observar CSP, `X-Frame-Options`, `nosniff` e
`Referrer-Policy` nas respostas reais.

Rollback: reverter `add21d3` e `876955a`, reconstruir a imagem frontend e preservar
o volume PostgreSQL.

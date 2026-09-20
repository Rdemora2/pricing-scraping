# INC-07B — perfil HTTP transparente

## Escopo e aceite

- Branch: `feature/inc-07b-transparent-http-profile`.
- Objetivo: negociar a representação apropriada para páginas comerciais sem
  fingir identidade humana ou ocultar que o cliente é automatizado.
- Aceite: headers explícitos, Amazon herdando o perfil comum, teste de regressão
  e documentação do limite de segurança.

## Invariantes

- o user-agent continua contendo a identidade `bot` do laboratório;
- `Accept` solicita HTML/XML, `Accept-Language` prioriza português do Brasil e
  `Cache-Control` força revalidação;
- o perfil não envia `Sec-CH-UA`, cookie de usuário ou user-agent de Chrome;
- HTTP 401/403/429, `robots.txt` e CAPTCHA continuam estados explícitos, sem
  escalada automática para browser.

## Evidência local

- o teste novo falhou antes do patch por ausência do perfil e pelo override da
  Amazon, confirmando que cobre a mudança observável.
- `uv run pytest tests/unit/test_request_profile.py tests/unit/test_browser_fallback.py -q`:
  `9 passed`;
- `uv run pytest -q`: `93 passed`;
- `uv run ruff check .` e `uv run ty check .`: verdes;
- `python3 .codex/execution_control.py gates --run --level full --task-id INC-07B`:
  testes rápidos, lint, typecheck e build verdes;
- revisão local funcional e de segurança: sem achados remanescentes, sem nova
  dependência, egress, cookie, segredo ou fallback em resposta de bloqueio.

O runtime desta tarefa não permite delegar um revisor independente. Por isso a
unidade permanece `LOCAL_VERIFIED_WITH_EXTERNAL_GATE`, sem fabricar recibo de
aprovação externa.

## Riscos e rollback

- lojas podem variar conteúdo por idioma; a preferência é explícita e estável.
- Rollback: remover os três headers e restaurar o override da Amazon; não há
  migração, dependência ou dado persistido.

# Gates de qualidade

Selecione e execute os comandos por `.codex/execution_control.py gates`; o
manifesto elimina `TODO` e comandos duplicados, começa pelo menor gate falsificador
e amplia conforme risco. A matriz abaixo continua sendo o critério de suficiência.

## Toda unidade

- aceite rastreado para teste ou evidência observável;
- validação de erros, limites e repetição/idempotência quando aplicável;
- teste específico e suíte relevante verdes;
- lint, typecheck, análise estática e build aplicáveis;
- mudança completa revisada, inclusive baseline sem HEAD;
- ausência de segredo, PII, cache, binário ou artefato indevido;
- revisão independente sem achado alto/bloqueante;
- riscos residuais, observabilidade e rollback registrados.

## Risco alto

Acrescente threat model, testes negativos de autorização/isolamento, concorrência,
timeout, recuperação, migrations forward/rollback, redaction e revisão por
`security-reviewer`. Não enfraqueça teste, gate ou threshold para obter verde.

## Fechamento

`VERIFIED` exige comportamento comprovado e a entrega definida no contrato. Gates
externos permanecem separados; use `LOCAL_VERIFIED_WITH_EXTERNAL_GATE` quando
somente eles faltarem.

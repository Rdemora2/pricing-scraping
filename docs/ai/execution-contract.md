# Contrato único de execução

Revisão usa [review-protocol.md](review-protocol.md): leitura por escopo,
checkpoint, ferramentas por runtime e recibo validado antes de aceitar o gate.
Rotas read_only recusam gates executáveis e --run, mesmo com --level explícito.

Este arquivo concentra o fluxo comum de implementação. `AGENTS.md`, agentes,
prompts e skills declaram apenas diferenças do papel; não devem repetir este
contrato.

## Entrada compilada uma vez

Na raiz Git, prepare a tarefa antes da primeira edição:

```bash
python3 .codex/execution_control.py prepare \
  --task-id UNIDADE \
  --goal "resultado observável" \
  --acceptance "critério verificável" \
  --file caminho/relevante \
  --signal behavior
```

O comando cria `.codex/sessions/UNIDADE/TASK_CONTEXT.md`, local e ignorado. Esse
arquivo é o handoff único entre explorer, worker, verifier e revisores. Reutilize-o
enquanto o fingerprint permanecer igual; não redescubra fatos já registrados.

O roteador lê `.codex/execution-policy.json` e decide deterministicamente risco,
papéis, promoções, ciclos máximos e gates. Sinais explícitos vencem inferências por
caminho. Produção, deploy, segredo, privilégio ou irreversibilidade resultam em
`critical`, somente leitura e autorização humana específica.

## Loop mínimo

1. O orquestrador prepara ou reutiliza a cápsula e aciona apenas os papéis da rota.
2. Um `worker` escreve fontes por Git root e implementa uma intenção lógica.
3. O orquestrador cumpre a etapa `verifier` com `gates --run`; o controle para na primeira falha e exibe
   somente a cauda útil.
4. Revisores exigidos pelo risco avaliam o diff completo, sem editar.
5. Falha determinística volta ao worker; falha transitória admite duas tentativas.
6. O orquestrador cumpre a etapa `delivery-manager` somente após evidência verde.

`roles` são participantes; `operational_stages` são responsabilidades por scripts.
Baixo: worker; médio: worker + reviewer; alto: worker + reviewer + security-reviewer.
Explorer/test-designer continuam condicionais. O principal pode ser o worker;
nunca aprova o próprio trabalho. Delegue verifier/delivery-manager apenas por
ambiguidade concreta, usando suas baselines existentes. Nenhum gate é removido.

Nunca usar Fast, `/fast` ou tiers `fast`/`priority`/`ultrafast`, no Codex/Claude ou
em subagentes. Configuração padrão: `service_tier = "default"` e
`features.fast_mode = false`. Isso não altera retroativamente conversas abertas
nem é política administrativa contra overrides. Confira o modo na retomada.
[Referência oficial](https://learn.chatgpt.com/docs/config-file/config-reference).

Execute gates sem repetir comandos equivalentes:

```bash
python3 .codex/execution_control.py gates --run --task-id UNIDADE --file caminho/relevante
```

`relevant` e `full` usam comandos oficiais detectados pelo bootstrap.
O nome legado `test_fast` significa teste direcionado, não Fast de inferência;
fail-fast e fast-forward também continuam permitidos.
Arquivos exclusivamente documentais não disparam suíte de código; revisão e hooks
continuam obrigatórios. Um nível superior pode ser solicitado explicitamente, mas
nunca inferior ao risco material observado.

## Registro de eficiência

### Reutilização seletiva

O gate `governance_contract` valida estaticamente configuração e roteamento,
em Python 3.11+, sem rede ou dependências novas. Seu fechamento está declarado
em `gates.evidence_gates`: comando argv, cwd, padrões de impacto e dependências.
É a única ativação de cache por padrão; os comandos de stack permanecem intactos
e sem cache de evidência. CI, integração, scans e revisões não são substituídos.

Cache v2 é local a cada raiz/tarefa. Hash inclui contrato, todas as dependências,
runtime confiável e ambiente fechado, não HEAD/status ou só arquivos alterados.
Execução ocorre em cópia temporária privada dos bytes fingerprintados, sem
`__pycache__`, removida ao terminar. Testamos troca A/B/A e bytecode divergente.
Entradas ausentes, ilegíveis, privadas, symlinks ou acima dos limites desabilitam
reuso; falhas e evidências antigas nunca aprovam. Mudança durante captura bloqueia.
O sistema operacional, Python e usuário local são confiáveis: isso não isola
um invasor com a mesma identidade capaz de adulterar o próprio recibo.

Não compartilhar evidências entre roots/clientes nem executar agregação mutante
no portfólio. A cápsula continua acompanhando Git para handoff separadamente.
Habilitar outro gate exige fechamento completo, execução isolável e regressões;
hash de lockfile sozinho não comprova toolchains, módulos e serviços mutáveis.

Upgrades preservam arquivos customizados. Apenas versões gerenciadas conhecidas
são substituídas; políticas customizadas incompatíveis exigem adaptação explícita.

Ao fechar uma etapa material, registre somente metadados operacionais:

```bash
python3 .codex/execution_control.py record \
  --task-id UNIDADE --stage verify --outcome success \
  --model gpt-5.6-terra --effort low --cycles 1 --tool-calls 3
```

`.codex/metrics/executions.jsonl` é local, ignorado, limitado a 500 registros e não
aceita objetivo, prompt, código, log, segredo ou PII. Consulte a tendência com:

```bash
python3 .codex/execution_control.py summary --limit 100
```

Os indicadores são sucesso na primeira passagem, ciclos, promoções, chamadas e
duração. Ausência de token count não deve ser preenchida por estimativa. Ajuste
modelo, esforço ou composição somente após evidência repetida.

## Invariantes

- Objetivo, aceite, HEAD ou estado do escopo alterado invalidam a cápsula.
- Promoção de modelo vale somente para a etapa sinalizada.
- Não releia logs, diffs ou histórico já resumidos em evidência estável.
- Não use telemetria para registrar conteúdo da tarefa ou avaliar pessoas.
- Hooks, CI, branch protection, segurança e autoridade permanecem definidos pelas
  políticas específicas; este controle não os contorna.

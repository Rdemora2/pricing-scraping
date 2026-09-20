# Escalada seletiva para GPT-6 Astra

## Baseline preservada

Terra executa trabalho previsível; Sol conduz orquestração e julgamento crítico.
Astra é uma exceção por decisão difícil, não a baseline de tarefas grandes ou
financeiras. Os arquivos de agentes continuam definindo os modelos de rotina.
Esta política complementa a política de reasoning e prevalece somente quanto à
escalada seletiva descrita aqui. Não amplia permissões nem reduz gates.

## Sinais e destino

| Sinal explícito | Evidência necessária | Override nesta etapa |
| --- | --- | --- |
| `architecture-complex` | Alternativas arquiteturais com trade-offs não resolvidos entre múltiplos módulos/contratos; descreva a decisão e restrições | `reviewer=gpt-6-astra/high` |
| `contract-conflict` | Dois contratos normativos incompatíveis, identificados por caminho/símbolo e consequência | `reviewer=gpt-6-astra/high` |
| `diagnosis-exhausted` | Mesmo fingerprint após duas tentativas focadas e diagnóstico causal com Sol ainda inconclusivo; exclua falha transitória/ambiente | `explorer=gpt-6-astra/high` |

Uma migração financeira, auth, frontend, infraestrutura ou muitos arquivos não
acionam Astra por si só: continuam no roteamento por risco com Terra/Sol.
O reviewer permanece independente e read-only; o explorer entrega hipótese,
evidência e teste discriminante. Sol/Terra implementam a decisão delimitada.
Nenhum sinal introduz um worker em uma rota crítica read-only.

## Execução e consumo

1. Registre o sinal, evidência sanitizada e pergunta específica na cápsula.
2. Execute o roteador existente com `--signal SINAL`. Ele calcula o override;
   não inicia agentes nem troca o modelo da conversa automaticamente.
3. O orquestrador aplica o modelo/esforço retornado somente ao papel indicado.
   Use contexto mínimo: decisão, contratos relevantes, diff e resultados já obtidos.
4. Faça uma passagem Astra por pergunta não resolvida. Nova passagem exige nova
   evidência ou hipótese; não reexecute revisões idênticas nem aumente max_cycles.
5. Registre modelo real, gatilho, resultado e custo/tokens quando disponíveis;
   não estime economia garantida. Resolvida a incerteza, remova o sinal e volte
   à baseline. Gates, Git, relatórios e tarefas seguintes não herdam a promoção.

`high` é o esforço da exceção; `xhigh` exige justificativa adicional,
`max` exige pedido explícito. Não promova todos os papéis por contágio.
Se Astra não estiver disponível, registre a limitação e mantenha Sol/high;
não declare a incerteza resolvida sem evidência. Se a decisão continuar
materialmente bloqueada, reporte o bloqueio, sem retry ilimitado.

O principal continua Sol/high por padrão. Quando ele próprio precisar da síntese
complexa, prefira delegá-la ao papel Astra acima; uma troca da conversa principal
é uma ação explícita do runtime, não efeito de editar TOML.

## Claude Code

Os IDs OpenAI são exclusivos do Codex. No Claude Code preserve Sonnet/Opus e use
Opus para a mesma etapa excepcional, quando disponível, com os mesmos limites
de evidência e rebaixamento. Isto é equivalência de intenção, não garantia de
paridade entre modelos ou de aplicação automática do override OpenAI.

## Referência

[GPT-6 Astra — documentação oficial](https://developers.openai.com/api/docs/models/gpt-6-astra).
A indicação para problemas difíceis fundamenta a exceção; benefícios de custo e
latência devem ser medidos no projeto, não presumidos.

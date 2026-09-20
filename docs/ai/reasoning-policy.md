# Política adaptativa de modelo e reasoning

Fast é proibido no Codex, Claude e subagentes. Verifier/delivery-manager são
etapas do orquestrador por scripts; estas baselines valem somente quando a
delegação é justificada por ambiguidade. Revisores permanecem independentes.

## Objetivo

Usar `gpt-5.6-sol` para orquestração e julgamento crítico, e `gpt-5.6-terra`
para execução previsível. Modelo maior não substitui contexto focado, testes,
evidência ou revisão independente.

## Baselines

| Papel | Modelo/esforço | Promoção permitida |
| --- | --- | --- |
| Agente principal | `sol/high` | `sol/xhigh` em decisão crítica excepcional |
| `explorer` | `terra/medium` | `sol/high` em arquitetura desconhecida ou transversal |
| `worker` | `terra/medium` | `sol/high` em migração, auth, concorrência, dados ou múltiplos módulos |
| `test-designer` | `terra/medium` | `sol/high` em state machine, recuperação ou invariantes críticos |
| `verifier` | `terra/low` | `terra/medium` para falha ambígua; `sol` só em diagnóstico complexo persistente |
| `reviewer` | `terra/medium` | `sol/high` em mudança crítica, irreversível ou transversal |
| `security-reviewer` | `sol/high` | `sol/xhigh` em combinação crítica de trust boundaries |
| `delivery-manager` | `terra/low` | `terra/medium` em conflito, CI ambígua ou estado Git inesperado |
| `repo-explorer` | `terra/low` | `terra/medium`; `sol` somente em arquitetura cross-repo incerta |
| `client-tech-lead` | `terra/medium` | `sol/high` em contrato ou arquitetura cross-repo |
| `portfolio-reviewer` | `sol/high` | `sol/xhigh` em migração coordenada de alto impacto |
| `portfolio-tech-lead` | `sol/high` | `sol/xhigh` em decisão excepcional; delegue rotina a `terra` |
| Relatório diário | `terra/medium` | `sol/high` somente em auditoria ou recuperação anômala |

A configuração do papel é a baseline. O orquestrador aplica override de modelo ou
esforço apenas à execução que apresentar gatilho e não persiste a promoção nas
etapas seguintes.

## Gatilhos para `sol`

Promova quando houver ao menos um destes sinais materiais:

- arquitetura desconhecida cruzando mais de dois módulos ou mais de um Git root;
- migração, persistência, risco de perda de dados ou rollback não trivial;
- autenticação, autorização, PII, segredo ou nova fronteira de confiança;
- concorrência, idempotência, recuperação ou estado distribuído;
- evidências conflitantes ou falha repetida sem causa explicada;
- impacto difícil de reverter ou contrato público transversal.

Não promova por tamanho de log, quantidade de arquivos, execução de checklist ou
preferência. `xhigh` exige risco alto e complexidade real. `max` não integra o
roteamento automático e exige pedido explícito do usuário.

## Rebaixamento obrigatório

Resolvida a incerteza, retorne ao modelo e esforço da baseline. Testes, coleta de
pass/fail, Git, PR, checks, merge e sincronização não herdam `sol/high` usado na
análise ou implementação. Falha determinística retorna ao papel dono; não mantenha
um papel operacional promovido para corrigir código.

## Controle de consumo

- Faça uma passagem de descoberta focada e reutilize o mapa produzido.
- Não releia diff, histórico ou saída já registrados como evidência estável.
- Não relance agentes para reproduzir artefato já suficiente.
- Limite retry transitório a dois; falha determinística muda de papel.
- Registre promoções a `sol`/`xhigh`: gatilho, papel e resultado.
- Compare periodicamente sucesso, retrabalho, defeitos, tokens, latência e chamadas
  de ferramenta; ajuste baselines somente com evidência.

Consulte também [Escalada seletiva para Astra](astra-routing.md): exceção
por evidência, preservando as baselines existentes e sem promoção automática global.

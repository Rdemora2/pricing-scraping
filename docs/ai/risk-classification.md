# Classificação de risco para uso do Codex

Use a classificação mais alta quando uma tarefa se enquadrar em mais de uma categoria. `.codex/execution-policy.json` é a fonte executável; este documento explica o contrato. Modelo e esforço seguem `reasoning-policy.md`; o nível define composição, profundidade dos gates e rollback.

| Nível | Exemplos | Composição mínima | Gates obrigatórios |
| --- | --- | --- | --- |
| Baixo | Docs, configuração isolada, correção mecânica | `worker` | Mudança revisada, check específico e hooks |
| Médio | Bug/feature isolada, refactor, contrato interno | `worker` + `reviewer` | Plano curto, teste falsificador, suíte relevante e revisão independente |
| Alto | Auth, PII, integração, migração, concorrência, infraestrutura local | `worker` + `reviewer` + `security-reviewer`; explorer/test-designer condicionais | Threat model, negativos, recuperação/rollback, suíte ampliada e duas revisões |
| Crítico | Produção, deploy, segredo, privilégio ou ação irreversível | Análise read-only; sem entrega automática | Autorização humana específica e controles operacionais externos |

## Sinais de escalada

Verifier e delivery-manager são etapas obrigatórias por scripts/orquestrador,
não conversas de IA obrigatórias. Delegue somente por ambiguidade objetiva.
Baselines e especializações permanecem; nenhum revisor independente vira autor.

Escale quando a mudança cruzar trust boundary, criar acesso, mudar contrato público, alterar persistência, incluir dados pessoais, usar rede, adicionar dependência, tocar infraestrutura ou mudar o plano de controle do próprio agente.

## Regra de decisão

Execute `python3 .codex/execution_control.py route` com caminhos e sinais observados. Na dúvida, trate como nível superior. Risco maior aumenta verificação e revisão, não cria aprovação intermediária para desenvolvimento e entrega já autorizados. O agente declara nível, motivo, papéis e evidência.

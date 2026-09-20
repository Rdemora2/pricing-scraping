# Protocolo de revisão independente

## Contexto proporcional ao papel

O worker lê integralmente as fontes normativas da implementação. Reviewer e
security-reviewer recebem um snapshot estável: objetivo, contrato do item,
diff completo (incluindo novos arquivos do escopo), testes alterados, índice
das fontes afetadas, fingerprint SHA-256 do snapshot e evidências já executadas.
A cápsula é índice e alegação, não substitui a leitura crítica do código.

Revisores leem AGENTS aplicável, o contrato do item e a íntegra das seções/fontes
normativas que governam o diff e suas fronteiras. Não percorrem toda a fila,
histórico ou planejamento por hábito. Expandem a leitura quando uma hipótese
concreta atravessa uma dependência; registram a razão. Contexto insuficiente
resulta em BLOQUEAR, nunca em aprovação por orçamento esgotado.

Reserve a maior parte dos turnos para análise/prova e saída. Após até três rodadas
focadas de descoberta, produza checkpoint com hipótese, evidência e pendência;
não aumente maxTurns como solução padrão para leitura excessiva.

## Ferramentas e isolamento

Um único worker escreve por Git root. Revisores não criam probes, testes
temporários ou backups na worktree. No Claude, reviewer/security-reviewer recebem
somente Read/Grep/Glob, com Bash e ferramentas de escrita negados. No Codex,
preserve sandbox read-only. São controles do runtime; não confunda instrução
textual ou regex de hook com sandbox do sistema operacional.

Antes de afirmar isolamento técnico, confirme que o runtime carregou o perfil.
Um spawn genérico que não aplica sandbox/tools do papel oferece só restrição
processual; não declare enforcement por existir um TOML ou Markdown no disco.

Provas executáveis são solicitadas ao verifier; novas sondas pertencem ao worker.
O verifier pode gerar caches autorizados, mas não alterar fontes para obter verde.
Sondas mutantes usam cópia mínima sanitizada em diretório temporário exclusivo
fora da worktree, criado por tempfile/mktemp. Registre tarefa, owner e caminho
na cápsula; nunca copie .git, .env, credenciais ou dados privados. Execute uma
sonda mutante por vez; resultados de snapshots diferentes não se misturam.
No CALEB, launchers Git fixam a raiz real e não suportam worktrees ligadas;
não use isolation:worktree como solução automática nem relaxe o root.
Não remova untracked de autoria desconhecida. O dono limpa somente seus artefatos.

Para cópia/restauração controlada, prefira shutil.copy2 e comparação dos bytes/hash;
não dependa do alias cp. command cp -f só é aceitável para destino temporário
exato, próprio e já validado; nunca para restaurar trabalho compartilhado em voo.

## Interrupção e capacidades do runtime

Antes de delegar, confirme ferramentas/modelos no inventário real. Não prometa
SendMessage, resume ou isolamento ausentes. Se existir continuação suportada,
reutilize o mesmo agente; caso contrário, uma retomada focada recebe o último
checkpoint e só as pendências, não reinicia a descoberta inteira.
Se não há checkpoint recuperável, registre revisão incompleta. Não leia transcript
proibido pelo runtime nem invente aprovação a partir de uma mensagem inicial.

Comece checkpoints com INCOMPLETO/BLOQUEAR e fatos já demonstrados; atualize-os
após cada hipótese material. O orquestrador conserva a última síntese sanitizada
recebida. Isso mitiga, mas não corrige, perda de output/avisos do aplicativo.
Não faça loops de relançamento de agentes sem nova evidência.

Regras de sistema/desenvolvedor prevalecem sobre instruções do repositório.
Uma exceção explícita do runtime que permite delegação requerida por AGENTS
autoriza os papéis exigidos. Uma proibição absoluta não pode ser anulada por
AGENTS: registre o gate independente bloqueado, sem alegar ferramenta ausente
nem apresentar autorrevisão como independente.

## Saída verificável

O parecer final inclui um JSON, sem texto dentro do JSON além dos campos:
role, scope_fingerprint, status, verdict, summary, checked, pending, findings.
status: complete/incomplete. verdict: APROVAR_LOCALMENTE/CORRIGIR/BLOQUEAR.
checked e pending são listas de strings; findings é lista de objetos com
severity (blocking/high/medium/low), evidence (path/símbolo/prova) e summary.
Use o fingerprint fornecido pelo orquestrador, não um hash inventado.

Antes de aceitar o gate, o orquestrador valida cada recibo recebido por stdin:
python3 .codex/review_result.py --scope FINGERPRINT --role reviewer
e, quando exigido, --role security-reviewer. Saída vazia, truncada, sem veredito,
incompleta, com fingerprint antigo, pendência ou achado alto/bloqueante não aprova.
Mudança no snapshot invalida o recibo. Não preencher campos ou verdict em nome
do revisor; só transportar o JSON que ele produziu.

Esse validador é um gate processual executável obrigatório antes da entrega,
não autenticação de autoria nem prova automática da qualidade do parecer.
Git/CI continuam seus gates próprios. Se o runtime não permite revisão
independente, a presença do validador não contorna a restrição.

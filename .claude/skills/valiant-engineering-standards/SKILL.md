---
name: valiant-engineering-standards
description: Aplique padrões técnicos da Valiant somente quando a tarefa envolve arquitetura, implementação ou revisão de Go, Web/Node ou infraestrutura. Não carregue todas as referências nem imponha padrões greenfield sobre convenções existentes.
---

# Valiant engineering standards

## Procedimento

1. Identifique o stack pelos manifests e pelo código existente; não suponha versões.
2. Leia somente a referência correspondente:
   - Go: `references/go.md`.
   - React, Next.js ou Node.js: `references/web-node.md`.
   - Terraform, AWS, Docker ou proxy: `references/platform.md`.
3. Trate a arquitetura e as dependências já adotadas como contrato. Padrões desta skill são defaults para código novo, não autorização para migração ou troca de biblioteca.
4. Se houver conflito entre a referência, a documentação local e o código em produção, cite a evidência e peça decisão antes de ampliar o escopo.
5. Aplique apenas os itens relacionados ao requisito; não faça modernização oportunista.

## Saída

Registre o padrão relevante, a evidência local, qualquer divergência e o efeito sobre implementação, testes e rollback. Não reproduza a referência inteira na resposta.

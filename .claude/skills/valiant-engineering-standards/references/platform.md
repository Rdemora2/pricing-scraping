# Plataforma e infraestrutura

Defaults para código novo quando o repositório não documentar outra escolha:

- AWS é o default corporativo; região, provedor e ambiente observados no projeto prevalecem.
- Terraform deve usar módulos revisáveis, identidade estável com `for_each`, tags comuns e backend remoto em produção.
- Nunca execute `terraform apply`, `destroy` ou `-auto-approve` sem autorização explícita e plano revisado.
- Docker usa builds multi-stage e imagem final mínima; preserve o nome de compose já adotado, preferindo `compose.yaml` em projetos novos.
- Redes privadas e públicas devem ser separadas; acesso inbound amplo requer justificativa e revisão de segurança.
- Traefik v3 é o default para novos proxies quando nenhum padrão local existir.
- Não faça deploy, alteração de cloud, segredo, privilégio ou produção por inferência.

Mudanças de infraestrutura exigem plano, revisão independente, estratégia de rollback e evidência de validação sem mutação.

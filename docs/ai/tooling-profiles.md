# Perfis opcionais de ferramentas

O kit mantém Git bruto normal e rede de shell desligada como defaults universais.
Projetos podem adotar launchers fechados quando o risco justificar, sem copiar
paths, hashes ou contratos de outro produto.

## Git fechado

`.codex/safe_git_fetch.py` oferece fetch e leituras determinísticas sem substituir
o fluxo padrão. Para bloquear Git/`gh` brutos, o repositório deve possuir tarefa
explícita de governança, launcher de entrega testado, roots/origins configuráveis e
rollback; não altere apenas `default.rules`.

## Dependências

Um perfil autônomo de dependências deve fixar gerenciador e registry, isolar cache
e configuração, rejeitar credenciais/origens arbitrárias, validar manifest e
lockfile, desligar lifecycle scripts inicialmente e vincular eventual habilitação
a evidência e hash do lockfile. O perfil deve ser específico da stack e testado em
Windows/macOS antes de entrar no bootstrap.

## Containers e serviços

Um launcher de containers deve validar o modelo renderizado, mounts, portas,
privilégios, redes, imagens/digests, scanners e SBOM antes de alcançar o daemon.
Paths de OrbStack/Docker Desktop, imagens, versões, hashes e serviços pertencem ao
projeto. O kit promove o contrato e os testes, nunca binários, caches ou sockets.

Perfis não podem ampliar produção, deploy, rede privada, Unix sockets arbitrários,
secrets ou credenciais. Alterá-los é uma trust-boundary change de risco alto.

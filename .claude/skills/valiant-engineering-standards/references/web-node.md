# Web e Node.js

Defaults para código novo quando o repositório não documentar outra escolha:

- Next.js com App Router e abordagem server-first, ou React + Vite para SPA; preserve a arquitetura existente.
- TypeScript estrito, componentes funcionais e contratos validados nas fronteiras.
- Tailwind CSS conforme a versão instalada; Shadcn/Radix, TanStack Query, Zustand, React Hook Form e Zod somente quando já adotados ou aprovados.
- Use um único linter/formatter por projeto: ESLint flat config ou Biome, nunca ambos sem justificativa explícita.
- Preserve o package manager e o lockfile existentes.
- Em backend Node.js legado, preserve Fastify/Prisma quando forem a arquitetura observada; não migre frameworks oportunisticamente.
- Evite novas dependências para utilidades simples; não introduza `moment.js`.

Versões documentadas no projeto prevalecem. Dependência ou upgrade novo exige aprovação humana.

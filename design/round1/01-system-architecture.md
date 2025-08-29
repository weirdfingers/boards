# System Architecture

- **Backend**: Python + SQLAlchemy + Supabase (storage; auth optional via adapters)
- **Job system**: Framework-agnostic queue (RQ or Dramatiq) with workers
- **API**: GraphQL (Ariadne) for data/relations; REST endpoints + SSE for job submission/progress
- **Storage**: Supabase buckets for artifacts; presigned upload/download
- **Auth**: **Pluggable** via provider adapters (Supabase Auth, Clerk, Auth0, custom JWT/OIDC)
- **Frontend**: React + shadcn (optional). **Hooks-first design**; toolkit ships hooks, not mandatory UI components.
  - Hooks encapsulate: data access, auth/session, job submission/progress, credits, boards/artifacts.
- **Observability**: structured logs, job metrics, audit trail on credit transactions.

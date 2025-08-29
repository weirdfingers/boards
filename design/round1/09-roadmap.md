# Roadmap

### Phase 1 — Foundations
- Monorepo + CI skeleton; env/config
- Core schema + migrations
- Job queue (RQ/Dramatiq) + minimal worker
- `useGeneration` MVP (submit + progress via SSE/poll)
- Hello-world docs + example app

### Phase 2 — Productization
- Credit ledger (reserve/finalize/refund) + hooks
- Auth adapters (Supabase, Clerk) + `useAuth`
- Boards & artifacts hooks; example board app
- Provider plugin skeletons (Replicate, FAL) 

### Phase 3 — Collaboration & LoRAs
- Board RBAC; invites; sharing flows
- LoRA training job + management UI via hooks
- Advanced inputs: masking, multi-input video

### Phase 4 — Ecosystem & Stability
- Additional providers (Google, Luma, etc.)
- Observability dashboards; quotas
- Hardening, docs polish, public launch

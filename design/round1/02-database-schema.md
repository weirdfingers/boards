# Database Schema

Core tables:
- **users** → external auth IDs (provider, subject), profile
- **boards** → collaborative collections (owner_id, title, metadata)
- **board_members** → user↔board membership (role: owner|editor|viewer)
- **artifacts** → generated items (type: image|video|audio|text, storage_path, metadata, inputs_ref)
- **jobs** → async job status + progress + outputs (queue_id, provider, model, params)
- **credits** → transactions ledger (reserve/finalize/refund), per-user or per-org
- **lora_models** → LoRA metadata (trigger, base_model, training_config, storage_paths)

Notes:
- Provider-agnostic **inputs_ref** stored as JSON (validated via Pydantic) for provenance.
- Migrations managed via Alembic; seed data for demo auth/providers.

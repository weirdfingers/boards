# Detailed Database Schema

## Overview
Multi-tenant database design with tenant isolation, supporting boards, generations, and collaborative features.

## SQL DDL Schema

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tenants table for multi-tenant isolation
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Users table (references external auth providers)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    auth_provider VARCHAR(50) NOT NULL, -- 'supabase', 'clerk', 'auth0', etc.
    auth_subject VARCHAR(255) NOT NULL, -- external user ID from auth provider
    email VARCHAR(255),
    display_name VARCHAR(255),
    avatar_url TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, auth_provider, auth_subject)
);

-- Boards table
CREATE TABLE boards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    settings JSONB DEFAULT '{}', -- board-specific settings
    metadata JSONB DEFAULT '{}', -- flexible metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Board members (collaboration)
CREATE TABLE board_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('viewer', 'editor', 'admin')),
    invited_by UUID REFERENCES users(id),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(board_id, user_id)
);

-- Provider configurations (per tenant)
CREATE TABLE provider_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    provider_name VARCHAR(100) NOT NULL, -- 'replicate', 'fal', 'openai', etc.
    is_enabled BOOLEAN DEFAULT TRUE,
    config JSONB NOT NULL, -- encrypted API keys, endpoints, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, provider_name)
);

-- Generations (artifacts created by generators)
CREATE TABLE generations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Generation details
    generator_name VARCHAR(100) NOT NULL, -- 'flux-pro', 'veo-2', etc.
    provider_name VARCHAR(100) NOT NULL,
    artifact_type VARCHAR(50) NOT NULL CHECK (artifact_type IN ('image', 'video', 'audio', 'text', 'lora', 'model')),
    
    -- Storage
    storage_url TEXT, -- primary artifact URL
    thumbnail_url TEXT, -- thumbnail for preview
    additional_files JSONB DEFAULT '[]', -- array of {url, type, metadata}
    
    -- Generation parameters and metadata
    input_params JSONB NOT NULL, -- validated generator-specific parameters
    output_metadata JSONB DEFAULT '{}', -- dimensions, duration, format, etc.
    
    -- Lineage tracking
    parent_generation_id UUID REFERENCES generations(id),
    input_generation_ids UUID[] DEFAULT '{}', -- array of generation IDs used as inputs
    
    -- Job tracking
    external_job_id VARCHAR(255), -- provider's job ID
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    progress DECIMAL(5,2) DEFAULT 0.0,
    error_message TEXT,
    
    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Credits/billing
CREATE TABLE credit_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    generation_id UUID REFERENCES generations(id),
    
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('reserve', 'finalize', 'refund', 'purchase', 'grant')),
    amount DECIMAL(10,4) NOT NULL,
    balance_after DECIMAL(10,4) NOT NULL,
    
    description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- LoRA models (for advanced users)
CREATE TABLE lora_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    name VARCHAR(255) NOT NULL,
    trigger_word VARCHAR(100),
    base_model VARCHAR(100) NOT NULL,
    
    storage_url TEXT NOT NULL,
    config JSONB NOT NULL, -- training parameters
    metadata JSONB DEFAULT '{}',
    
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_auth ON users(auth_provider, auth_subject);
CREATE INDEX idx_boards_tenant ON boards(tenant_id);
CREATE INDEX idx_boards_owner ON boards(owner_id);
CREATE INDEX idx_board_members_board ON board_members(board_id);
CREATE INDEX idx_board_members_user ON board_members(user_id);
CREATE INDEX idx_generations_tenant ON generations(tenant_id);
CREATE INDEX idx_generations_board ON generations(board_id);
CREATE INDEX idx_generations_user ON generations(user_id);
CREATE INDEX idx_generations_status ON generations(status);
CREATE INDEX idx_generations_lineage ON generations(parent_generation_id);
CREATE INDEX idx_credit_transactions_user ON credit_transactions(user_id);

-- Updated timestamp triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_boards_updated_at BEFORE UPDATE ON boards
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_generations_updated_at BEFORE UPDATE ON generations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## Key Design Decisions

### Multi-tenancy
- All tables include `tenant_id` for data isolation
- Enables both single-tenant (self-hosted) and multi-tenant (SaaS) deployments
- Row-level security can be implemented based on tenant_id

### Lineage Tracking
- `parent_generation_id`: Single parent for derivative works
- `input_generation_ids`: Multiple inputs for complex generations (e.g., style transfer)
- Enables visualization of creation trees and reuse patterns

### Flexible Storage
- `storage_url`: Primary artifact location (S3, GCS, Supabase, local)
- `additional_files`: Supporting files (masks, depth maps, etc.)
- Storage provider abstracted from database

### Provider/Generator Separation
- `provider_configs`: Per-tenant provider settings (API keys, endpoints)
- `generator_name` + `provider_name`: Specific model from specific provider
- Enables same model from multiple providers

### Credits System
- Transaction-based ledger for audit trail
- Reserve → Finalize pattern for long-running jobs
- Supports refunds for failed generations

## Migration Strategy
1. This DDL will be versioned in `migrations/001_initial_schema.sql`
2. Custom migration runner will apply in sequence
3. Each migration includes UP and DOWN scripts
4. Schema changes generate new SQLAlchemy models via CLI

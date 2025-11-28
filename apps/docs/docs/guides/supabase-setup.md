---
sidebar_position: 2
---

# Supabase Setup Guide

:::caution Under Construction

This documentation has not yet been fully tested with an actual Supabase project. Some steps may be incomplete or require adjustments. We welcome community contributions to validate and improve this guide.

**[Help us test this guide →](https://github.com/weirdfingers/boards/issues/152)**

:::

Learn how to configure Boards to use Supabase as your database, storage, and authentication provider instead of the default local PostgreSQL setup.

## Why Use Supabase?

Supabase provides a complete backend-as-a-service that includes:

- **PostgreSQL Database** - Managed PostgreSQL with connection pooling
- **Storage** - S3-compatible object storage for generated artifacts
- **Authentication** - Built-in auth with multiple providers
- **Realtime** - WebSocket subscriptions for live updates
- **Row Level Security** - Perfect for multi-tenant applications

This guide shows you how to migrate from the local Docker PostgreSQL setup to Supabase.

## Prerequisites

- [Supabase account](https://supabase.com) (free tier available)
- Existing Boards development environment
- Basic understanding of PostgreSQL

## 1. Create Supabase Project

1. **Sign up** at [supabase.com](https://supabase.com)
2. **Create a new project**:
   - Choose a project name (e.g., "boards-dev")
   - Set a database password (save this!)
   - Select a region close to you
3. **Wait for setup** (usually 1-2 minutes)

## 2. Get Connection Details

From your Supabase project dashboard:

1. Go to **Settings → Database**
2. Find the **Connection string** section
3. Copy the connection details:

```bash
# Direct connection (for development)
postgresql://postgres.[PROJECT_REF]:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres

# Connection pooling (for production)
postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?pgbouncer=true
```

4. Go to **Settings → API** and copy:
   - Project URL
   - Anonymous public key (`anon` key)
   - Service role key (`service_role` key) - **Keep this secret!**

## 3. Update Environment Configuration

Create or update your environment file:

```bash
# packages/backend/.env.supabase
# Database Configuration
BOARDS_DATABASE_URL=postgresql://postgres.abcdefghij:your_password@db.abcdefghij.supabase.co:5432/postgres

# Supabase API Configuration
SUPABASE_URL=https://abcdefghij.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# For production, use connection pooling:
# BOARDS_DATABASE_URL=postgresql://postgres.abcdefghij:your_password@aws-0-us-east-1.pooler.supabase.com:6543/postgres?pgbouncer=true
```

**Security Note**: Never commit the service role key to version control. Use environment variables or secure secret management.

## 4. Apply Database Schema

Apply your schema to Supabase using Alembic:

```bash
cd packages/backend
uv run alembic upgrade head
```

This will create all tables and required extensions (e.g., `uuid-ossp`).

## 5. Configure Storage

Set up Supabase Storage for generated artifacts:

### Create Storage Buckets

In the Supabase dashboard:

1. Go to **Storage**
2. Create buckets:
   - `generations` - For AI-generated content
   - `thumbnails` - For preview images
   - `lora-models` - For custom models (if applicable)

### Set Bucket Policies

```sql
-- Allow authenticated users to upload to their tenant's folder
CREATE POLICY "Users can upload to their tenant folder" ON storage.objects
FOR INSERT TO authenticated
WITH CHECK (
  bucket_id = 'generations'
  AND (storage.foldername(name))[1] = auth.jwt() ->> 'tenant_id'
);

-- Allow users to read their tenant's files
CREATE POLICY "Users can view their tenant files" ON storage.objects
FOR SELECT TO authenticated
USING (
  bucket_id = 'generations'
  AND (storage.foldername(name))[1] = auth.jwt() ->> 'tenant_id'
);
```

### Update Backend Configuration

```python
# packages/backend/src/boards/config.py
import os
from supabase import create_client

# Supabase client for storage operations
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')  # Use service key for backend

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Storage configuration
STORAGE_BUCKET = 'generations'
THUMBNAIL_BUCKET = 'thumbnails'
```

## 6. Row Level Security (RLS)

Enable RLS for multi-tenant data isolation using Alembic revisions (see Database Migrations guide for patterns). Example:

```python
from alembic import op

def upgrade() -> None:
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY;")
    # ... create policies with IF NOT EXISTS guards ...

def downgrade() -> None:
    # ... drop policies if exist, then disable RLS ...
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY;")
```

## 7. Authentication Integration

Configure Supabase Auth to work with your existing user system:

### Update User Registration

```python
# When creating users, sync with Supabase Auth
from supabase import create_client

async def create_user(email: str, password: str, tenant_id: str):
    # Create user in Supabase Auth
    auth_response = supabase.auth.sign_up({
        "email": email,
        "password": password,
        "options": {
            "data": {
                "tenant_id": tenant_id  # Custom claim for RLS
            }
        }
    })

    # Create user record in your database
    user_record = await create_user_record(
        auth_subject=auth_response.user.id,
        auth_provider="supabase",
        email=email,
        tenant_id=tenant_id
    )

    return user_record
```

### JWT Custom Claims

Ensure the JWT includes tenant_id for RLS policies:

```sql
-- Function to add tenant_id to JWT
CREATE OR REPLACE FUNCTION public.custom_access_token_hook(event jsonb)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
BEGIN
  -- Add tenant_id from user metadata to JWT
  IF event->>'user_id' IS NOT NULL THEN
    DECLARE tenant_id TEXT;
    SELECT u.tenant_id INTO tenant_id
    FROM public.users u
    WHERE u.auth_subject = (event->>'user_id')
    AND u.auth_provider = 'supabase';

    IF tenant_id IS NOT NULL THEN
      event := jsonb_set(event, '{tenant_id}', to_jsonb(tenant_id), true);
    END IF;
  END IF;

  RETURN event;
END;
$$;

-- Grant permissions
GRANT EXECUTE ON FUNCTION public.custom_access_token_hook TO service_role;
```

## 8. Local Development Options

### Option 1: Direct Remote Connection

Use your Supabase project directly for development:

```bash
# Use remote database URL
export BOARDS_DATABASE_URL="postgresql://postgres.xxx:password@db.xxx.supabase.co:5432/postgres"

# Start development
make dev
```

**Pros**: Real cloud environment, no local setup needed  
**Cons**: Requires internet connection, shared with team

### Option 2: Supabase CLI Local Development

Run Supabase locally while staying in sync with remote:

```bash
# Start local Supabase
supabase start

# This provides local URLs:
# Database: postgresql://postgres:postgres@localhost:54322/postgres
# API URL: http://localhost:54321

# Sync schema from remote
supabase db pull

# Make local changes and push
supabase db push
```

**Pros**: Offline development, isolated environment  
**Cons**: Additional setup, need to sync changes

## 9. Production Configuration

### Connection Pooling

For production, use connection pooling to handle high load:

```bash
# Use pooled connection string
BOARDS_DATABASE_URL=postgresql://postgres.xxx:password@aws-0-region.pooler.supabase.com:6543/postgres?pgbouncer=true
```

### Performance Optimization

```sql
-- Add indexes for common queries (if not already present)
CREATE INDEX CONCURRENTLY idx_generations_tenant_status ON generations(tenant_id, status);
CREATE INDEX CONCURRENTLY idx_boards_tenant_owner ON boards(tenant_id, owner_id);

-- Optimize for time-series queries
CREATE INDEX CONCURRENTLY idx_generations_created_at ON generations(created_at DESC);
```

### Monitoring and Alerts

Set up monitoring in Supabase dashboard:

1. **Database** tab → Monitor connection count, query performance
2. **API** tab → Monitor request volume and errors
3. **Storage** tab → Monitor storage usage and bandwidth

## 10. Testing Your Setup

Verify everything works:

```bash
# Test database connection
psql $BOARDS_DATABASE_URL -c "SELECT version();"

# Test your application
cd packages/backend
python -c "from boards.dbmodels import Users, Boards; print('✅ import ok')"

# Start the development server
make dev
```

## Next Steps

With Supabase configured, you can now:

1. **Deploy to production** using the same Supabase project
2. **Set up Supabase Storage** for file uploads and serving
3. **Configure Supabase Auth** for user authentication
4. **Use Supabase Realtime** for live updates
5. **Set up Edge Functions** for webhooks and background jobs

For detailed migration workflows, see the [Database Migrations guide](../backend/migrations.md).

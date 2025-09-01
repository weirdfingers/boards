---
sidebar_position: 2
---

# Supabase Setup Guide

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
DATABASE_URL=postgresql://postgres.abcdefghij:your_password@db.abcdefghij.supabase.co:5432/postgres

# Supabase API Configuration  
SUPABASE_URL=https://abcdefghij.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# For production, use connection pooling:
# DATABASE_URL=postgresql://postgres.abcdefghij:your_password@aws-0-us-east-1.pooler.supabase.com:6543/postgres?pgbouncer=true
```

**Security Note**: Never commit the service role key to version control. Use environment variables or secure secret management.

## 4. Apply Database Schema

Apply your existing schema to the Supabase database:

### Option A: Direct SQL Application

```bash
# Navigate to backend directory
cd packages/backend

# Apply schema directly to Supabase
psql $DATABASE_URL < migrations/schemas/001_initial_schema.sql
```

### Option B: Using Migration System

```bash
# Generate migration comparing empty DB to your schema
python scripts/generate_migration.py --name initial_supabase_setup --current-db $DATABASE_URL

# Review the generated migration
cat migrations/generated/*_initial_supabase_setup_up.sql

# Apply the migration
psql $DATABASE_URL < migrations/generated/*_initial_supabase_setup_up.sql
```

### Option C: Using Supabase CLI

```bash
# Install Supabase CLI
npm install -g supabase

# Initialize Supabase in your project
supabase init

# Link to your remote project
supabase link --project-ref your-project-ref

# Push your local schema to Supabase
supabase db push
```

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

Enable RLS for multi-tenant data isolation:

```sql
-- Enable RLS on all tables
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE boards ENABLE ROW LEVEL SECURITY;
ALTER TABLE generations ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;

-- Create policies for tenant isolation
-- Users can only see their own tenant's data
CREATE POLICY "Users can access their tenant data" ON boards
FOR ALL TO authenticated
USING (tenant_id = auth.jwt() ->> 'tenant_id');

CREATE POLICY "Users can access their tenant generations" ON generations
FOR ALL TO authenticated  
USING (tenant_id = auth.jwt() ->> 'tenant_id');

-- Similar policies for other tables...
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
export DATABASE_URL="postgresql://postgres.xxx:password@db.xxx.supabase.co:5432/postgres"

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
DATABASE_URL=postgresql://postgres.xxx:password@aws-0-region.pooler.supabase.com:6543/postgres?pgbouncer=true
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

## 10. Migration Script

Create a helper script to migrate existing data:

```python
# scripts/migrate_to_supabase.py
import os
import asyncio
from sqlalchemy import create_engine, text

async def migrate_to_supabase():
    """Migrate existing local data to Supabase."""
    
    # Source (local) and destination (Supabase) databases
    local_url = "postgresql://boards:boards_dev@localhost:5433/boards_dev"
    supabase_url = os.environ.get('DATABASE_URL')
    
    local_engine = create_engine(local_url)
    supabase_engine = create_engine(supabase_url)
    
    try:
        # Tables to migrate (in dependency order)
        tables = ['tenants', 'users', 'boards', 'board_members', 'generations']
        
        for table in tables:
            print(f"Migrating {table}...")
            
            # Export from local
            with local_engine.connect() as local_conn:
                result = local_conn.execute(text(f"SELECT * FROM {table}"))
                rows = result.fetchall()
                columns = result.keys()
            
            # Import to Supabase
            if rows:
                with supabase_engine.connect() as supabase_conn:
                    # Build INSERT statement with conflict handling
                    placeholders = ", ".join([f":{col}" for col in columns])
                    insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
                    
                    # Insert data with error handling
                    try:
                        supabase_conn.execute(text(insert_sql), [dict(row) for row in rows])
                        supabase_conn.commit()
                        print(f"Migrated {len(rows)} rows from {table}")
                    except Exception as e:
                        print(f"Error migrating table {table}: {e}")
                        supabase_conn.rollback()
                        continue
            else:
                print(f"No data to migrate for {table}")
    finally:
        # Properly close database connections
        local_engine.dispose()
        supabase_engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate_to_supabase())
```

Run the migration:

```bash
python scripts/migrate_to_supabase.py
```

## 11. Testing Your Setup

Verify everything works:

```bash
# Test database connection
psql $DATABASE_URL -c "SELECT version();"

# Test your application
cd packages/backend
python -c "
from boards.database.models import User, Board
from sqlalchemy import create_engine
engine = create_engine('$DATABASE_URL')
print('✅ Database connection successful')
"

# Start the development server
make dev
```

## Troubleshooting

### Connection Issues

**Problem**: `connection to server failed`
```bash
# Check your connection string format
echo $DATABASE_URL

# Test direct connection
psql "postgresql://postgres.xxx:password@db.xxx.supabase.co:5432/postgres" -c "SELECT 1;"
```

**Problem**: SSL connection errors
```bash
# Add SSL mode to connection string
DATABASE_URL="postgresql://...?sslmode=require"
```

### Schema Issues

**Problem**: Missing extensions
```sql
-- Enable required extensions in Supabase SQL editor
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- for text search
```

**Problem**: Permission denied
- Ensure you're using the correct connection string
- Use service role key for backend operations
- Check RLS policies aren't blocking your queries

### Performance Issues

**Problem**: Slow queries
```sql
-- Check for missing indexes
EXPLAIN ANALYZE SELECT * FROM generations WHERE tenant_id = 'xxx';

-- Add missing indexes
CREATE INDEX CONCURRENTLY idx_missing ON table_name(column_name);
```

### RLS Policy Issues

**Problem**: No data returned with RLS enabled
```sql
-- Test without RLS first
ALTER TABLE boards DISABLE ROW LEVEL SECURITY;

-- Check JWT claims
SELECT auth.jwt();

-- Verify policy logic
SELECT * FROM boards WHERE tenant_id = auth.jwt() ->> 'tenant_id';
```

## Next Steps

With Supabase configured, you can now:

1. **Deploy to production** using the same Supabase project
2. **Set up Supabase Storage** for file uploads and serving
3. **Configure Supabase Auth** for user authentication  
4. **Use Supabase Realtime** for live updates
5. **Set up Edge Functions** for webhooks and background jobs

For detailed migration workflows, see the [Database Migrations guide](../backend/migrations.md).

For deployment strategies, check the [Deployment Overview](../deployment/overview.md).
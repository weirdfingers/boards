---
title: Supabase Database
description: Use Supabase PostgreSQL with Boards.
sidebar_position: 3
---

# Supabase Database

[Supabase](https://supabase.com) provides a managed PostgreSQL database with built-in connection pooling, auth, and storage. If you're also using Supabase for authentication or storage, this is a natural choice.

## Getting Started

### 1. Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and create an account
2. Create a new project
3. Wait for the database to be provisioned

### 2. Get Connection Details

In your Supabase dashboard:

1. Go to **Settings** > **Database**
2. Find the connection string under **Connection string** > **URI**

You'll see two options:
- **Direct connection** (port 5432) - For long-running processes
- **Connection pooling** (port 6543) - Recommended for serverless and high-concurrency

### 3. Configure Boards

Use the pooled connection URL for best performance:

```bash
# .env
BOARDS_DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
```

Replace:
- `[project-ref]` with your project reference (e.g., `abcdefghijkl`)
- `[password]` with your database password
- `[region]` with your project's region (e.g., `us-east-1`)

## Connection Modes

### Session Mode (Recommended)

For applications with persistent connections:

```bash
# Port 5432 - Direct connection
BOARDS_DATABASE_URL=postgresql://postgres.[ref]:[pass]@db.[ref].supabase.co:5432/postgres
```

### Transaction Mode

For serverless deployments with many short-lived connections:

```bash
# Port 6543 - Pooled connection
BOARDS_DATABASE_URL=postgresql://postgres.[ref]:[pass]@aws-0-[region].pooler.supabase.com:6543/postgres
```

:::note
Transaction mode doesn't support prepared statements. Boards uses parameterized queries which work correctly in both modes.
:::

## Using with Supabase Auth

If you're using Supabase for both database and authentication:

```bash
# Database
BOARDS_DATABASE_URL=postgresql://postgres.[ref]:[pass]@aws-0-[region].pooler.supabase.com:6543/postgres

# Auth
BOARDS_AUTH_PROVIDER=supabase
SUPABASE_URL=https://[ref].supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

See [Authentication](../authentication.md) for full auth setup.

## Using with Supabase Storage

Supabase Storage can be used alongside the database:

```yaml
# storage_config.yaml
default_provider: supabase

providers:
  supabase:
    type: supabase
    bucket: boards-storage
```

```bash
# .env
SUPABASE_URL=https://[ref].supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

## Free Tier Limits

Supabase's free tier includes:

| Resource | Limit |
|----------|-------|
| Database size | 500 MB |
| Bandwidth | 2 GB/month |
| Connections | 60 direct, unlimited pooled |
| Pausing | After 7 days inactive |

For production workloads, consider the Pro plan or higher.

## Security

### Database Password

Reset your database password in **Settings** > **Database** > **Database password**.

### Service Role Key

The service role key bypasses Row Level Security. Keep it secure:

1. Never expose in client-side code
2. Store in environment variables or secrets manager
3. Rotate periodically in **Settings** > **API**

### IP Allowlist

Supabase allows connections from any IP by default. To restrict:

1. Go to **Settings** > **Database** > **Network Restrictions**
2. Add your server's IP addresses

## Migrations

Migrations run automatically on API startup. You can also run them via the Supabase SQL Editor:

1. Go to **SQL Editor** in your dashboard
2. Run migration files from `packages/backend/src/boards/db/migrations/`

## Monitoring

Monitor your database in the Supabase dashboard:

- **Database** > **Reports** - Query performance
- **Database** > **Postgres Logs** - Connection and error logs
- **Settings** > **Infrastructure** - Resource usage

## Troubleshooting

### "Database is paused"

Free tier projects pause after 7 days of inactivity:

1. Go to your project dashboard
2. Click **Restore project**
3. Consider upgrading to Pro for always-on

### Connection Timeout

1. Use the pooled connection URL (port 6543)
2. Check your deployment region matches Supabase region
3. Verify network connectivity to Supabase

### "Prepared statement already exists"

Switch to transaction pooling mode or ensure your connection string uses port 6543.

## Next Steps

- [Supabase Auth Setup](/docs/auth/providers/supabase) - Configure authentication
- [Storage Configuration](../storage.md) - Set up Supabase Storage

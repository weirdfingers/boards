---
title: Neon
description: Use Neon serverless PostgreSQL with Boards.
sidebar_position: 7
---

# Neon Serverless PostgreSQL

[Neon](https://neon.tech) is a serverless PostgreSQL platform with automatic scaling, branching, and a generous free tier.

## Why Neon?

- **Serverless**: Scales to zero when idle, scales up automatically
- **Branching**: Create instant database copies for development
- **Generous free tier**: 0.5 GB storage, 190 compute hours/month
- **Built-in connection pooling**: No separate pooler needed

## Getting Started

### 1. Create a Neon Account

1. Go to [neon.tech](https://neon.tech) and sign up
2. Create a new project
3. Select your region (choose closest to your deployment)

### 2. Get Connection String

In the Neon console:

1. Go to your project **Dashboard**
2. Find the connection string in the **Connection Details** panel
3. Copy the **Pooled connection** string

### 3. Configure Boards

```bash
# .env
BOARDS_DATABASE_URL=postgresql://username:password@ep-cool-name-123456.us-east-2.aws.neon.tech/boards?sslmode=require
```

## Connection Modes

### Pooled Connection (Recommended)

Use the pooled connection endpoint for web applications:

```bash
# Pooled (notice -pooler in hostname)
BOARDS_DATABASE_URL=postgresql://user:pass@ep-name-123456-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
```

### Direct Connection

Use direct connection for migrations and admin tasks:

```bash
# Direct
BOARDS_DATABASE_URL=postgresql://user:pass@ep-name-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
```

## Serverless Driver (Optional)

For serverless deployments (Cloud Run, Lambda), Neon provides a specialized driver. However, the standard `psycopg2` connection works well for most Boards deployments.

## Database Branching

Neon's killer feature is instant database branching:

### Create a Development Branch

```bash
# Via Neon CLI
neonctl branches create --name dev --project-id your-project-id

# Get connection string for branch
neonctl connection-string dev --project-id your-project-id
```

### Use Cases

- **Development**: Each developer gets their own branch
- **Testing**: Create branch before running tests, delete after
- **Previews**: Branch per PR for preview deployments

### Workflow Example

```bash
# Create branch for feature
neonctl branches create --name feature-xyz --parent main

# Run migrations on branch
BOARDS_DATABASE_URL="branch-connection-string" python -m boards.db.migrate

# Test feature...

# Delete branch when done
neonctl branches delete feature-xyz --project-id your-project-id
```

## Autoscaling

Neon automatically scales compute based on load:

| Tier | Min CU | Max CU | Autosuspend |
|------|--------|--------|-------------|
| Free | 0.25 | 0.25 | 5 min |
| Launch | 0.25 | 4 | Configurable |
| Scale | 0.25 | 8 | Configurable |

**Compute Units (CU)**: 1 CU = 1 vCPU, 4 GB RAM

### Configure Autoscaling

In the Neon console or via API:

```bash
neonctl endpoints update \
  --project-id your-project-id \
  --autoscaling-min-cu 0.25 \
  --autoscaling-max-cu 4
```

### Autosuspend

Configure when idle databases suspend:

```bash
neonctl endpoints update \
  --project-id your-project-id \
  --suspend-timeout-seconds 300  # 5 minutes
```

Set to `0` to disable (always-on).

## Cold Start Handling

Serverless databases have cold starts when scaling from zero. For Boards:

1. **First request**: May take 500ms-2s for cold start
2. **Subsequent requests**: Normal latency

To minimize cold starts:
- Keep autosuspend timeout higher (10-15 min)
- Use a keep-alive ping from your application
- Upgrade to a paid tier for faster cold starts

## IP Allow List

On paid tiers, restrict access by IP:

1. Go to project **Settings** > **IP Allow**
2. Add your server IP addresses
3. Enable **Require IP Allow**

## Monitoring

### Neon Console

Monitor in the dashboard:
- **Metrics**: CPU, memory, connections, storage
- **Operations**: Query history and performance
- **Branches**: Branch usage and storage

### Connection Info

Check connections programmatically:

```sql
SELECT count(*) FROM pg_stat_activity;
```

## Free Tier Limits

| Resource | Limit |
|----------|-------|
| Storage | 0.5 GB |
| Compute | 190 hours/month |
| Branches | 10 |
| Projects | 1 |

For Boards production workloads, consider the Launch ($19/month) or Scale tier.

## Pricing

| Tier | Monthly Base | Compute | Storage |
|------|-------------|---------|---------|
| Free | $0 | 190 CU-hours | 0.5 GB |
| Launch | $19 | 300 CU-hours | 10 GB |
| Scale | $69 | 750 CU-hours | 50 GB |

Additional usage billed per compute-hour and GB.

## Troubleshooting

### Connection Timeout on Cold Start

Increase connection timeout:

```bash
BOARDS_DATABASE_URL=postgresql://...?connect_timeout=30
```

### "Too Many Connections"

Use the pooled connection endpoint (has `-pooler` in hostname).

### Branch Not Found

Verify branch exists and connection string is correct:

```bash
neonctl branches list --project-id your-project-id
```

## Next Steps

- [Cloud Run Deployment](../cloud/cloud-run.md) - Great pairing with Neon
- [Railway Deployment](../cloud/railway.md) - Another serverless-friendly option

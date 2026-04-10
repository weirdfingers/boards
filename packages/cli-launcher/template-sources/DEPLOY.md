# Deployment Guide

This guide covers deploying your Boards project to **Railway** and **Fly.io**. Both platforms support the full stack: frontend (Next.js), API (Python/uvicorn), worker, PostgreSQL, and Redis.

## Prerequisites

- Your scaffolded project (created with `npx @weirdfingers/baseboards up`)
- At least one AI provider API key (Replicate, FAL, OpenAI, etc.)
- An account on [Railway](https://railway.app) or [Fly.io](https://fly.io)

---

## Deploy to Railway

Railway provides the simplest deployment path with built-in PostgreSQL, Redis, and S3-compatible object storage.

### 1. Install Railway CLI

```bash
npm install -g @railway/cli
railway login
```

### 2. Create a Railway Project

```bash
railway init
```

Or create a project at [railway.app/new](https://railway.app/new).

### 3. Provision Databases

Add PostgreSQL and Redis from the Railway dashboard:

1. Open your project at railway.app
2. Click **+ New** > **Database** > **Add PostgreSQL**
3. Click **+ New** > **Database** > **Add Redis**

### 4. Provision Object Storage (Railway Buckets)

1. Click **+ New** > **Add** > **Object Storage (S3-compatible)**
2. Railway provisions an S3-compatible bucket with credentials
3. Note the following variables from the bucket service:
   - `RAILWAY_STORAGE_ENDPOINT`
   - `RAILWAY_STORAGE_ACCESS_KEY_ID`
   - `RAILWAY_STORAGE_SECRET_ACCESS_KEY`
   - `RAILWAY_STORAGE_BUCKET_NAME`

### 5. Set Secrets

Set your API keys and auth config in the Railway dashboard or CLI:

```bash
# Provider API keys (set at least one)
railway variables set REPLICATE_API_TOKEN=your-token
railway variables set FAL_KEY=your-key
railway variables set OPENAI_API_KEY=your-key

# JWT secret (generate a random 32+ char string)
railway variables set BOARDS_JWT_SECRET=$(openssl rand -hex 32)

# Storage credentials (from Railway Buckets)
railway variables set AWS_ACCESS_KEY_ID=$RAILWAY_STORAGE_ACCESS_KEY_ID
railway variables set AWS_SECRET_ACCESS_KEY=$RAILWAY_STORAGE_SECRET_ACCESS_KEY
```

### 6. Update Storage Config for Production

Edit `config/storage_config.yaml` to use the S3 provider:

```yaml
storage:
  default_provider: "s3"
  providers:
    s3:
      type: "s3"
      config:
        bucket: "${RAILWAY_STORAGE_BUCKET_NAME}"
        region: "auto"
        endpoint_url: "${RAILWAY_STORAGE_ENDPOINT}"
```

Or use the included `.env.production.example` as a reference for environment-based configuration.

### 7. Deploy

The included `railway.json` defines three services (api, worker, web) with proper environment variable wiring:

```bash
railway up
```

Railway automatically:
- Wires `DATABASE_URL` and `REDIS_URL` from provisioned databases
- Runs Alembic migrations on API startup
- Sets up internal networking between services
- Provisions HTTPS endpoints

### 8. Verify

```bash
# Check service status
railway status

# View logs
railway logs
```

Visit your Railway dashboard to find the public URLs for the web and API services.

---

## Deploy to Fly.io

Fly.io deploys containers to their global edge network. This project includes three Fly config files for each service.

### 1. Install Fly CLI

```bash
# macOS
brew install flyctl

# Linux
curl -L https://fly.io/install.sh | sh

fly auth login
```

### 2. Provision PostgreSQL

```bash
fly postgres create --name boards-db
```

Save the connection string from the output.

### 3. Provision Redis (Upstash)

```bash
fly redis create --name boards-redis
```

Save the Redis URL from the output.

### 4. Provision Object Storage (Tigris)

```bash
fly storage create --name boards-storage
```

This provisions a Tigris S3-compatible bucket. Save the credentials:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_ENDPOINT_URL_S3`
- `BUCKET_NAME`

### 5. Deploy the API

```bash
# Create the app (edit fly.api.toml to change app name/region first)
fly launch --config fly.api.toml --copy-config --no-deploy

# Attach PostgreSQL (auto-sets DATABASE_URL)
fly postgres attach boards-db --app boards-api

# Set secrets
fly secrets set \
  BOARDS_DATABASE_URL="postgres://..." \
  BOARDS_REDIS_URL="redis://..." \
  BOARDS_JWT_SECRET=$(openssl rand -hex 32) \
  BOARDS_CORS_ORIGINS='["https://boards-web.fly.dev"]' \
  AWS_ACCESS_KEY_ID=your-tigris-key \
  AWS_SECRET_ACCESS_KEY=your-tigris-secret \
  REPLICATE_API_TOKEN=your-token \
  --app boards-api

# Deploy
fly deploy --config fly.api.toml
```

### 6. Deploy the Worker

```bash
# Create the worker app
fly launch --config fly.worker.toml --copy-config --no-deploy

# Attach PostgreSQL
fly postgres attach boards-db --app boards-worker

# Set secrets (same provider keys as API)
fly secrets set \
  BOARDS_DATABASE_URL="postgres://..." \
  BOARDS_REDIS_URL="redis://..." \
  BOARDS_INTERNAL_API_URL="http://boards-api.internal:8800" \
  AWS_ACCESS_KEY_ID=your-tigris-key \
  AWS_SECRET_ACCESS_KEY=your-tigris-secret \
  REPLICATE_API_TOKEN=your-token \
  --app boards-worker

# Deploy
fly deploy --config fly.worker.toml
```

### 7. Deploy the Frontend

```bash
# Edit fly.web.toml to set your app name, then build args for API URLs
fly launch --config fly.web.toml --copy-config --no-deploy

# Set build-time env vars (Next.js needs these at build time)
fly secrets set \
  NEXT_PUBLIC_API_URL="https://boards-api.fly.dev" \
  NEXT_PUBLIC_GRAPHQL_URL="https://boards-api.fly.dev/graphql" \
  NEXT_PUBLIC_AUTH_PROVIDER=none \
  --app boards-web

# Deploy from the project root (Dockerfile.web is in the root)
fly deploy --config fly.web.toml --dockerfile Dockerfile.web
```

### 8. Update Storage Config for Production

Edit `config/storage_config.yaml`:

```yaml
storage:
  default_provider: "s3"
  providers:
    s3:
      type: "s3"
      config:
        bucket: "${BUCKET_NAME}"
        region: "auto"
        endpoint_url: "${AWS_ENDPOINT_URL_S3}"
```

### 9. Verify

```bash
fly status --app boards-api
fly status --app boards-worker
fly status --app boards-web

# Stream logs
fly logs --app boards-api
```

---

## Authentication Setup

Both platforms require the same auth configuration. Set these environment variables on the API and web services:

### No Auth (Development/Testing)

```bash
BOARDS_AUTH_PROVIDER=none
NEXT_PUBLIC_AUTH_PROVIDER=none
```

### Clerk

```bash
# API service
BOARDS_AUTH_PROVIDER=clerk
CLERK_SECRET_KEY=sk_live_...

# Web service
NEXT_PUBLIC_AUTH_PROVIDER=clerk
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
```

### Supabase

```bash
# API service
BOARDS_AUTH_PROVIDER=supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=...

# Web service
NEXT_PUBLIC_AUTH_PROVIDER=supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
```

### JWT (Custom)

```bash
# API service
BOARDS_AUTH_PROVIDER=jwt
BOARDS_JWT_SECRET=your-secret-key
```

---

## Environment Variables Reference

See `.env.production.example` for a complete list of production environment variables. Key variables:

| Variable | Service | Description |
|----------|---------|-------------|
| `BOARDS_DATABASE_URL` | api, worker | PostgreSQL connection string |
| `BOARDS_REDIS_URL` | api, worker | Redis connection string |
| `BOARDS_JWT_SECRET` | api | Secret for JWT token signing |
| `BOARDS_CORS_ORIGINS` | api | JSON array of allowed CORS origins |
| `BOARDS_INTERNAL_API_URL` | worker | Internal URL for worker-to-API communication |
| `BOARDS_AUTH_PROVIDER` | api | Auth provider: none, clerk, supabase, jwt |
| `NEXT_PUBLIC_API_URL` | web | Public URL of the API service |
| `NEXT_PUBLIC_GRAPHQL_URL` | web | Public URL of the GraphQL endpoint |
| `AWS_ACCESS_KEY_ID` | api, worker | S3-compatible storage access key |
| `AWS_SECRET_ACCESS_KEY` | api, worker | S3-compatible storage secret key |

---

## Troubleshooting

### Database Migrations Fail

- Verify `BOARDS_DATABASE_URL` is set correctly
- Check the database is accessible from the service network
- On Railway: migrations run automatically via the start command in `railway.json`
- On Fly.io: migrations run via `release_command` in `fly.api.toml`

### Worker Not Processing Jobs

- Verify `BOARDS_REDIS_URL` is set on the worker
- Check `BOARDS_INTERNAL_API_URL` points to the API's internal address
- On Railway: use `http://${{api.RAILWAY_PRIVATE_DOMAIN}}:8800`
- On Fly.io: use `http://boards-api.internal:8800`

### Storage Upload Errors

- Verify S3-compatible credentials are set on both api and worker services
- Check `storage_config.yaml` uses the `s3` provider with correct endpoint
- Ensure the bucket exists and credentials have write access

### CORS Errors

- Set `BOARDS_CORS_ORIGINS` to include your frontend's public URL
- Format: `["https://your-frontend.fly.dev"]` (JSON array)

---
sidebar_position: 1
---

# Installing Baseboards

Complete guide to installing and configuring Baseboards, the one-command Boards deployment.

## What You'll Get

Baseboards provides a complete, containerized Boards instance including:

- **Web UI** - Next.js frontend at http://localhost:3300
- **GraphQL API** - Backend server at http://localhost:8088
- **PostgreSQL** - Database for persistent storage
- **Redis** - Job queue and caching
- **Worker** - Background job processor for AI generation

## Prerequisites

### Required Software

- **Docker Desktop** (macOS/Windows) or **Docker Engine** (Linux)
  - [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)
  - Verify: `docker --version` and `docker compose version`

- **Node.js 20+**
  - [Download Node.js](https://nodejs.org/)
  - Verify: `node --version`

### System Requirements

- **Memory**: 4GB RAM minimum, 8GB recommended
- **Disk Space**: 2GB for Docker images + storage for generated content
- **Ports**: 3300 (web), 8088 (api) must be available

## Installation

### Step 1: Run the CLI

```bash
npx @weirdfingers/baseboards up my-boards-app
```

This command will:

1. ✅ Check system prerequisites (Docker, Node.js)
2. 📁 Create project directory with templates
3. 🔑 Prompt for API keys (optional - can add later)
4. 🐳 Pull Docker images
5. 🚀 Start all services in detached mode

### Step 2: Enter API Keys

The CLI will prompt you to enter API keys for AI providers:

```
? Enter Replicate API key (optional): r8_xxxxx
? Enter OpenAI API key (optional): sk-xxxxx
? Enter FAL API key (optional): xxxxx
? Enter Google AI API key (optional): xxxxx
```

**Tip:** You can skip this and add keys later by editing `api/.env`.

### Step 3: Wait for Services

The CLI will start all services. This may take a few minutes on first run while Docker images are downloaded.

```
✓ Services started successfully
✓ Web UI: http://localhost:3300
✓ GraphQL API: http://localhost:8088/graphql
```

### Step 4: Access Baseboards

Open http://localhost:3300 in your browser. You should see the Boards interface!

## Getting API Keys

To use AI generators, you'll need API keys from providers:

### Replicate (Recommended)

1. Sign up at https://replicate.com
2. Go to https://replicate.com/account/api-tokens
3. Create a new token
4. Copy the token (starts with `r8_`)

**Supported models:**
- FLUX Schnell (fast image generation)
- Stable Diffusion XL
- Many other models

### OpenAI

1. Sign up at https://platform.openai.com
2. Go to https://platform.openai.com/api-keys
3. Create a new API key
4. Copy the key (starts with `sk-`)

**Supported models:**
- GPT-4o (text generation)
- DALL-E 3 (image generation)

### FAL.ai

1. Sign up at https://fal.ai
2. Go to https://fal.ai/dashboard/keys
3. Create a new API key
4. Copy the key

**Supported models:**
- Fast Flux models
- Real-time image generation

### Google AI

1. Sign up at https://ai.google.dev
2. Go to https://makersuite.google.com/app/apikey
3. Create a new API key
4. Copy the key

**Supported models:**
- Gemini models

## Configuration

### Adding or Updating API Keys

Edit `api/.env` in your installation directory:

```bash
cd my-boards-app
nano api/.env  # or use your preferred editor
```

Update the `BOARDS_GENERATOR_API_KEYS` variable:

```bash
BOARDS_GENERATOR_API_KEYS={"REPLICATE_API_KEY":"r8_...","OPENAI_API_KEY":"sk-...","FAL_API_KEY":"...","GOOGLE_API_KEY":"..."}
```

After editing, restart the services:

```bash
baseboards down
baseboards up
```

### Configuring Generators

Edit `api/config/generators.yaml` to enable/disable generators or add new ones:

```yaml
generators:
  # Enable Replicate FLUX Schnell (fast image generation)
  - name: flux-schnell
    provider: replicate
    type: text-to-image
    model: black-forest-labs/flux-schnell
    enabled: true

  # Enable OpenAI GPT-4o
  - name: gpt-4o
    provider: openai
    type: text-to-text
    model: gpt-4o
    enabled: true
```

See the [Generators documentation](../generators/configuration) for more details.

### Configuring Storage

By default, Baseboards uses local file storage. To use cloud storage, edit `api/config/storage_config.yaml`:

```yaml
# Local storage (default)
type: local
local:
  base_path: /app/data/storage

# Amazon S3
# type: s3
# s3:
#   bucket: my-boards-bucket
#   region: us-east-1
#   access_key_id: AWS_ACCESS_KEY_ID  # Or set AWS_ACCESS_KEY_ID env var
#   secret_access_key: AWS_SECRET_ACCESS_KEY  # Or set AWS_SECRET_ACCESS_KEY env var

# Google Cloud Storage
# type: gcs
# gcs:
#   bucket: my-boards-bucket
#   project_id: my-project
#   credentials_path: /path/to/service-account.json

# Supabase Storage
# type: supabase
# supabase:
#   url: https://xxx.supabase.co
#   key: your-anon-key
#   bucket: boards-storage
```

See the [Storage documentation](../backend/storage) for configuration details.

### Custom Ports

If the default ports are in use:

```bash
baseboards up --ports web=3301,api=8089
```

Or edit `docker/compose.yaml` to change ports permanently.

## Using Baseboards

### Managing Services

```bash
# Stop services
baseboards down

# Start services
baseboards up

# Restart services
baseboards down && baseboards up

# View logs
baseboards logs

# Follow logs in real-time
baseboards logs -f

# View specific service logs
baseboards logs api
baseboards logs worker

# Check service status
baseboards status
```

### Updating Baseboards

```bash
# Update to latest version (preserves your data and configuration)
baseboards update
```

### Cleaning Up

```bash
# Stop and remove containers (keeps data)
baseboards down

# Stop and remove containers + data
baseboards down --volumes

# Full cleanup including Docker images
baseboards clean --hard
```

## Troubleshooting

### Docker Not Running

**Error:** `Cannot connect to the Docker daemon`

**Solution:** Start Docker Desktop or Docker Engine

```bash
# macOS/Windows: Open Docker Desktop application

# Linux: Start Docker service
sudo systemctl start docker
```

### Port Already in Use

**Error:** `Bind for 0.0.0.0:3300 failed: port is already allocated`

**Solution:** Use custom ports or stop the conflicting service

```bash
# Use custom ports
baseboards up --ports web=3301,api=8089

# Or find and stop the conflicting process
lsof -i :3300  # macOS/Linux
netstat -ano | findstr :3300  # Windows
```

### Services Won't Start

**Solution:** Check logs and run diagnostics

```bash
# View all logs
baseboards logs

# Run diagnostics
baseboards doctor

# Try restarting
baseboards down
baseboards up
```

### API Keys Not Working

**Symptoms:** Generators fail with authentication errors

**Solution:**

1. Verify keys are correct in `api/.env`
2. Check the JSON format is valid (use a JSON validator)
3. Restart services after editing `.env`

```bash
# Example correct format
BOARDS_GENERATOR_API_KEYS={"REPLICATE_API_KEY":"r8_xxxxx"}

# Example incorrect format (missing quotes)
BOARDS_GENERATOR_API_KEYS={REPLICATE_API_KEY:r8_xxxxx}  # ❌ Wrong
```

### Worker Not Processing Jobs

**Symptoms:** Jobs stuck in "pending" status

**Solution:** Check worker logs and restart

```bash
# Check worker logs
baseboards logs worker

# Restart worker
docker compose restart worker

# Full restart
baseboards down
baseboards up
```

### Database Connection Errors

**Solution:** Reset database

```bash
# Stop services and remove volumes
baseboards down --volumes

# Start fresh
baseboards up
```

**Warning:** This will delete all data (boards, artifacts, etc.)

### Disk Space Issues

**Solution:** Clean up old images and containers

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Or use baseboards clean
baseboards clean --hard
```

## Production Deployment

For production use, see the [Deployment Guide](../deployment/overview) for:

- Setting up HTTPS with reverse proxy
- Configuring authentication
- Using external databases
- Setting up monitoring and logging
- Scaling workers for higher throughput

## Next Steps

- 📘 **[Baseboards Overview](../baseboards/overview)** - Learn more about Baseboards
- 🎨 **[Generators Guide](../generators/getting-started)** - Configure AI generators
- 🔐 **[Authentication Setup](../auth/overview)** - Add user authentication
- 🚀 **[Deployment Guide](../deployment/overview)** - Deploy to production

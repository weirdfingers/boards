---
sidebar_position: 1
---

# Deployment Overview

Deploy Boards to production with various hosting options and configurations. This section covers everything you need to run Boards in a production environment.

## Deployment Components

A complete Boards deployment consists of:

| Component | Description | Required |
|-----------|-------------|----------|
| **API** | GraphQL API server (uvicorn) | Yes |
| **Worker** | Background job processor | Yes |
| **PostgreSQL** | Database for persistent data | Yes |
| **Redis** | Job queue and caching | Yes |
| **Frontend** | Web application (Next.js) | Optional |
| **Storage** | Object storage for artifacts | Yes |

## Quick Start Paths

Choose your deployment approach:

### Development / Single Server

Use Docker Compose for the simplest setup:

```bash
# Using the CLI
npx @weirdfingers/baseboards

# Or manual Docker Compose
docker compose up -d
```

See [Docker Deployment](./docker.md) for details.

### Production / Scalable

For production workloads:

1. **Kubernetes** - Full control with K8s manifests → [Kubernetes Guide](./kubernetes.md)
2. **Cloud Platform** - Managed infrastructure:
   - [Google Cloud Run](./cloud/cloud-run.md) - Serverless containers
   - [AWS Elastic Beanstalk](./cloud/elastic-beanstalk.md) - Managed containers
   - [Railway](./cloud/railway.md) - Simple PaaS
   - [Render](./cloud/render.md) - Unified cloud platform
   - [Fly.io](./cloud/fly-io.md) - Edge deployment

## Configuration Checklist

Before deploying, you'll need to configure:

### 1. Database

Choose your PostgreSQL provider:

| Option | Best For | Guide |
|--------|----------|-------|
| Self-hosted | Single server, dev | [Standalone PostgreSQL](./database/standalone.md) |
| Supabase | Full-stack Supabase | [Supabase](./database/supabase.md) |
| AWS RDS | AWS deployments | [AWS RDS](./database/aws-rds.md) |
| Cloud SQL | GCP deployments | [Cloud SQL](./database/cloud-sql.md) |
| Azure | Azure deployments | [Azure Database](./database/azure-postgres.md) |
| Neon | Serverless/edge | [Neon](./database/neon.md) |

See [Managed PostgreSQL](./database/managed-postgresql.md) for general guidance.

### 2. Storage

Choose your object storage provider:

| Provider | Best For |
|----------|----------|
| Local | Development only |
| S3 | AWS, S3-compatible services |
| GCS | Google Cloud |
| Supabase | When using Supabase |

See [Storage Configuration](./storage.md) for setup.

### 3. Authentication

Choose your auth provider:

| Provider | Best For |
|----------|----------|
| JWT | Self-managed auth |
| Supabase | Supabase users |
| Clerk | Quick setup |
| Auth0 | Enterprise |
| OIDC | Generic providers |

See [Authentication](./authentication.md) for setup.

### 4. Environment & Secrets

Configure environment variables and secrets:

- Database connection URL
- Redis connection URL
- Generator API keys
- Auth provider credentials
- Storage credentials

See [Configuration Reference](./configuration.md) for all variables.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                       Your Application                       │
│  ┌─────────────────┐         ┌─────────────────────────┐    │
│  │    Frontend     │         │     Load Balancer       │    │
│  │   (Next.js)     │────────▶│    (nginx/Caddy/ALB)    │    │
│  └─────────────────┘         └───────────┬─────────────┘    │
│                                          │                   │
│                              ┌───────────┴───────────┐      │
│                              │                       │      │
│                        ┌─────▼─────┐          ┌──────▼─────┐│
│                        │    API    │          │   Worker   ││
│                        │ (uvicorn) │          │  (boards-  ││
│                        │           │          │   worker)  ││
│                        └─────┬─────┘          └──────┬─────┘│
│                              │                       │      │
│          ┌───────────────────┼───────────────────────┤      │
│          │                   │                       │      │
│    ┌─────▼─────┐       ┌─────▼─────┐          ┌─────▼─────┐ │
│    │ PostgreSQL │       │   Redis   │          │  Storage  │ │
│    │           │       │           │          │ (S3/GCS)  │ │
│    └───────────┘       └───────────┘          └───────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Pre-built Images

Boards publishes pre-built Docker images:

**Backend** (API + Worker):
- GHCR: `ghcr.io/weirdfingers/boards-backend:latest`
- Docker Hub: `cdiddy/weirdfingers-boards-backend:latest`

**Frontend**: Requires custom build (see [Frontend Deployment](./frontend.md))

## Security Checklist

Before going to production:

- [ ] HTTPS enabled with valid certificates
- [ ] Auth provider configured (not `none`)
- [ ] Database connections encrypted (SSL)
- [ ] Secrets stored securely (not in code)
- [ ] CORS origins restricted
- [ ] API rate limiting enabled
- [ ] Regular backups configured
- [ ] Monitoring and alerting set up

## Documentation Structure

| Section | Content |
|---------|---------|
| [Docker](./docker.md) | Docker Compose deployment |
| [Kubernetes](./kubernetes.md) | K8s manifests |
| [Monitoring](./monitoring.md) | Logging, health checks, metrics |
| [Configuration](./configuration.md) | Environment variables reference |
| [Storage](./storage.md) | Object storage setup |
| [Authentication](./authentication.md) | Auth provider configuration |
| [Frontend](./frontend.md) | Web application deployment |
| [Database](./database/) | PostgreSQL setup guides |
| [Cloud Platforms](./cloud/) | Platform-specific guides |

## Getting Help

- Check the specific guide for your deployment target
- Review [Configuration Reference](./configuration.md) for environment variables
- See [Monitoring](./monitoring.md) for debugging tips

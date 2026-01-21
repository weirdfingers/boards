---
title: Upgrades & Migrations
description: How to upgrade Boards and run database migrations.
sidebar_position: 9
---

# Upgrades & Migrations

This guide covers upgrading Boards to newer versions, including running database migrations.

## Upgrade Process Overview

Upgrading Boards involves:

1. **Check release notes** for breaking changes
2. **Backup your database** before upgrading
3. **Run database migrations** (if required)
4. **Update container images** for API and worker
5. **Verify the deployment** is healthy

:::warning Important
Always run database migrations **before** deploying new application versions. The new code may depend on schema changes that migrations provide.
:::

## Database Migrations

Boards uses [Alembic](https://alembic.sqlalchemy.org/) for database migrations. Migrations are included in the backend image and can be run using the `boards-migrate` CLI.

### Migration Commands

```bash
# Upgrade to latest version
boards-migrate upgrade head

# Upgrade to a specific revision
boards-migrate upgrade abc123

# Show current database revision
boards-migrate current

# Show migration history
boards-migrate history

# Downgrade one revision (for rollbacks)
boards-migrate downgrade -1

# Downgrade to a specific revision
boards-migrate downgrade abc123
```

### Running Migrations

#### Docker Compose

Run migrations before updating services:

```bash
# Pull new images
docker compose pull

# Run migrations using the new image
docker compose run --rm api boards-migrate upgrade head

# Then update services
docker compose up -d
```

Or as a one-liner:

```bash
docker compose pull && \
docker compose run --rm api boards-migrate upgrade head && \
docker compose up -d
```

#### Kubernetes

**Option 1: Job (Recommended)**

Create a migration job:

```yaml
# migration-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: boards-migrate-v1-2-0
  namespace: boards
spec:
  ttlSecondsAfterFinished: 3600
  template:
    spec:
      containers:
        - name: migrate
          image: ghcr.io/weirdfingers/boards-backend:v1.2.0
          command: ["boards-migrate", "upgrade", "head"]
          env:
            - name: BOARDS_DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: boards-secrets
                  key: database-url
      restartPolicy: Never
  backoffLimit: 1
```

Run the migration:

```bash
kubectl apply -f migration-job.yaml
kubectl wait --for=condition=complete job/boards-migrate-v1-2-0 -n boards --timeout=300s
kubectl logs job/boards-migrate-v1-2-0 -n boards
```

Then update deployments:

```bash
kubectl set image deployment/boards-api api=ghcr.io/weirdfingers/boards-backend:v1.2.0 -n boards
kubectl set image deployment/boards-worker worker=ghcr.io/weirdfingers/boards-backend:v1.2.0 -n boards
```

**Option 2: Init Container**

Add an init container to run migrations on deployment:

```yaml
spec:
  initContainers:
    - name: migrate
      image: ghcr.io/weirdfingers/boards-backend:v1.2.0
      command: ["boards-migrate", "upgrade", "head"]
      env:
        - name: BOARDS_DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: boards-secrets
              key: database-url
```

:::note
Init containers run on every pod start. Alembic handles this gracefully—if migrations are already applied, it's a no-op. However, this adds startup latency.
:::

#### Cloud Platforms

**Cloud Run:**

```bash
# Run migration as a one-off job
gcloud run jobs create boards-migrate \
  --image ghcr.io/weirdfingers/boards-backend:v1.2.0 \
  --command "boards-migrate,upgrade,head" \
  --set-secrets "BOARDS_DATABASE_URL=boards-database-url:latest" \
  --region us-central1

gcloud run jobs execute boards-migrate --region us-central1 --wait

# Then update services
gcloud run services update boards-api --image ghcr.io/weirdfingers/boards-backend:v1.2.0
gcloud run services update boards-worker --image ghcr.io/weirdfingers/boards-backend:v1.2.0
```

**Railway:**

```bash
# SSH into the API service and run migrations
railway run boards-migrate upgrade head --service boards-api

# Then trigger a redeploy with the new image
```

**Fly.io:**

```bash
# Run migration via SSH
fly ssh console --app boards-api -C "boards-migrate upgrade head"

# Then deploy new version
fly deploy --app boards-api
fly deploy --app boards-worker
```

**Render:**

```bash
# Use the shell to run migrations
render shell boards-api
boards-migrate upgrade head

# Then trigger redeploy from dashboard or CLI
```

## Pre-Upgrade Checklist

Before upgrading:

- [ ] Read the release notes for the target version
- [ ] Check for breaking changes or required configuration updates
- [ ] **Backup your database**
- [ ] Test the upgrade in a staging environment
- [ ] Plan for rollback if needed
- [ ] Schedule maintenance window if required

### Backup Database

**Docker Compose:**

```bash
docker compose exec db pg_dump -U boards boards > backup-$(date +%Y%m%d-%H%M%S).sql
```

**Kubernetes:**

```bash
kubectl exec -n boards postgres-0 -- pg_dump -U boards boards > backup.sql
```

**Managed databases** (RDS, Cloud SQL, etc.): Create a snapshot via the provider's console or CLI.

## Rollback Procedures

If an upgrade fails:

### 1. Rollback Application

**Docker Compose:**

```bash
# Edit compose.yaml to use previous version
# Or set BACKEND_VERSION in .env
BACKEND_VERSION=v1.1.0 docker compose up -d
```

**Kubernetes:**

```bash
kubectl rollout undo deployment/boards-api -n boards
kubectl rollout undo deployment/boards-worker -n boards
```

### 2. Rollback Database (If Needed)

Only rollback the database if the migration itself caused issues:

```bash
# Downgrade one migration
boards-migrate downgrade -1

# Or restore from backup
psql -U boards boards < backup.sql
```

:::danger
Database rollbacks can cause data loss if the migration added columns that now contain data. Always prefer forward-fixes over rollbacks when possible.
:::

## Zero-Downtime Upgrades

For zero-downtime upgrades:

### 1. Ensure Migration Compatibility

Migrations should be **backwards compatible**:
- Add columns as nullable or with defaults
- Don't remove columns until the next release
- Don't rename columns; add new, migrate data, remove old

### 2. Rolling Update Strategy

**Kubernetes:**

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
```

**Docker Compose with multiple replicas:**

```bash
# Update one at a time
docker compose up -d --no-deps --scale api=2 api
docker compose up -d --no-deps --scale api=1 api
```

### 3. Blue-Green Deployment

1. Deploy new version alongside old
2. Run migrations
3. Switch traffic to new version
4. Tear down old version

## Version Compatibility

### Checking Versions

```bash
# Check API version
curl https://api.example.com/health
# Returns: {"status": "healthy", "version": "1.2.0"}

# Check database migration version
boards-migrate current
```

### Skipping Versions

You can upgrade across multiple versions—Alembic will run all pending migrations in order:

```bash
# From v1.0.0 to v1.3.0
boards-migrate upgrade head
# Runs: v1.0.0 → v1.1.0 → v1.2.0 → v1.3.0 migrations
```

## Troubleshooting

### Migration Fails

1. Check the error message in logs
2. Verify database connectivity
3. Check if migration was partially applied:
   ```bash
   boards-migrate current
   ```
4. Fix the issue and retry, or rollback

### "Revision Not Found"

The migration revision doesn't exist in the new image. Ensure you're using the correct image version.

### Database Locked

Another migration or connection is holding a lock:

```sql
-- Find blocking queries
SELECT pid, query, state FROM pg_stat_activity WHERE state != 'idle';

-- Terminate if necessary (careful!)
SELECT pg_terminate_backend(pid);
```

### Data Migration Takes Too Long

For large tables:
1. Run migrations during low-traffic periods
2. Consider breaking into smaller migrations
3. Add indexes concurrently: `CREATE INDEX CONCURRENTLY`

## Automation

### CI/CD Pipeline Example

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    steps:
      - name: Backup database
        run: |
          # Create backup via your provider's CLI

      - name: Run migrations
        run: |
          docker run --rm \
            -e BOARDS_DATABASE_URL=${{ secrets.DATABASE_URL }} \
            ghcr.io/weirdfingers/boards-backend:${{ github.ref_name }} \
            boards-migrate upgrade head

      - name: Deploy
        run: |
          # Deploy to your platform
```

## Next Steps

- [Docker Deployment](./docker.md) - Upgrade Docker Compose deployments
- [Kubernetes Deployment](./kubernetes.md) - Upgrade K8s deployments
- [Monitoring](./monitoring.md) - Monitor upgrade health

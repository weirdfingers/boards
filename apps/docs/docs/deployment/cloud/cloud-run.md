---
title: Google Cloud Run
description: Deploy Boards to Google Cloud Run.
sidebar_position: 1
---

# Google Cloud Run

[Cloud Run](https://cloud.google.com/run) is Google Cloud's serverless container platform. It automatically scales based on traffic and you only pay for what you use.

## Architecture

```mermaid
flowchart TB
    subgraph CloudRun["Cloud Run"]
        APIService["API Service<br/>(auto-scale)"]
        WorkerService["Worker Service<br/>(min 1 replica)"]
    end

    APIService --> CloudSQL["Cloud SQL<br/>(Postgres)"]
    APIService --> Memorystore["Memorystore<br/>(Redis)"]
    WorkerService --> CloudSQL
    WorkerService --> Memorystore
```

## Prerequisites

- Google Cloud project with billing enabled
- `gcloud` CLI installed and configured
- Cloud SQL PostgreSQL instance ([setup guide](../database/cloud-sql.md))
- Memorystore Redis instance (or Upstash Redis)

## Deploy API Service

### 1. Deploy from Pre-built Image

```bash
gcloud run deploy boards-api \
  --image ghcr.io/weirdfingers/boards-backend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8800 \
  --cpu 1 \
  --memory 512Mi \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars "BOARDS_LOG_FORMAT=json,BOARDS_LOG_LEVEL=info" \
  --set-secrets "BOARDS_DATABASE_URL=boards-database-url:latest,BOARDS_REDIS_URL=boards-redis-url:latest,BOARDS_GENERATOR_API_KEYS=boards-api-keys:latest"
```

### 2. Configure Cloud SQL Connection

Add the Cloud SQL connection:

```bash
gcloud run services update boards-api \
  --add-cloudsql-instances PROJECT:REGION:INSTANCE_NAME \
  --region us-central1
```

Update the database URL to use the Unix socket:

```bash
# Store in Secret Manager
echo -n "postgresql://user:pass@/boards?host=/cloudsql/PROJECT:REGION:INSTANCE_NAME" | \
  gcloud secrets create boards-database-url --data-file=-
```

### 3. Mount Config Files

Create configs as secrets:

```bash
# Create generators config secret
gcloud secrets create boards-generators-config \
  --data-file=config/generators.yaml

# Create storage config secret
gcloud secrets create boards-storage-config \
  --data-file=config/storage_config.yaml
```

Mount as volumes:

```bash
gcloud run services update boards-api \
  --region us-central1 \
  --update-secrets="/app/config/generators.yaml=boards-generators-config:latest" \
  --update-secrets="/app/config/storage_config.yaml=boards-storage-config:latest" \
  --set-env-vars "BOARDS_GENERATORS_CONFIG_PATH=/app/config/generators.yaml,BOARDS_STORAGE_CONFIG_PATH=/app/config/storage_config.yaml"
```

## Deploy Worker Service

The worker needs to run continuously, so configure minimum instances:

```bash
gcloud run deploy boards-worker \
  --image ghcr.io/weirdfingers/boards-backend:latest \
  --platform managed \
  --region us-central1 \
  --no-allow-unauthenticated \
  --cpu 2 \
  --memory 1Gi \
  --min-instances 1 \
  --max-instances 5 \
  --command "boards-worker" \
  --args "--log-level,info,--processes,1,--threads,1" \
  --set-env-vars "BOARDS_LOG_FORMAT=json,BOARDS_INTERNAL_API_URL=https://boards-api-xxxxx-uc.a.run.app" \
  --set-secrets "BOARDS_DATABASE_URL=boards-database-url:latest,BOARDS_REDIS_URL=boards-redis-url:latest,BOARDS_GENERATOR_API_KEYS=boards-api-keys:latest" \
  --add-cloudsql-instances PROJECT:REGION:INSTANCE_NAME
```

:::note
Workers need `--min-instances 1` to ensure jobs are processed. Cloud Run Jobs is an alternative for batch processing.
:::

## Redis Options

### Option 1: Memorystore (VPC Required)

Create a Memorystore instance:

```bash
gcloud redis instances create boards-redis \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_7_0
```

Connect Cloud Run to VPC:

```bash
# Create VPC connector
gcloud compute networks vpc-access connectors create boards-connector \
  --region us-central1 \
  --subnet default

# Update services to use connector
gcloud run services update boards-api \
  --vpc-connector boards-connector \
  --region us-central1
```

### Option 2: Upstash Redis (Simpler)

[Upstash](https://upstash.com) provides serverless Redis accessible without VPC:

1. Create a Redis database at upstash.com
2. Use the provided connection URL:

```bash
echo -n "rediss://default:xxxxx@us1-xxxxx.upstash.io:6379" | \
  gcloud secrets create boards-redis-url --data-file=-
```

## Secret Manager Setup

Store all sensitive values in Secret Manager:

```bash
# Database URL
echo -n "postgresql://..." | gcloud secrets create boards-database-url --data-file=-

# Redis URL
echo -n "redis://..." | gcloud secrets create boards-redis-url --data-file=-

# Generator API keys
echo -n '{"fal": "key", "openai": "key"}' | gcloud secrets create boards-api-keys --data-file=-

# Grant access to Cloud Run service account
gcloud secrets add-iam-policy-binding boards-database-url \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Deploy Frontend

Build and deploy the frontend:

```bash
# Build frontend image
gcloud builds submit \
  --tag gcr.io/PROJECT/boards-frontend \
  --build-arg NEXT_PUBLIC_API_URL=https://boards-api-xxxxx-uc.a.run.app \
  --build-arg NEXT_PUBLIC_GRAPHQL_URL=https://boards-api-xxxxx-uc.a.run.app/graphql

# Deploy to Cloud Run
gcloud run deploy boards-frontend \
  --image gcr.io/PROJECT/boards-frontend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 3000
```

## Custom Domain

Map a custom domain:

```bash
gcloud run domain-mappings create \
  --service boards-api \
  --domain api.boards.example.com \
  --region us-central1
```

Follow the DNS verification instructions provided.

## CI/CD with Cloud Build

Create `cloudbuild.yaml`:

```yaml
steps:
  # Deploy API
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'boards-api'
      - '--image'
      - 'ghcr.io/weirdfingers/boards-backend:${_VERSION}'
      - '--region'
      - 'us-central1'

  # Deploy Worker
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'boards-worker'
      - '--image'
      - 'ghcr.io/weirdfingers/boards-backend:${_VERSION}'
      - '--region'
      - 'us-central1'

substitutions:
  _VERSION: latest
```

Trigger on new releases:

```bash
gcloud builds triggers create github \
  --repo-name=your-repo \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

## Monitoring

### Cloud Logging

View logs:

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=boards-api" --limit 100
```

### Cloud Monitoring

Set up alerts:

```bash
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Boards API Errors" \
  --condition-display-name="Error rate > 5%" \
  --condition-filter='resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_count" AND metric.labels.response_code_class="5xx"'
```

## Cost Optimization

- **API**: Set `--min-instances 0` to scale to zero when idle
- **Worker**: Consider Cloud Run Jobs for batch processing
- **Redis**: Use Upstash pay-per-request for low traffic

## Troubleshooting

### Cold Start Latency

If cold starts are too slow:

```bash
gcloud run services update boards-api \
  --min-instances 1 \
  --region us-central1
```

### Cloud SQL Connection Errors

1. Verify Cloud SQL instance name is correct
2. Check service account has `cloudsql.client` role
3. Ensure Cloud SQL Admin API is enabled

### Worker Not Processing Jobs

1. Verify `--min-instances 1` for worker
2. Check Redis connectivity
3. Review worker logs in Cloud Logging

## Next Steps

- [Cloud SQL Setup](../database/cloud-sql.md) - Database configuration
- [GCS Storage](../storage.md) - Configure Cloud Storage
- [Monitoring](../monitoring.md) - Set up observability

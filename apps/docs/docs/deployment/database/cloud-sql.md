---
title: Google Cloud SQL
description: Use Google Cloud SQL PostgreSQL with Boards.
sidebar_position: 5
---

# Google Cloud SQL

[Cloud SQL](https://cloud.google.com/sql) is Google Cloud's managed PostgreSQL service with automatic replication, backups, and scaling.

## Creating a Cloud SQL Instance

### Via Console

1. Go to **Cloud SQL** > **Create instance** > **PostgreSQL**
2. Configure:
   - **Instance ID**: `boards-db`
   - **Password**: Set root password
   - **Database version**: PostgreSQL 16
   - **Region**: Match your application region
   - **Machine type**: Start with `db-f1-micro` for testing
3. Under **Connections**:
   - Enable **Private IP** (recommended)
   - Or enable **Public IP** with authorized networks
4. Click **Create instance**

### Via gcloud CLI

```bash
gcloud sql instances create boards-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=your-secure-password \
  --network=default \
  --no-assign-ip
```

Create a database:

```bash
gcloud sql databases create boards --instance=boards-db
```

Create a user:

```bash
gcloud sql users create boards_user \
  --instance=boards-db \
  --password=user-password
```

## Connection Methods

### Cloud SQL Auth Proxy (Recommended)

The Auth Proxy provides secure connections without managing SSL certificates:

```bash
# Download the proxy
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy

# Run the proxy
./cloud-sql-proxy --port 5432 PROJECT_ID:REGION:boards-db
```

Connect via localhost:

```bash
BOARDS_DATABASE_URL=postgresql://boards_user:password@127.0.0.1:5432/boards
```

### In Kubernetes with Sidecar

Add the Auth Proxy as a sidecar container:

```yaml
spec:
  containers:
    - name: api
      image: ghcr.io/weirdfingers/boards-backend:latest
      env:
        - name: BOARDS_DATABASE_URL
          value: postgresql://boards_user:password@127.0.0.1:5432/boards
    - name: cloud-sql-proxy
      image: gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.8.0
      args:
        - "--structured-logs"
        - "--port=5432"
        - "PROJECT_ID:REGION:boards-db"
      securityContext:
        runAsNonRoot: true
```

### Direct Private IP Connection

If using Private IP within the same VPC:

```bash
BOARDS_DATABASE_URL=postgresql://boards_user:password@PRIVATE_IP:5432/boards?sslmode=require
```

Get the private IP:

```bash
gcloud sql instances describe boards-db --format="value(ipAddresses[0].ipAddress)"
```

### Public IP with SSL

For public IP connections, download SSL certificates:

```bash
gcloud sql ssl client-certs create boards-client \
  --instance=boards-db \
  --cert=client-cert.pem \
  --key=client-key.pem

gcloud sql instances describe boards-db \
  --format="value(serverCaCert.cert)" > server-ca.pem
```

Connect with SSL:

```bash
BOARDS_DATABASE_URL=postgresql://boards_user:password@PUBLIC_IP:5432/boards?sslmode=verify-full&sslcert=/path/to/client-cert.pem&sslkey=/path/to/client-key.pem&sslrootcert=/path/to/server-ca.pem
```

## Using Workload Identity

For GKE deployments, use Workload Identity instead of passwords:

1. Create a service account:

```bash
gcloud iam service-accounts create boards-sql-client
```

2. Grant Cloud SQL Client role:

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:boards-sql-client@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
```

3. Configure Workload Identity:

```bash
gcloud iam service-accounts add-iam-policy-binding \
  boards-sql-client@PROJECT_ID.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:PROJECT_ID.svc.id.goog[boards/boards-api]"
```

4. Annotate Kubernetes service account:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: boards-api
  namespace: boards
  annotations:
    iam.gke.io/gcp-service-account: boards-sql-client@PROJECT_ID.iam.gserviceaccount.com
```

## High Availability

Enable HA for automatic failover:

```bash
gcloud sql instances patch boards-db --availability-type=REGIONAL
```

This provides:
- Synchronous replication to standby
- Automatic failover (typically under 60 seconds)
- Same connection endpoint after failover

## Backups

### Automated Backups

Configure backup retention:

```bash
gcloud sql instances patch boards-db \
  --backup-start-time=02:00 \
  --retained-backups-count=7
```

### On-Demand Backups

```bash
gcloud sql backups create --instance=boards-db
```

### Point-in-Time Recovery

Enable and use PITR:

```bash
# Enable
gcloud sql instances patch boards-db --enable-point-in-time-recovery

# Restore
gcloud sql instances clone boards-db boards-db-restored \
  --point-in-time='2024-01-15T10:00:00Z'
```

## Monitoring

### Cloud Monitoring

Key metrics:
- `cloudsql.googleapis.com/database/cpu/utilization`
- `cloudsql.googleapis.com/database/memory/utilization`
- `cloudsql.googleapis.com/database/network/connections`
- `cloudsql.googleapis.com/database/disk/utilization`

### Query Insights

Enable Query Insights for query-level monitoring:

```bash
gcloud sql instances patch boards-db --insights-config-query-insights-enabled
```

## Pricing

| Machine Type | vCPU | RAM | Monthly (us-central1) |
|--------------|------|-----|----------------------|
| db-f1-micro | shared | 0.6 GB | ~$9 |
| db-g1-small | shared | 1.7 GB | ~$27 |
| db-custom-2-4096 | 2 | 4 GB | ~$75 |
| db-custom-4-8192 | 4 | 8 GB | ~$150 |

Additional costs:
- Storage: ~$0.17/GB/month (SSD)
- Backups: ~$0.08/GB/month
- HA: Doubles compute cost

## Next Steps

- [Cloud Run Deployment](../cloud/cloud-run.md) - Deploy Boards on Cloud Run
- [Storage with GCS](../storage.md) - Configure GCS storage

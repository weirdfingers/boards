---
title: Self-Hosted PostgreSQL
description: Run PostgreSQL alongside your Boards deployment.
sidebar_position: 1
---

# Self-Hosted PostgreSQL

Run PostgreSQL as a container alongside your Boards deployment. This approach works well for single-server deployments and development environments.

## Docker Compose

Include PostgreSQL in your `compose.yaml`:

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: boards
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: boards
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U boards -d boards"]
      interval: 5s
      timeout: 5s
      retries: 20
    networks:
      - internal

  api:
    # ... your api config
    environment:
      - BOARDS_DATABASE_URL=postgresql://boards:${POSTGRES_PASSWORD}@db:5432/boards
    depends_on:
      db:
        condition: service_healthy

volumes:
  db-data:
```

Set the password in your `.env`:

```bash
POSTGRES_PASSWORD=your-secure-password-here
```

## Kubernetes

For Kubernetes, consider using a managed PostgreSQL service instead. If you must run PostgreSQL in-cluster:

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: boards
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:16
          env:
            - name: POSTGRES_USER
              value: boards
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: boards-secrets
                  key: postgres-password
            - name: POSTGRES_DB
              value: boards
          ports:
            - containerPort: 5432
          volumeMounts:
            - name: postgres-data
              mountPath: /var/lib/postgresql/data
          readinessProbe:
            exec:
              command: ["pg_isready", "-U", "boards", "-d", "boards"]
            initialDelaySeconds: 5
            periodSeconds: 5
  volumeClaimTemplates:
    - metadata:
        name: postgres-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: boards
spec:
  ports:
    - port: 5432
  selector:
    app: postgres
```

:::warning
Running PostgreSQL in Kubernetes without proper backup and HA configuration is not recommended for production. Consider using a managed service like [AWS RDS](./aws-rds.md), [Cloud SQL](./cloud-sql.md), or [Supabase](./supabase.md).
:::

## Connection Configuration

Configure Boards to connect to PostgreSQL:

```bash
# Docker internal network
BOARDS_DATABASE_URL=postgresql://boards:password@db:5432/boards

# Kubernetes internal service
BOARDS_DATABASE_URL=postgresql://boards:password@postgres.boards.svc.cluster.local:5432/boards
```

## Production Considerations

### Backups

Set up regular backups with `pg_dump`:

```bash
# Docker Compose
docker compose exec db pg_dump -U boards boards > backup-$(date +%Y%m%d).sql

# Kubernetes
kubectl exec -n boards postgres-0 -- pg_dump -U boards boards > backup.sql
```

Automate with a cron job or Kubernetes CronJob:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: boards
spec:
  schedule: "0 2 * * *"  # Daily at 2am
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: postgres:16
              command:
                - /bin/sh
                - -c
                - pg_dump -h postgres -U boards boards | gzip > /backups/backup-$(date +%Y%m%d).sql.gz
              env:
                - name: PGPASSWORD
                  valueFrom:
                    secretKeyRef:
                      name: boards-secrets
                      key: postgres-password
              volumeMounts:
                - name: backups
                  mountPath: /backups
          restartPolicy: OnFailure
          volumes:
            - name: backups
              persistentVolumeClaim:
                claimName: backup-storage
```

### Performance Tuning

For production workloads, tune PostgreSQL settings:

```yaml
services:
  db:
    image: postgres:16
    command:
      - "postgres"
      - "-c"
      - "shared_buffers=256MB"
      - "-c"
      - "effective_cache_size=768MB"
      - "-c"
      - "maintenance_work_mem=64MB"
      - "-c"
      - "checkpoint_completion_target=0.9"
      - "-c"
      - "wal_buffers=16MB"
      - "-c"
      - "max_connections=100"
```

### Monitoring

Monitor PostgreSQL with these queries:

```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity;

-- Database size
SELECT pg_size_pretty(pg_database_size('boards'));

-- Slow queries (requires pg_stat_statements extension)
SELECT query, calls, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

## When to Use Managed PostgreSQL

Consider switching to a managed service when you need:

- **High availability** - Automatic failover and replication
- **Point-in-time recovery** - Restore to any moment
- **Automated backups** - Without managing backup infrastructure
- **Scaling** - Easy vertical and horizontal scaling
- **Monitoring** - Built-in metrics and alerting

See the managed database guides:
- [AWS RDS](./aws-rds.md)
- [Google Cloud SQL](./cloud-sql.md)
- [Azure Database for PostgreSQL](./azure-postgres.md)
- [Supabase](./supabase.md)
- [Neon](./neon.md)

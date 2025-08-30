---
sidebar_position: 1
---

# Deployment Overview

Deploy Boards to production with various hosting options and configurations.

## Deployment Options

### Docker Compose

The simplest deployment option using Docker containers:

```yaml
# docker-compose.prod.yml
services:
  api:
    build: ./packages/backend
    environment:
      - BOARDS_DATABASE_URL=postgresql://user:pass@db/boards
      - BOARDS_REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  web:
    build: ./apps/example-nextjs
    environment:
      - NEXT_PUBLIC_API_URL=http://api:8000
    depends_on:
      - api

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: boards
      POSTGRES_USER: boards
      POSTGRES_PASSWORD: your_secure_password

  redis:
    image: redis:7
```

### Kubernetes

For scalable production deployments:

```yaml
# k8s/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: boards-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: boards-api
  template:
    metadata:
      labels:
        app: boards-api
    spec:
      containers:
      - name: api
        image: your-registry/boards-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: BOARDS_DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: boards-secrets
              key: database-url
```

### Cloud Platforms

- **Vercel** - Frontend deployment with serverless functions
- **Railway** - Full-stack deployment with managed databases
- **AWS ECS** - Container orchestration with AWS services
- **Google Cloud Run** - Serverless container deployment

## Environment Configuration

### Production Environment Variables

```bash
# Database
BOARDS_DATABASE_URL=postgresql://user:pass@host:5432/boards

# Redis  
BOARDS_REDIS_URL=redis://host:6379/0

# Storage
BOARDS_STORAGE_PROVIDER=s3
BOARDS_STORAGE_S3_BUCKET=your-bucket
BOARDS_STORAGE_S3_REGION=us-east-1

# Authentication
BOARDS_AUTH_PROVIDER=supabase
BOARDS_AUTH_SUPABASE_URL=https://your-project.supabase.co
BOARDS_AUTH_SUPABASE_SERVICE_KEY=your_service_key

# Security
BOARDS_SECRET_KEY=your-secret-key-here
BOARDS_ALLOWED_ORIGINS=https://yourapp.com,https://www.yourapp.com
```

### SSL/TLS Configuration

Always use HTTPS in production:

```bash
# Let's Encrypt with Certbot
certbot --nginx -d yourapi.com
```

### Database Security

- Use connection pooling
- Enable SSL connections
- Regular backups
- Monitoring and alerting

## Performance Optimization

### Caching Strategy

```python
# Redis caching for frequently accessed data
BOARDS_CACHE_TTL=3600  # 1 hour
BOARDS_CACHE_PREFIX=boards:
```

### Database Optimization

```sql
-- Add indexes for common queries
CREATE INDEX CONCURRENTLY idx_generations_status_created 
ON generations(status, created_at);

-- Partition large tables
CREATE TABLE generations_2024 PARTITION OF generations
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

### CDN Integration

Use a CDN for static assets and generated content:

```bash
# CloudFlare, AWS CloudFront, or Vercel Edge Network
BOARDS_CDN_URL=https://cdn.yourapp.com
```

## Monitoring and Logging

### Health Checks

```python
# Built-in health check endpoint
GET /health

# Response
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "version": "1.0.0"
}
```

### Logging Configuration

```python
# Production logging
BOARDS_LOG_LEVEL=INFO
BOARDS_LOG_FORMAT=json
BOARDS_LOG_FILE=/var/log/boards/app.log
```

### Metrics and Alerting

- **Prometheus** - Metrics collection
- **Grafana** - Visualization
- **Sentry** - Error tracking
- **Datadog** - APM and monitoring

## Security Checklist

- [ ] HTTPS enabled with valid certificates
- [ ] Database connections encrypted
- [ ] API rate limiting enabled
- [ ] Input validation and sanitization
- [ ] Authentication tokens secured
- [ ] Regular security updates
- [ ] Backup and disaster recovery plan

## Next Steps

- **[Docker Deployment](./docker)** - Container-based deployment
- **[Kubernetes Guide](./kubernetes)** - Scalable orchestration  
- **[Monitoring Setup](./monitoring)** - Observability and alerting
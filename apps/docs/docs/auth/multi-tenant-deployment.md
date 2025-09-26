# Multi-Tenant Deployment Guide

This guide covers deployment configurations for multi-tenant Boards applications across different scenarios.

## Deployment Scenarios

### 1. Development Environment

Simple setup for local development and testing.

**Configuration:**

```bash
# .env.development
BOARDS_ENVIRONMENT=development
BOARDS_DEBUG=true
BOARDS_AUTH_PROVIDER=none
BOARDS_MULTI_TENANT_MODE=false
BOARDS_DATABASE_URL=postgresql://boards:boards_dev@localhost:5433/boards_dev
BOARDS_REDIS_URL=redis://localhost:6380
```

**Setup:**

```bash
# Start services
docker-compose up -d postgres redis

# Run migrations
alembic upgrade head

# Start server
python -m boards.cli serve --reload
```

The default tenant is created automatically.

### 2. Single-Tenant Production

Production deployment serving one organization.

**Configuration:**

```bash
# .env.production
BOARDS_ENVIRONMENT=production
BOARDS_DEBUG=false
BOARDS_MULTI_TENANT_MODE=false

# Authentication
BOARDS_AUTH_PROVIDER=jwt
BOARDS_JWT_SECRET=your-super-secure-secret-key
BOARDS_JWT_ALGORITHM=HS256

# Custom tenant branding
BOARDS_TENANT_NAME="Your Company Name"
BOARDS_TENANT_SLUG="your-company"

# Database
BOARDS_DATABASE_URL=postgresql://user:password@prod-db:5432/boards
BOARDS_REDIS_URL=redis://prod-redis:6379

# API settings
BOARDS_API_HOST=0.0.0.0
BOARDS_API_PORT=8000
BOARDS_CORS_ORIGINS=https://boards.yourcompany.com,https://yourcompany.com

# Frontend integration
BOARDS_FRONTEND_BASE_URL=https://boards.yourcompany.com
```

**Docker Deployment:**

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN pip install -e .

EXPOSE 8000
CMD ["python", "-m", "boards.cli", "serve", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  boards-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - BOARDS_ENVIRONMENT=production
      - BOARDS_MULTI_TENANT_MODE=false
      - BOARDS_AUTH_PROVIDER=jwt
      - BOARDS_JWT_SECRET=${JWT_SECRET}
      - BOARDS_DATABASE_URL=postgresql://boards:${DB_PASSWORD}@db:5432/boards
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=boards
      - POSTGRES_USER=boards
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### 3. Multi-Tenant SaaS

SaaS platform with self-service tenant registration.

**Configuration:**

```bash
# .env.saas
BOARDS_ENVIRONMENT=production
BOARDS_DEBUG=false
BOARDS_MULTI_TENANT_MODE=true

# Authentication with OIDC
BOARDS_AUTH_PROVIDER=oidc
BOARDS_OIDC_ISSUER=https://auth.yourservice.com
BOARDS_OIDC_CLIENT_ID=your-client-id
BOARDS_OIDC_CLIENT_SECRET=your-client-secret

# JWT tenant extraction
BOARDS_JWT_TENANT_CLAIM=organization

# Self-service registration
BOARDS_TENANT_REGISTRATION_REQUIRES_APPROVAL=false
BOARDS_MAX_TENANTS_PER_USER=3

# Frontend integration
BOARDS_FRONTEND_BASE_URL=https://app.boards.com

# Database and infrastructure
BOARDS_DATABASE_URL=postgresql://boards:password@db-cluster:5432/boards
BOARDS_REDIS_URL=redis://redis-cluster:6379

# Rate limiting and scaling
BOARDS_API_WORKERS=4
```

**Kubernetes Deployment:**

```yaml
# k8s/deployment.yaml
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
      - name: boards-api
        image: boards/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: BOARDS_MULTI_TENANT_MODE
          value: "true"
        - name: BOARDS_AUTH_PROVIDER
          value: "oidc"
        - name: BOARDS_JWT_TENANT_CLAIM
          value: "organization"
        - name: BOARDS_DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: boards-secrets
              key: database-url
        - name: BOARDS_OIDC_CLIENT_SECRET
          valueFrom:
            secretKeyRef:
              name: boards-secrets
              key: oidc-client-secret
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: boards-api-service
spec:
  selector:
    app: boards-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: boards-api-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt
spec:
  tls:
  - hosts:
    - api.boards.com
    secretName: boards-api-tls
  rules:
  - host: api.boards.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: boards-api-service
            port:
              number: 80
```

### 4. Enterprise Multi-Tenant

Enterprise deployment with approval workflows and domain restrictions.

**Configuration:**

```bash
# .env.enterprise
BOARDS_ENVIRONMENT=production
BOARDS_DEBUG=false
BOARDS_MULTI_TENANT_MODE=true

# Enterprise authentication
BOARDS_AUTH_PROVIDER=oidc
BOARDS_OIDC_ISSUER=https://sso.enterprise.com
BOARDS_JWT_TENANT_CLAIM=org_slug

# Restricted registration
BOARDS_TENANT_REGISTRATION_REQUIRES_APPROVAL=true
BOARDS_TENANT_REGISTRATION_ALLOWED_DOMAINS=client1.com,client2.com,partner.org
BOARDS_MAX_TENANTS_PER_USER=1

# Enhanced security
BOARDS_JWT_ALGORITHM=RS256
BOARDS_JWT_PUBLIC_KEY_URL=https://sso.enterprise.com/.well-known/jwks.json

# Enterprise features
BOARDS_ENABLE_AUDIT_LOGGING=true
BOARDS_ENABLE_ADVANCED_METRICS=true
```

## Database Configuration

### Single Database with Tenant Isolation

**Recommended for most deployments:**

```bash
# Single PostgreSQL instance with tenant_id filtering
BOARDS_DATABASE_URL=postgresql://boards:password@db:5432/boards_prod
```

Pros:
- Simpler management
- Cost-effective
- Built-in backup/recovery
- Query optimization across tenants

Cons:
- Requires careful query filtering
- Shared resource limits
- Cross-tenant data leak risk

### Database Per Tenant

**For high-isolation requirements:**

```python
# Custom database URL resolver
def get_database_url(tenant_slug: str = None) -> str:
    if tenant_slug and settings.multi_tenant_mode:
        return f"postgresql://boards:password@db:5432/tenant_{tenant_slug}"
    return settings.database_url
```

Pros:
- Complete data isolation
- Independent scaling
- Tenant-specific backups

Cons:
- Complex management
- Higher costs
- Migration complexity

## Authentication Provider Configuration

### JWT Configuration

```bash
# Symmetric key (HS256)
BOARDS_JWT_SECRET=your-256-bit-secret
BOARDS_JWT_ALGORITHM=HS256

# Asymmetric key (RS256) - recommended for production
BOARDS_JWT_ALGORITHM=RS256
BOARDS_JWT_PUBLIC_KEY_URL=https://auth.yourservice.com/.well-known/jwks.json
```

**JWT Token Structure:**

```json
{
  "sub": "user123",
  "iss": "https://auth.yourservice.com",
  "aud": "boards-api",
  "exp": 1640995200,
  "iat": 1640991600,
  "organization": "acme-corp",
  "email": "user@acme-corp.com"
}
```

### OIDC Configuration

```bash
BOARDS_AUTH_PROVIDER=oidc
BOARDS_OIDC_ISSUER=https://accounts.google.com
BOARDS_OIDC_CLIENT_ID=your-client-id
BOARDS_OIDC_CLIENT_SECRET=your-client-secret
BOARDS_OIDC_AUDIENCE=boards-api
```

### Multiple Provider Support

```python
# Custom auth adapter factory
class MultiProviderAuthAdapter:
    def __init__(self):
        self.providers = {
            'internal': JWTAuthAdapter(settings.jwt_secret),
            'google': OIDCAdapter('https://accounts.google.com', settings.google_client_id),
            'enterprise': OIDCAdapter(settings.enterprise_oidc_issuer, settings.enterprise_client_id)
        }

    async def verify_token(self, token: str) -> Principal:
        # Try each provider in order
        for provider in self.providers.values():
            try:
                return await provider.verify_token(token)
            except AuthenticationError:
                continue
        raise AuthenticationError("Token not valid for any provider")
```

## Security Considerations

### Tenant Isolation

**Database Level:**

```sql
-- Row-level security (RLS)
ALTER TABLE boards ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON boards
  FOR ALL
  TO boards_app_role
  USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

**Application Level:**

```python
# Automatic tenant filtering
@strawberry.field
async def boards(self, info: Info) -> List[Board]:
    # Tenant context automatically applied
    tenant_id = info.context.auth.tenant_id
    return await get_tenant_boards(info.context.db, tenant_id)
```

### API Security

**Rate Limiting:**

```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.post("/api/tenants/register")
@app.dependency_overrides[RateLimiter] = RateLimiter(times=3, hours=1)
async def register_tenant():
    # Tenant registration limited to 3 per hour
    pass
```

**Input Validation:**

```python
# Tenant slug validation
@validator('slug')
def validate_slug(cls, v):
    if not re.match(r'^[a-z0-9-]+$', v):
        raise ValueError('Invalid slug format')
    if len(v) > 50:
        raise ValueError('Slug too long')
    return v
```

## Monitoring and Observability

### Key Metrics

```python
# Prometheus metrics
tenant_request_count = Counter(
    'boards_tenant_requests_total',
    'Total tenant requests',
    ['tenant_slug', 'endpoint']
)

tenant_isolation_violations = Counter(
    'boards_tenant_isolation_violations_total',
    'Tenant isolation violations',
    ['violation_type']
)
```

### Logging Configuration

```python
# Structured logging with tenant context
logger.info(
    "Request processed",
    tenant_slug=tenant_slug,
    user_id=user_id,
    endpoint=endpoint,
    response_time=response_time
)
```

### Health Checks

```python
@app.get("/health")
async def health_check():
    # Check tenant isolation health
    try:
        await validate_tenant_configuration()
        return {
            "status": "healthy",
            "multi_tenant_mode": settings.multi_tenant_mode,
            "tenant_count": await get_tenant_count(),
            "isolation_status": "ok"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
```

## Scaling Strategies

### Horizontal Scaling

**API Servers:**

```yaml
# k8s horizontal pod autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: boards-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: boards-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

**Database:**

```yaml
# PostgreSQL cluster with read replicas
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: boards-db
spec:
  instances: 3
  postgresql:
    parameters:
      max_connections: "500"
      shared_preload_libraries: "pg_stat_statements"

  bootstrap:
    initdb:
      database: boards
      owner: boards
```

### Vertical Scaling

**Resource Allocation:**

```yaml
# k8s resource requests and limits
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

### Caching Strategy

**Redis Configuration:**

```python
# Tenant-aware caching
class TenantCache:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def get(self, tenant_id: str, key: str):
        cache_key = f"tenant:{tenant_id}:{key}"
        return await self.redis.get(cache_key)

    async def set(self, tenant_id: str, key: str, value: str, ttl: int = 3600):
        cache_key = f"tenant:{tenant_id}:{key}"
        await self.redis.setex(cache_key, ttl, value)
```

## Backup and Disaster Recovery

### Database Backups

```bash
# Automated backup script
#!/bin/bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="boards_backup_${TIMESTAMP}.sql"

# Full database backup
pg_dump $BOARDS_DATABASE_URL > $BACKUP_FILE

# Tenant-specific backup
pg_dump $BOARDS_DATABASE_URL \
  --table="tenants" \
  --table="users" \
  --table="boards" \
  --where="tenant_id = '$TENANT_ID'" \
  > "tenant_${TENANT_SLUG}_${TIMESTAMP}.sql"

# Upload to S3
aws s3 cp $BACKUP_FILE s3://boards-backups/
```

### Configuration Backups

```bash
# Backup environment configuration
cat > config_backup.env << EOF
BOARDS_MULTI_TENANT_MODE=${BOARDS_MULTI_TENANT_MODE}
BOARDS_AUTH_PROVIDER=${BOARDS_AUTH_PROVIDER}
BOARDS_JWT_TENANT_CLAIM=${BOARDS_JWT_TENANT_CLAIM}
# ... other important settings
EOF
```

## Migration Scripts

### Single to Multi-Tenant Migration

```python
# migration_script.py
import asyncio
from boards.database.connection import get_async_session
from boards.config import settings

async def migrate_to_multitenant():
    """Migrate from single-tenant to multi-tenant mode."""
    async with get_async_session() as db:
        # 1. Verify current state
        print("Checking current configuration...")
        assert not settings.multi_tenant_mode, "Already in multi-tenant mode"

        # 2. Create backup
        print("Creating backup...")
        # Backup logic here

        # 3. Update configuration
        print("Updating configuration...")
        # Set BOARDS_MULTI_TENANT_MODE=true

        # 4. Restart application
        print("Restart the application with multi-tenant mode enabled")
        print("Your existing data will remain in the default tenant")

if __name__ == "__main__":
    asyncio.run(migrate_to_multitenant())
```

## Environment-Specific Configurations

### Development

```bash
# .env.development
BOARDS_DEBUG=true
BOARDS_AUTH_PROVIDER=none
BOARDS_MULTI_TENANT_MODE=false
BOARDS_LOG_LEVEL=debug
```

### Staging

```bash
# .env.staging
BOARDS_DEBUG=false
BOARDS_AUTH_PROVIDER=jwt
BOARDS_MULTI_TENANT_MODE=true
BOARDS_JWT_TENANT_CLAIM=org
BOARDS_TENANT_REGISTRATION_REQUIRES_APPROVAL=true
```

### Production

```bash
# .env.production
BOARDS_DEBUG=false
BOARDS_AUTH_PROVIDER=oidc
BOARDS_MULTI_TENANT_MODE=true
BOARDS_TENANT_REGISTRATION_REQUIRES_APPROVAL=true
BOARDS_TENANT_REGISTRATION_ALLOWED_DOMAINS=trusted1.com,trusted2.com
BOARDS_ENABLE_AUDIT_LOGGING=true
```

## Troubleshooting

### Common Deployment Issues

1. **Database Connection Failures**
   ```bash
   # Test database connectivity
   python -c "from boards.database.connection import get_async_session; print('DB OK')"
   ```

2. **JWT Verification Errors**
   ```bash
   # Validate JWT configuration
   curl -H "Authorization: Bearer $TEST_TOKEN" http://localhost:8000/health
   ```

3. **Tenant Isolation Issues**
   ```bash
   # Run isolation audit
   python -m boards.cli tenant audit --output-format json
   ```

## Security Checklist

- [ ] JWT secrets are properly configured
- [ ] Database credentials are secured
- [ ] HTTPS is enforced in production
- [ ] Rate limiting is configured
- [ ] Tenant isolation audits are scheduled
- [ ] Monitoring and alerting is set up
- [ ] Backup procedures are tested
- [ ] Access logs are retained
- [ ] Security headers are configured
- [ ] Input validation is comprehensive

## Next Steps

- Configure [monitoring dashboards](../deployment/monitoring.md)
- Set up [automated backups](../deployment/overview.md)
- Review [security best practices](./multi-tenant.md#security--isolation)
- Test [disaster recovery procedures](../deployment/overview.md)
- Configure [performance monitoring](../deployment/monitoring.md)
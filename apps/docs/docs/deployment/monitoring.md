---
title: Monitoring & Observability
description: Logging, health checks, and monitoring for Boards deployments.
sidebar_position: 4
---

# Monitoring & Observability

Monitor your Boards deployment with structured logging, health checks, and integration with external monitoring tools.

## Health Checks

### API Health Endpoint

The backend exposes a health check endpoint:

```
GET /health
```

Response:

```json
{
  "status": "healthy",
  "version": "0.9.10"
}
```

Use this endpoint for:
- Load balancer health checks
- Kubernetes readiness/liveness probes
- Uptime monitoring services

### Docker Compose

```yaml
services:
  api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8800/health"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 10s
```

### Kubernetes

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8800
  initialDelaySeconds: 10
  periodSeconds: 5
livenessProbe:
  httpGet:
    path: /health
    port: 8800
  initialDelaySeconds: 30
  periodSeconds: 10
```

## Structured Logging

Boards uses [structlog](https://www.structlog.org/) for structured logging with consistent formatting and context.

### Configuration

```bash
# Log level: debug, info, warning, error
BOARDS_LOG_LEVEL=info

# Format: console (human-readable) or json (structured)
BOARDS_LOG_FORMAT=json
```

### Log Format

**Console format** (development):

```
2024-01-15 10:30:45 [info     ] Request started    method=POST path=/graphql request_id=abc123
2024-01-15 10:30:45 [info     ] Request completed  method=POST path=/graphql status=200 duration_ms=45
```

**JSON format** (production):

```json
{"event": "Request started", "method": "POST", "path": "/graphql", "request_id": "abc123", "timestamp": "2024-01-15T10:30:45.123Z", "level": "info"}
{"event": "Request completed", "method": "POST", "path": "/graphql", "status": 200, "duration_ms": 45, "request_id": "abc123", "timestamp": "2024-01-15T10:30:45.168Z", "level": "info"}
```

### Request Context

Each request includes:
- `request_id`: Unique identifier for tracing
- `method`: HTTP method
- `path`: Request path
- `user_id`: Authenticated user (if available)
- `tenant_id`: Tenant identifier (if multi-tenant)

### Worker Logs

Worker processes log job execution:

```json
{"event": "Job started", "job_id": "job-123", "generator": "FluxProGenerator", "timestamp": "..."}
{"event": "Job completed", "job_id": "job-123", "duration_ms": 5432, "timestamp": "..."}
{"event": "Job failed", "job_id": "job-456", "error": "API rate limit exceeded", "timestamp": "..."}
```

## Log Aggregation

### Docker Compose

Forward logs to a file or aggregation service:

```yaml
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Or use a logging driver:

```yaml
services:
  api:
    logging:
      driver: "fluentd"
      options:
        fluentd-address: "localhost:24224"
        tag: "boards.api"
```

### Kubernetes

Logs are collected automatically by the cluster logging solution. Common options:

- **EFK Stack**: Elasticsearch, Fluentd, Kibana
- **Loki + Grafana**: Lightweight log aggregation
- **Cloud Logging**: AWS CloudWatch, GCP Cloud Logging, Azure Monitor

Example Fluentd config for parsing JSON logs:

```xml
<filter kubernetes.var.log.containers.boards-api**>
  @type parser
  key_name log
  <parse>
    @type json
  </parse>
</filter>
```

## External Monitoring Integration

### Prometheus (Metrics)

Boards doesn't expose Prometheus metrics natively, but you can add metrics collection:

**Option 1: Sidecar exporter**

Use a sidecar to expose metrics from logs:

```yaml
services:
  api:
    # ... api config

  metrics-exporter:
    image: google/mtail
    volumes:
      - api-logs:/var/log/boards:ro
      - ./mtail:/etc/mtail:ro
    ports:
      - "3903:3903"
```

**Option 2: Application-level metrics**

Add custom instrumentation in your application layer.

### Grafana

Visualize logs and metrics with Grafana:

1. Connect to your log aggregation (Loki, Elasticsearch)
2. Create dashboards for:
   - Request rate and latency
   - Error rates
   - Job queue depth and processing time
   - Database connection pool

### Sentry (Error Tracking)

Capture and track errors with Sentry:

```bash
# Add to your application
SENTRY_DSN=https://key@sentry.io/project
```

For the backend, configure in your application startup:

```python
import sentry_sdk
sentry_sdk.init(dsn=os.environ.get("SENTRY_DSN"))
```

### Datadog

For comprehensive APM with Datadog:

```yaml
services:
  datadog-agent:
    image: datadog/agent:latest
    environment:
      - DD_API_KEY=your-api-key
      - DD_LOGS_ENABLED=true
      - DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL=true
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /proc/:/host/proc/:ro
      - /sys/fs/cgroup/:/host/sys/fs/cgroup:ro

  api:
    labels:
      com.datadoghq.ad.logs: '[{"source": "python", "service": "boards-api"}]'
```

## Uptime Monitoring

### External Health Checks

Use uptime monitoring services to check your deployment:

- [UptimeRobot](https://uptimerobot.com)
- [Pingdom](https://www.pingdom.com)
- [Better Uptime](https://betteruptime.com)

Configure to check:
- `GET https://api.boards.example.com/health`
- Expected response: `200 OK`
- Check interval: 1-5 minutes

### Alerting

Set up alerts for:

| Condition | Severity | Action |
|-----------|----------|--------|
| Health check fails | Critical | Page on-call |
| Error rate > 5% | Warning | Notify team |
| Response time > 2s | Warning | Investigate |
| Disk usage > 80% | Warning | Scale storage |

## Database Monitoring

### PostgreSQL Metrics

Monitor key database metrics:

```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

-- Connection utilization
SELECT count(*) * 100.0 / current_setting('max_connections')::int
FROM pg_stat_activity;

-- Slow queries (requires pg_stat_statements)
SELECT query, calls, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### Redis Monitoring

Monitor Redis queue depth:

```bash
# Queue length
redis-cli LLEN boards:queue

# Memory usage
redis-cli INFO memory
```

## Performance Debugging

### Request Tracing

Use request IDs to trace requests through the system:

1. Find request ID in frontend console or response headers
2. Search logs: `grep "request_id=abc123" /var/log/boards/api.log`
3. Correlate with worker logs

### Slow Query Analysis

Enable slow query logging in PostgreSQL:

```sql
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1 second
SELECT pg_reload_conf();
```

## Recommended Monitoring Stack

For a complete monitoring setup:

| Component | Tool | Purpose |
|-----------|------|---------|
| Logs | Loki + Grafana | Log aggregation and search |
| Metrics | Prometheus + Grafana | System and application metrics |
| Errors | Sentry | Error tracking and alerting |
| Uptime | UptimeRobot | External health monitoring |
| APM | Datadog (optional) | Full application performance |

## Next Steps

- [Docker Deployment](./docker.md) - Configure logging in Docker
- [Kubernetes Deployment](./kubernetes.md) - K8s logging and monitoring
- [Configuration Reference](./configuration.md) - Logging environment variables

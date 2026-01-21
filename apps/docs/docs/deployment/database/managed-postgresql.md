---
title: Managed PostgreSQL
description: Configure Boards with any managed PostgreSQL service.
sidebar_position: 2
---

# Managed PostgreSQL

Boards works with any PostgreSQL 14+ database. This guide covers general configuration that applies to all managed PostgreSQL providers.

## Connection URL Format

Configure the database connection via environment variable:

```bash
BOARDS_DATABASE_URL=postgresql://username:password@hostname:port/database?sslmode=require
```

### URL Components

| Component | Description | Example |
|-----------|-------------|---------|
| `username` | Database user | `boards_user` |
| `password` | User password (URL-encoded if contains special chars) | `myp%40ssword` |
| `hostname` | Database host | `db.example.com` |
| `port` | Port number | `5432` |
| `database` | Database name | `boards` |

### Query Parameters

| Parameter | Description | Recommended |
|-----------|-------------|-------------|
| `sslmode` | SSL connection mode | `require` for production |
| `connect_timeout` | Connection timeout (seconds) | `10` |
| `application_name` | Identifies connections in pg_stat_activity | `boards-api` |

Example with all parameters:

```bash
BOARDS_DATABASE_URL=postgresql://boards:password@db.example.com:5432/boards?sslmode=require&connect_timeout=10&application_name=boards-api
```

## SSL Configuration

Most managed providers require SSL connections. Boards supports these modes:

| Mode | Description |
|------|-------------|
| `disable` | No SSL (not recommended) |
| `require` | SSL required, no certificate verification |
| `verify-ca` | SSL required, verify server certificate |
| `verify-full` | SSL required, verify server certificate and hostname |

For providers that require certificate verification:

```bash
# Path to CA certificate
BOARDS_DATABASE_SSL_CA=/path/to/ca-certificate.crt
```

## Connection Pooling

For high-traffic deployments, use a connection pooler like PgBouncer:

```
Application → PgBouncer → PostgreSQL
```

Many managed providers offer built-in connection pooling:
- **Supabase**: Built-in PgBouncer on port 6543
- **Neon**: Serverless driver with built-in pooling
- **AWS RDS**: Use RDS Proxy
- **Cloud SQL**: Use Cloud SQL Auth Proxy

When using pooling, adjust your connection URL to point to the pooler:

```bash
# Direct connection
BOARDS_DATABASE_URL=postgresql://user:pass@db.supabase.co:5432/postgres

# Pooled connection (recommended)
BOARDS_DATABASE_URL=postgresql://user:pass@db.supabase.co:6543/postgres
```

## Database Setup

### 1. Create Database

Most providers create a default database. If you need a dedicated database:

```sql
CREATE DATABASE boards;
```

### 2. Create User (Optional)

For better security, create a dedicated user:

```sql
CREATE USER boards_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE boards TO boards_user;
```

### 3. Run Migrations

Migrations run automatically when the API starts. To run manually:

```bash
# Docker
docker compose exec api python -m boards.db.migrate

# Direct
BOARDS_DATABASE_URL=postgresql://... python -m boards.db.migrate
```

## Performance Recommendations

### Minimum Requirements

| Workload | vCPU | RAM | Storage |
|----------|------|-----|---------|
| Development | 1 | 1GB | 10GB |
| Small production | 2 | 4GB | 20GB |
| Medium production | 4 | 8GB | 50GB |
| Large production | 8+ | 16GB+ | 100GB+ |

### Indexes

Boards creates these indexes automatically via migrations. Verify they exist for optimal performance:

```sql
-- Check existing indexes
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public';
```

### Connection Limits

Configure your pool size based on your database's connection limit:

| Provider | Default Max Connections |
|----------|------------------------|
| AWS RDS (db.t3.micro) | 66 |
| Cloud SQL (db-f1-micro) | 25 |
| Supabase (Free) | 60 |
| Neon (Free) | 100 |

## Monitoring Queries

Check database health:

```sql
-- Active connections
SELECT count(*) as connections,
       state,
       application_name
FROM pg_stat_activity
GROUP BY state, application_name;

-- Database size
SELECT pg_size_pretty(pg_database_size(current_database()));

-- Table sizes
SELECT relname as table,
       pg_size_pretty(pg_total_relation_size(relid)) as size
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 10;

-- Slow queries (if pg_stat_statements enabled)
SELECT query,
       calls,
       round(mean_exec_time::numeric, 2) as avg_ms
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

## Provider-Specific Guides

For detailed setup instructions, see the provider-specific guides:

- [Supabase](./supabase.md) - Postgres with built-in auth and storage
- [AWS RDS](./aws-rds.md) - Amazon's managed PostgreSQL
- [Google Cloud SQL](./cloud-sql.md) - Google's managed PostgreSQL
- [Azure Database](./azure-postgres.md) - Microsoft's managed PostgreSQL
- [Neon](./neon.md) - Serverless PostgreSQL

## Troubleshooting

### Connection Refused

1. Check firewall/security group rules allow your IP
2. Verify the hostname and port
3. Ensure SSL mode matches provider requirements

### Authentication Failed

1. Verify username and password
2. Check if password needs URL encoding for special characters
3. Ensure user has access to the specified database

### SSL Certificate Error

1. Use `sslmode=require` instead of `verify-full`
2. Download and specify the provider's CA certificate
3. Check certificate hasn't expired

### Too Many Connections

1. Use connection pooling
2. Reduce application replica count
3. Upgrade to a larger database instance

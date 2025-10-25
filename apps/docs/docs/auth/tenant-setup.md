# Tenant Setup and Configuration

Boards supports both single-tenant and multi-tenant deployments. This guide covers how to set up tenants for different deployment scenarios.

## Overview

A **tenant** in Boards represents an organizational boundary that contains:
- Users and their authentication data
- Boards and generated content
- Provider configurations and credits
- Settings and customizations

## Single-Tenant Setup

For most deployments, single-tenant mode is the simplest approach where one tenant serves all users.

### Method 1: Automatic Setup (Recommended)

The easiest way is to let Boards create the default tenant automatically:

1. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

2. **Start the application**:
   ```bash
   python -m boards.cli serve
   ```

The default tenant will be created automatically on first startup.

### Method 2: Manual Setup via Migration

You can customize the default tenant using environment variables before running migrations:

```bash
# Set custom tenant details
export BOARDS_TENANT_NAME="My Company"
export BOARDS_TENANT_SLUG="my-company"

# Run migration to create the tenant
alembic upgrade head
```

### Method 3: Setup API Endpoint

Use the setup API for programmatic tenant creation:

```bash
curl -X POST http://localhost:8000/api/setup/tenant \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Company",
    "slug": "my-company",
    "include_sample_data": false
  }'
```

### Method 4: CLI Command

Create tenants using the command line:

```bash
python -m boards.cli tenant create --name "My Company" --slug "my-company"
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BOARDS_TENANT_NAME` | `"Default Tenant"` | Display name for the default tenant |
| `BOARDS_TENANT_SLUG` | `"default"` | URL-safe identifier for the tenant |
| `BOARDS_MULTI_TENANT_MODE` | `false` | Enable multi-tenant support |

### Settings in config.py

```python
# Single-tenant settings
multi_tenant_mode: bool = False
default_tenant_slug: str = "default"
```

## Multi-Tenant Setup

For SaaS applications or organizations that need strict separation:

### Enable Multi-Tenant Mode

```bash
export BOARDS_MULTI_TENANT_MODE=true
```

### Create Tenants

**Via API**:
```bash
curl -X POST http://localhost:8000/api/setup/tenant \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer A",
    "slug": "customer-a"
  }'
```

**Via CLI**:
```bash
python -m boards.cli tenant create --name "Customer A" --slug "customer-a"
```

### Tenant Selection

In multi-tenant mode, specify the tenant via the `X-Tenant` header:

```bash
curl -H "X-Tenant: customer-a" http://localhost:8000/graphql
```

## Validation and Status

### Check Setup Status

The setup status endpoint shows your current configuration:

```bash
curl http://localhost:8000/api/setup/status
```

**Example Response**:
```json
{
  "setup_needed": false,
  "has_default_tenant": true,
  "default_tenant_id": "5ccba978-e0dc-4d0b-afb9-abd746cdef73",
  "default_tenant_slug": "default",
  "multi_tenant_mode": false,
  "auth_provider": "none",
  "recommendations": [
    "Single-tenant mode active with tenant: 5ccba978-e0dc-4d0b-afb9-abd746cdef73"
  ]
}
```

### Startup Validation

Boards automatically validates your tenant configuration on startup:

- ✅ **Single-tenant mode**: Ensures default tenant exists
- ✅ **Multi-tenant mode**: Validates database connectivity
- ✅ **Auth integration**: Checks auth provider configuration
- ✅ **Recommendations**: Provides setup guidance

## Tenant Management

### List All Tenants

```bash
python -m boards.cli tenant list
```

### Seed Database

Create all initial data (including default tenant):

```bash
python -m boards.cli seed
```

## Migration from Single to Multi-Tenant

If you start with single-tenant and want to migrate to multi-tenant:

1. **Set multi-tenant mode**:
   ```bash
   export BOARDS_MULTI_TENANT_MODE=true
   ```

2. **Your existing tenant becomes one of many tenants**
3. **Create additional tenants as needed**
4. **Update client applications** to send `X-Tenant` header

## Integration with Auth Providers

### No Auth (Development)

In no-auth mode, all users belong to the default tenant:

```bash
export BOARDS_AUTH_PROVIDER=none
# Default tenant created automatically
```

### Real Auth Providers

With real auth providers, users are provisioned into tenants based on:

- **Single-tenant**: All users go to the default tenant
- **Multi-tenant**: Tenant determined by:
  - `X-Tenant` header
  - JWT claims (e.g., organization)
  - Domain-based routing
  - Custom logic

## Troubleshooting

### "No Default Tenant" Error

If you see errors about missing tenants:

1. **Check if tenant exists**:
   ```bash
   python -m boards.cli tenant list
   ```

2. **Create default tenant**:
   ```bash
   alembic upgrade head
   # or
   python -m boards.cli tenant create --name "Default" --slug "default"
   ```

### Database Migrations

The seed migration (`553dc6a50a20`) creates the default tenant. If you need to re-run:

```bash
# Downgrade (WARNING: deletes all tenant data)
alembic downgrade 20250101_000000_initial_schema

# Upgrade again
alembic upgrade head
```

### Permission Issues

Even with tenants set up, you need proper board permissions:

```python
# In your application code
await add_board_member(db, board_id, user_id, "owner")
```

## Best Practices

### Single-Tenant Deployments

- Use the default tenant slug consistently
- Set `BOARDS_TENANT_NAME` to your organization name
- Keep `BOARDS_MULTI_TENANT_MODE=false`

### Multi-Tenant SaaS

- Use meaningful tenant slugs (e.g., company names)
- Implement tenant selection logic in your frontend
- Consider tenant-based rate limiting
- Plan for tenant data isolation

### Development

- Use no-auth mode for quick setup: `BOARDS_AUTH_PROVIDER=none`
- The default tenant is created automatically
- Consider using sample data: `include_sample_data: true`

### Production

- Always use a real auth provider
- Set proper tenant names and slugs
- Monitor tenant creation and usage
- Plan for tenant backup and recovery

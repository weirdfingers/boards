# Multi-Tenant Support

Boards provides comprehensive multi-tenant support for SaaS applications and enterprise deployments that require strict data isolation between organizations.

## Overview

Multi-tenant mode enables:

- 🏢 **Complete data isolation** between different organizations
- 🔐 **JWT/OIDC tenant extraction** from authentication claims
- 🎛️ **Self-service tenant registration** for organizations
- 🛡️ **Security auditing** with tenant isolation validation
- 📊 **Management APIs** for tenant CRUD operations
- 🔄 **Migration support** from single to multi-tenant

## Enabling Multi-Tenant Mode

Set the environment variable to enable multi-tenant support:

```bash
export BOARDS_MULTI_TENANT_MODE=true
```

In multi-tenant mode, each API request must include a tenant identifier via:

1. **JWT/OIDC claims** (automatic extraction)
2. **X-Tenant header** (explicit specification)

## Tenant Extraction from JWT/OIDC

Boards automatically extracts tenant information from authentication tokens using multiple strategies:

### Strategy 1: Direct Tenant Claim

```json
{
  "sub": "user123",
  "tenant": "acme-corp",
  "email": "user@acme-corp.com"
}
```

### Strategy 2: Organization Claims

```json
{
  "sub": "user123",
  "org": "acme-corp",
  "organization": "Acme Corporation",
  "org_slug": "acme-corp"
}
```

### Strategy 3: Custom Claims

Configure a custom claim name:

```bash
export BOARDS_JWT_TENANT_CLAIM=company
```

```json
{
  "sub": "user123",
  "company": "acme-corp",
  "email": "user@acme-corp.com"
}
```

### Strategy 4: Email Domain Extraction

For public email domains (gmail.com, etc.), this is skipped. For corporate domains:

```json
{
  "sub": "user123",
  "email": "user@acme-corp.com"
}
// → Extracted tenant: "acme-corp"
```

## X-Tenant Header

When JWT claims don't contain tenant information, use the X-Tenant header:

```bash
curl -H "Authorization: Bearer $TOKEN" \
     -H "X-Tenant: acme-corp" \
     https://api.boards.com/graphql
```

### Frontend Integration

```javascript
// Automatic tenant from JWT
const client = new Client({
  url: '/graphql',
  fetchOptions: {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
});

// Explicit tenant specification
const client = new Client({
  url: '/graphql',
  fetchOptions: {
    headers: {
      'Authorization': `Bearer ${token}`,
      'X-Tenant': 'acme-corp'
    }
  }
});
```

## Tenant Management

### Using the CLI

```bash
# Create a new tenant
python -m boards.cli tenant create --name "Acme Corp" --slug "acme-corp" --sample-data

# List all tenants
python -m boards.cli tenant list

# Audit tenant isolation
python -m boards.cli tenant audit --tenant-slug "acme-corp"
```

### Using the API

See the [Tenant Management API](./tenant-management-api.md) for complete REST API documentation.

```bash
# Create tenant
POST /api/setup/tenant
{
  "name": "Acme Corporation",
  "slug": "acme-corp",
  "settings": {"admin_email": "admin@acme-corp.com"},
  "include_sample_data": true
}

# List tenants
GET /api/setup/tenants
```

## Self-Service Registration

Enable organizations to register their own tenants:

### Configuration

```bash
export BOARDS_TENANT_REGISTRATION_REQUIRES_APPROVAL=false
export BOARDS_TENANT_REGISTRATION_ALLOWED_DOMAINS=company1.com,company2.com
export BOARDS_MAX_TENANTS_PER_USER=3
export BOARDS_FRONTEND_BASE_URL=https://boards.example.com
```

### Registration Flow

```bash
POST /api/tenants/register
Authorization: Bearer $TOKEN
{
  "organization_name": "New Startup Inc",
  "admin_email": "ceo@new-startup.com",
  "use_case": "AI content creation for marketing",
  "organization_size": "small"
}
```

Response includes tenant details and next steps:

```json
{
  "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
  "tenant_slug": "new-startup",
  "status": "active",
  "dashboard_url": "https://boards.example.com/?tenant=new-startup",
  "api_access": {
    "tenant_header": "X-Tenant: new-startup",
    "graphql_endpoint": "/graphql"
  }
}
```

## Security & Isolation

### Tenant Isolation Validation

Boards enforces strict tenant isolation to prevent data leaks:

```python
# Automatic validation in GraphQL resolvers
@strawberry.field
async def boards(self, info: Info) -> List[Board]:
    # Tenant context automatically applied
    return await get_user_boards(info.context.db, info.context.user_id)
```

### Manual Validation

For custom code, use the isolation validator:

```python
from boards.tenant_isolation import ensure_tenant_isolation

await ensure_tenant_isolation(
    db=db_session,
    user_id=user_id,
    tenant_id=tenant_id,
    resource_type="board",
    resource_id=board_id
)
```

### Security Auditing

Regular audits help identify potential isolation violations:

```bash
# Audit specific tenant
python -m boards.cli tenant audit --tenant-slug acme-corp

# Audit all tenants
python -m boards.cli tenant audit --output-format json
```

The audit checks for:
- Cross-tenant user access
- Orphaned records in wrong tenants
- Board membership violations
- Data consistency issues

## Migration from Single-Tenant

### Step 1: Backup Data

```bash
pg_dump boards_db > boards_backup.sql
```

### Step 2: Enable Multi-Tenant Mode

```bash
export BOARDS_MULTI_TENANT_MODE=true
```

### Step 3: Update Client Applications

Add X-Tenant headers or ensure JWT claims include tenant information:

```javascript
// Before (single-tenant)
headers: {
  'Authorization': `Bearer ${token}`
}

// After (multi-tenant)
headers: {
  'Authorization': `Bearer ${token}`,
  'X-Tenant': 'your-tenant-slug'
}
```

### Step 4: Validate Migration

```bash
python -m boards.cli tenant audit
```

Your existing data remains in the default tenant, and you can create additional tenants as needed.

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BOARDS_MULTI_TENANT_MODE` | `false` | Enable multi-tenant support |
| `BOARDS_JWT_TENANT_CLAIM` | `null` | Custom JWT claim for tenant extraction |
| `BOARDS_TENANT_REGISTRATION_REQUIRES_APPROVAL` | `false` | Require admin approval for new tenants |
| `BOARDS_TENANT_REGISTRATION_ALLOWED_DOMAINS` | `null` | Comma-separated list of allowed email domains |
| `BOARDS_MAX_TENANTS_PER_USER` | `null` | Maximum tenants per user (null = unlimited) |
| `BOARDS_FRONTEND_BASE_URL` | `null` | Base URL for frontend dashboard links |

### Supported Tenant Claims

Boards automatically recognizes these JWT/OIDC claims for tenant extraction:

- `tenant` - Direct tenant slug
- `org`, `organization`, `org_slug`, `org_name` - Organization-based
- `namespace`, `group`, `team`, `workspace` - Namespace-based
- Custom claim via `BOARDS_JWT_TENANT_CLAIM`
- Email domain extraction (for non-public domains)

## Troubleshooting

### Common Issues

#### Missing X-Tenant Header

```json
{
  "error": "Missing X-Tenant header",
  "detail": "X-Tenant header is required in multi-tenant mode for this endpoint"
}
```

**Solution**: Add X-Tenant header or ensure JWT contains tenant claims.

#### Tenant Isolation Violation

```json
{
  "error": "Access denied",
  "detail": "User does not belong to tenant"
}
```

**Solution**: Verify user permissions and tenant membership.

#### Invalid Tenant Slug

```json
{
  "error": "Invalid X-Tenant header format",
  "detail": "Tenant slug must contain only lowercase letters, numbers, and hyphens"
}
```

**Solution**: Use valid tenant slug format: `^[a-z0-9-]+$`

### Debugging

Enable debug logging:

```bash
export BOARDS_DEBUG=true
export BOARDS_LOG_LEVEL=debug
```

Check tenant resolution in logs:

```
"Tenant resolved for authenticated request" tenant_slug=acme-corp
```

## Best Practices

1. **Use meaningful tenant slugs** (e.g., company names)
2. **Implement proper error handling** for tenant-related errors
3. **Run regular security audits** with `tenant audit`
4. **Monitor tenant-scoped metrics** and usage
5. **Plan for tenant backup/recovery** procedures
6. **Test tenant isolation** in your application code
7. **Document tenant onboarding** procedures for your users

## Next Steps

- Review the [Tenant Management API](./tenant-management-api.md) reference
- Set up [deployment configuration](../deployment/overview.md) for production
- Configure [monitoring](../deployment/monitoring.md) for tenant-scoped metrics
- Implement tenant-aware [authorization](./backend/authorization.md) in your application
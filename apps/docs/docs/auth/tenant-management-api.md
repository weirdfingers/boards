# Tenant Management API

Complete API reference for multi-tenant management in Boards.

## Authentication

All endpoints require authentication. Include the JWT token in the Authorization header:

```http
Authorization: Bearer <jwt_token>
```

For multi-tenant endpoints, also include the tenant context:

```http
X-Tenant: <tenant_slug>
```

## Setup Endpoints

Base path: `/api/setup`

### Get Setup Status

Get current application setup and configuration.

```http
GET /api/setup/status
```

**Response:**

```json
{
  "setup_needed": false,
  "has_default_tenant": true,
  "default_tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "default_tenant_slug": "default",
  "multi_tenant_mode": true,
  "auth_provider": "jwt",
  "recommendations": [
    "Multi-tenant configuration is ready for operation"
  ]
}
```

## Tenant CRUD Operations

### Create Tenant

Create a new tenant with optional sample data.

```http
POST /api/setup/tenant
Content-Type: application/json
```

**Request:**

```json
{
  "name": "Acme Corporation",
  "slug": "acme-corp",
  "settings": {
    "admin_email": "admin@acme-corp.com",
    "billing_plan": "enterprise",
    "features": ["advanced_ai", "custom_branding"]
  },
  "include_sample_data": true
}
```

**Response:**

```json
{
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Acme Corporation",
  "slug": "acme-corp",
  "message": "Tenant created successfully",
  "existing": false
}
```

**Field Validation:**

- `name`: Required, 1-255 characters
- `slug`: Required, 1-255 characters, format: `^[a-z0-9-]+$`, must be unique
- `settings`: Optional JSON object for tenant-specific configuration
- `include_sample_data`: Boolean, defaults to `false`

### List Tenants

Retrieve all tenants in the system.

```http
GET /api/setup/tenants
```

**Response:**

```json
{
  "tenants": [
    {
      "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Acme Corporation",
      "slug": "acme-corp",
      "settings": {
        "admin_email": "admin@acme-corp.com",
        "billing_plan": "enterprise"
      },
      "created_at": "2025-09-25T10:00:00Z",
      "updated_at": "2025-09-25T12:30:00Z"
    }
  ],
  "total_count": 1
}
```

### Get Tenant

Retrieve specific tenant by ID.

```http
GET /api/setup/tenant/{tenant_id}
```

**Path Parameters:**

- `tenant_id` (UUID): Tenant identifier

**Response:**

```json
{
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Acme Corporation",
  "slug": "acme-corp",
  "settings": {
    "admin_email": "admin@acme-corp.com",
    "billing_plan": "enterprise",
    "features": ["advanced_ai"]
  },
  "created_at": "2025-09-25T10:00:00Z",
  "updated_at": "2025-09-25T14:15:00Z"
}
```

### Update Tenant

Update tenant information. Only provided fields will be updated.

```http
PUT /api/setup/tenant/{tenant_id}
Content-Type: application/json
```

**Request:**

```json
{
  "name": "Acme Corp (Updated)",
  "settings": {
    "admin_email": "new-admin@acme-corp.com",
    "billing_plan": "premium"
  }
}
```

**Response:**

```json
{
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Acme Corp (Updated)",
  "slug": "acme-corp",
  "settings": {
    "admin_email": "new-admin@acme-corp.com",
    "billing_plan": "premium"
  },
  "created_at": "2025-09-25T10:00:00Z",
  "updated_at": "2025-09-25T14:15:00Z"
}
```

### Delete Tenant

⚠️ **Permanently delete a tenant and all associated data.**

```http
DELETE /api/setup/tenant/{tenant_id}
```

**Response:**

```json
{
  "message": "Tenant 'Acme Corporation' (acme-corp) deleted successfully",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "warning": "All related data (users, boards, generations, etc.) has been permanently deleted"
}
```

**Important Notes:**

- This operation is **irreversible**
- Deletes ALL tenant data via CASCADE constraints:
  - All users in the tenant
  - All boards and their content
  - All generations and media
  - All provider configurations
  - All credit transactions
- Cannot delete default tenant in single-tenant mode
- Returns HTTP 400 if attempting to delete default tenant

## Self-Service Registration

Base path: `/api/tenants`

### Check Registration Status

Check if self-service tenant registration is enabled.

```http
GET /api/tenants/registration/status
```

**Response:**

```json
{
  "enabled": true,
  "requires_approval": false,
  "max_tenants_per_user": 3,
  "allowed_domains": [
    "company1.com",
    "company2.com"
  ]
}
```

### Register New Tenant

Register a new tenant (requires authentication).

```http
POST /api/tenants/register
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request:**

```json
{
  "organization_name": "New Startup Inc",
  "organization_slug": "new-startup",
  "admin_email": "ceo@new-startup.com",
  "admin_name": "Jane CEO",
  "use_case": "AI-powered content creation for social media",
  "organization_size": "small",
  "metadata": {
    "industry": "marketing",
    "employees": 25,
    "referral_source": "google"
  },
  "include_sample_data": true
}
```

**Field Validation:**

- `organization_name`: Required, 1-255 characters
- `organization_slug`: Optional, auto-generated if not provided
- `admin_email`: Required, valid email format
- `admin_name`: Optional
- `use_case`: Optional, max 500 characters
- `organization_size`: Optional, one of: `small`, `medium`, `large`, `enterprise`
- `metadata`: Optional JSON object for additional data
- `include_sample_data`: Boolean, default `true`

**Response:**

```json
{
  "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
  "organization_name": "New Startup Inc",
  "tenant_slug": "new-startup",
  "status": "active",
  "admin_instructions": "Your tenant 'new-startup' is ready to use! Include the X-Tenant header in all API requests.",
  "dashboard_url": "https://boards.example.com/?tenant=new-startup",
  "api_access": {
    "tenant_header": "X-Tenant: new-startup",
    "graphql_endpoint": "/graphql",
    "api_base_url": "/api",
    "authentication_required": true
  }
}
```

## Error Responses

### Standard Error Format

```json
{
  "error": "Error Type",
  "detail": "Detailed error message"
}
```

### Multi-Tenant Specific Errors

#### Missing X-Tenant Header

```json
{
  "error": "Missing X-Tenant header",
  "detail": "X-Tenant header is required in multi-tenant mode for this endpoint",
  "multi_tenant_mode": true
}
```

#### Invalid Tenant Slug Format

```json
{
  "error": "Invalid X-Tenant header format",
  "detail": "Tenant slug must contain only lowercase letters, numbers, and hyphens",
  "provided_tenant": "Invalid-Slug!"
}
```

#### Tenant Not Found

```json
{
  "error": "Tenant not found",
  "detail": "Tenant with ID 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

#### Slug Already Exists

```json
{
  "error": "Conflict",
  "detail": "A tenant with slug 'acme-corp' already exists"
}
```

#### Registration Disabled

```json
{
  "error": "Registration disabled",
  "detail": "Tenant registration is only available in multi-tenant mode"
}
```

#### Domain Not Allowed

```json
{
  "error": "Domain not allowed",
  "detail": "Email domain 'example.com' is not allowed for registration"
}
```

## Code Examples

### Python

```python
import httpx
import asyncio

class BoardsTenantClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

    async def create_tenant(self, name: str, slug: str, settings: dict = None):
        async with httpx.AsyncClient() as client:
            data = {
                'name': name,
                'slug': slug,
                'settings': settings or {},
                'include_sample_data': True
            }
            response = await client.post(
                f'{self.base_url}/api/setup/tenant',
                json=data,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def list_tenants(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{self.base_url}/api/setup/tenants',
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def register_tenant(self, org_name: str, admin_email: str, **kwargs):
        async with httpx.AsyncClient() as client:
            data = {
                'organization_name': org_name,
                'admin_email': admin_email,
                'include_sample_data': True,
                **kwargs
            }
            response = await client.post(
                f'{self.base_url}/api/tenants/register',
                json=data,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

# Usage
async def main():
    client = BoardsTenantClient('https://api.boards.com', admin_token)

    # Create tenant
    tenant = await client.create_tenant(
        'Acme Corp',
        'acme-corp',
        {'admin_email': 'admin@acme-corp.com'}
    )
    print(f"Created tenant: {tenant['tenant_id']}")

    # List tenants
    tenants = await client.list_tenants()
    print(f"Total tenants: {tenants['total_count']}")

    # Register via self-service
    new_tenant = await client.register_tenant(
        'Startup Inc',
        'founder@startup.com',
        use_case='AI content creation',
        organization_size='small'
    )
    print(f"Registered: {new_tenant['tenant_slug']}")

asyncio.run(main())
```

### JavaScript/Node.js

```javascript
class BoardsTenantAPI {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.token = token;
  }

  async request(method, endpoint, data = null) {
    const config = {
      method,
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      }
    };

    if (data) {
      config.body = JSON.stringify(data);
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, config);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`API Error: ${error.detail || error.error}`);
    }

    return response.json();
  }

  async createTenant(name, slug, settings = {}) {
    return this.request('POST', '/api/setup/tenant', {
      name,
      slug,
      settings,
      include_sample_data: true
    });
  }

  async listTenants() {
    return this.request('GET', '/api/setup/tenants');
  }

  async getTenant(tenantId) {
    return this.request('GET', `/api/setup/tenant/${tenantId}`);
  }

  async updateTenant(tenantId, updates) {
    return this.request('PUT', `/api/setup/tenant/${tenantId}`, updates);
  }

  async deleteTenant(tenantId) {
    return this.request('DELETE', `/api/setup/tenant/${tenantId}`);
  }

  async registerTenant(organizationName, adminEmail, options = {}) {
    return this.request('POST', '/api/tenants/register', {
      organization_name: organizationName,
      admin_email: adminEmail,
      include_sample_data: true,
      ...options
    });
  }

  async getRegistrationStatus() {
    return this.request('GET', '/api/tenants/registration/status');
  }
}

// Usage
const api = new BoardsTenantAPI('https://api.boards.com', adminToken);

// Create tenant
const tenant = await api.createTenant(
  'Acme Corporation',
  'acme-corp',
  { admin_email: 'admin@acme-corp.com' }
);
console.log('Created:', tenant.tenant_id);

// List tenants
const tenants = await api.listTenants();
console.log('Total:', tenants.total_count);

// Self-service registration
const newTenant = await api.registerTenant(
  'New Company',
  'admin@new-company.com',
  {
    use_case: 'Content marketing automation',
    organization_size: 'medium'
  }
);
console.log('Registered:', newTenant.tenant_slug);
```

### React Hook

```javascript
import { useState, useEffect } from 'react';

export const useTenantManagement = (apiClient) => {
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadTenants = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get('/api/setup/tenants');
      setTenants(response.tenants);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const createTenant = async (tenantData) => {
    setError(null);
    try {
      const newTenant = await apiClient.post('/api/setup/tenant', {
        ...tenantData,
        include_sample_data: true
      });
      setTenants(prev => [...prev, newTenant]);
      return newTenant;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const deleteTenant = async (tenantId) => {
    setError(null);
    try {
      await apiClient.delete(`/api/setup/tenant/${tenantId}`);
      setTenants(prev => prev.filter(t => t.tenant_id !== tenantId));
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const registerTenant = async (registrationData) => {
    setError(null);
    try {
      const result = await apiClient.post('/api/tenants/register', {
        ...registrationData,
        include_sample_data: true
      });
      await loadTenants(); // Refresh list
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  useEffect(() => {
    loadTenants();
  }, []);

  return {
    tenants,
    loading,
    error,
    createTenant,
    deleteTenant,
    registerTenant,
    loadTenants
  };
};
```

## Rate Limits

The following rate limits apply to tenant management endpoints:

| Endpoint | Rate Limit | Window |
|----------|------------|--------|
| `POST /api/setup/tenant` | 10 requests | 1 hour |
| `DELETE /api/setup/tenant/*` | 5 requests | 1 hour |
| `POST /api/tenants/register` | 3 requests | 1 hour |
| `GET /api/setup/*` | 100 requests | 1 minute |

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 8
X-RateLimit-Reset: 1640995200
```

## Next Steps

- Configure [multi-tenant mode](./multi-tenant.md)
- Set up [authentication providers](./overview.md)
- Review [authorization patterns](./backend/authorization.md)
- Implement [tenant-aware monitoring](../deployment/monitoring.md)
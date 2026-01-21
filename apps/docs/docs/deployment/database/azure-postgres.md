---
title: Azure Database for PostgreSQL
description: Use Azure Database for PostgreSQL with Boards.
sidebar_position: 6
---

# Azure Database for PostgreSQL

[Azure Database for PostgreSQL](https://azure.microsoft.com/en-us/products/postgresql/) provides managed PostgreSQL with built-in high availability and automated backups.

## Deployment Options

Azure offers two deployment modes:

| Mode | Best For |
|------|----------|
| **Flexible Server** | Most workloads (recommended) |
| **Single Server** | Legacy, being retired |

This guide covers Flexible Server.

## Creating a Flexible Server

### Via Azure Portal

1. Go to **Azure Database for PostgreSQL** > **Create**
2. Select **Flexible server**
3. Configure basics:
   - **Resource group**: Create or select
   - **Server name**: `boards-db`
   - **Region**: Match your application
   - **PostgreSQL version**: 16
   - **Workload type**: Based on needs
4. Configure compute:
   - **Burstable** for dev/test
   - **General Purpose** for production
5. Configure networking:
   - **Private access** via VNet (recommended)
   - Or **Public access** with firewall rules
6. Set admin credentials
7. Click **Create**

### Via Azure CLI

```bash
# Create resource group
az group create --name boards-rg --location eastus

# Create flexible server
az postgres flexible-server create \
  --resource-group boards-rg \
  --name boards-db \
  --location eastus \
  --admin-user boardsadmin \
  --admin-password 'YourSecurePassword!' \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 16 \
  --yes

# Create database
az postgres flexible-server db create \
  --resource-group boards-rg \
  --server-name boards-db \
  --database-name boards
```

## Connection Configuration

Get the connection string:

```bash
az postgres flexible-server show \
  --resource-group boards-rg \
  --name boards-db \
  --query fullyQualifiedDomainName \
  --output tsv
```

Configure Boards:

```bash
BOARDS_DATABASE_URL=postgresql://boardsadmin:password@boards-db.postgres.database.azure.com:5432/boards?sslmode=require
```

## Firewall Configuration

### Allow Azure Services

```bash
az postgres flexible-server firewall-rule create \
  --resource-group boards-rg \
  --name boards-db \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

### Allow Specific IPs

```bash
az postgres flexible-server firewall-rule create \
  --resource-group boards-rg \
  --name boards-db \
  --rule-name AllowMyIP \
  --start-ip-address YOUR_IP \
  --end-ip-address YOUR_IP
```

### Private Endpoint (Recommended)

For VNet integration:

```bash
az postgres flexible-server update \
  --resource-group boards-rg \
  --name boards-db \
  --public-access Disabled

# Create private endpoint
az network private-endpoint create \
  --resource-group boards-rg \
  --name boards-db-pe \
  --vnet-name your-vnet \
  --subnet your-subnet \
  --private-connection-resource-id $(az postgres flexible-server show -g boards-rg -n boards-db --query id -o tsv) \
  --group-id postgresqlServer \
  --connection-name boards-db-connection
```

## Using Managed Identity

Instead of passwords, use Azure AD authentication:

1. Enable Azure AD authentication:

```bash
az postgres flexible-server update \
  --resource-group boards-rg \
  --name boards-db \
  --active-directory-auth Enabled
```

2. Add Azure AD admin:

```bash
az postgres flexible-server ad-admin create \
  --resource-group boards-rg \
  --server-name boards-db \
  --display-name "boards-app" \
  --object-id YOUR_SERVICE_PRINCIPAL_ID
```

3. Use managed identity in your application to obtain tokens.

## High Availability

Enable zone-redundant HA:

```bash
az postgres flexible-server update \
  --resource-group boards-rg \
  --name boards-db \
  --high-availability ZoneRedundant
```

This provides:
- Synchronous replication across availability zones
- Automatic failover (typically 60-120 seconds)
- No connection string changes

## Backups

### Automated Backups

Configure retention (7-35 days):

```bash
az postgres flexible-server update \
  --resource-group boards-rg \
  --name boards-db \
  --backup-retention 14
```

### Geo-Redundant Backup

Enable for disaster recovery:

```bash
az postgres flexible-server update \
  --resource-group boards-rg \
  --name boards-db \
  --geo-redundant-backup Enabled
```

### Point-in-Time Restore

```bash
az postgres flexible-server restore \
  --resource-group boards-rg \
  --name boards-db-restored \
  --source-server boards-db \
  --restore-time "2024-01-15T10:00:00Z"
```

## Scaling

### Vertical Scaling

```bash
# Scale up compute
az postgres flexible-server update \
  --resource-group boards-rg \
  --name boards-db \
  --sku-name Standard_D2s_v3 \
  --tier GeneralPurpose

# Scale storage (can only increase)
az postgres flexible-server update \
  --resource-group boards-rg \
  --name boards-db \
  --storage-size 64
```

### Read Replicas

Create read replicas for read scaling:

```bash
az postgres flexible-server replica create \
  --resource-group boards-rg \
  --replica-name boards-db-replica \
  --source-server boards-db
```

## Monitoring

### Azure Monitor Metrics

Key metrics to track:
- `cpu_percent`
- `memory_percent`
- `storage_percent`
- `active_connections`
- `connections_failed`

### Query Performance Insight

Enable in Azure Portal under **Query Performance Insight** to identify slow queries.

### Diagnostic Settings

Stream logs to Log Analytics:

```bash
az monitor diagnostic-settings create \
  --resource $(az postgres flexible-server show -g boards-rg -n boards-db --query id -o tsv) \
  --name boards-db-logs \
  --workspace YOUR_LOG_ANALYTICS_WORKSPACE_ID \
  --logs '[{"category": "PostgreSQLLogs", "enabled": true}]' \
  --metrics '[{"category": "AllMetrics", "enabled": true}]'
```

## Pricing

| SKU | vCores | RAM | Monthly (East US) |
|-----|--------|-----|-------------------|
| B1ms (Burstable) | 1 | 2 GB | ~$15 |
| B2s (Burstable) | 2 | 4 GB | ~$30 |
| D2s_v3 (General Purpose) | 2 | 8 GB | ~$125 |
| D4s_v3 (General Purpose) | 4 | 16 GB | ~$250 |

Additional costs:
- Storage: ~$0.115/GB/month
- Backup storage: Free up to 100% of provisioned storage
- HA: Doubles compute cost

## Next Steps

- [Storage Configuration](../storage.md) - Configure Azure Blob Storage
- [Kubernetes Deployment](../kubernetes.md) - Deploy on AKS

---
title: AWS RDS
description: Use Amazon RDS PostgreSQL with Boards.
sidebar_position: 4
---

# AWS RDS PostgreSQL

[Amazon RDS](https://aws.amazon.com/rds/) provides managed PostgreSQL with automated backups, replication, and scaling.

## Creating an RDS Instance

### Via AWS Console

1. Go to **RDS** > **Create database**
2. Select **PostgreSQL**
3. Choose a template:
   - **Free tier** for testing
   - **Production** for production workloads
4. Configure settings:
   - **DB instance identifier**: `boards-db`
   - **Master username**: `boards`
   - **Master password**: Generate or specify
5. Instance configuration:
   - **db.t3.micro** for free tier
   - **db.t3.small** or larger for production
6. Storage:
   - **20 GB** minimum
   - Enable **storage autoscaling** for production
7. Connectivity:
   - **VPC**: Your application VPC
   - **Public access**: No (recommended)
   - **Security group**: Create new or use existing
8. Click **Create database**

### Via AWS CLI

```bash
aws rds create-db-instance \
  --db-instance-identifier boards-db \
  --db-instance-class db.t3.small \
  --engine postgres \
  --engine-version 16 \
  --master-username boards \
  --master-user-password 'your-secure-password' \
  --allocated-storage 20 \
  --storage-type gp3 \
  --vpc-security-group-ids sg-xxxxxxxx \
  --db-subnet-group-name your-subnet-group \
  --no-publicly-accessible \
  --backup-retention-period 7
```

## Security Group Configuration

Allow inbound PostgreSQL connections from your application:

```bash
# Allow from ECS/EKS security group
aws ec2 authorize-security-group-ingress \
  --group-id sg-rds-xxxxxxxx \
  --protocol tcp \
  --port 5432 \
  --source-group sg-app-xxxxxxxx
```

Or for specific IPs:

```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-rds-xxxxxxxx \
  --protocol tcp \
  --port 5432 \
  --cidr 10.0.0.0/16
```

## Connection Configuration

Get the endpoint from the RDS console or CLI:

```bash
aws rds describe-db-instances \
  --db-instance-identifier boards-db \
  --query 'DBInstances[0].Endpoint'
```

Configure Boards:

```bash
BOARDS_DATABASE_URL=postgresql://boards:password@boards-db.xxxxxxxx.us-east-1.rds.amazonaws.com:5432/boards?sslmode=require
```

## RDS Proxy (Recommended)

For serverless or high-concurrency deployments, use RDS Proxy:

1. Go to **RDS** > **Proxies** > **Create proxy**
2. Configure:
   - **Engine family**: PostgreSQL
   - **Target**: Your RDS instance
   - **Secrets Manager secret**: Create for credentials
3. Update connection string to use proxy endpoint:

```bash
BOARDS_DATABASE_URL=postgresql://boards:password@proxy-endpoint.proxy-xxxxxxxx.us-east-1.rds.amazonaws.com:5432/boards
```

Benefits:
- Connection pooling
- Reduced connection overhead
- Automatic failover handling

## Using IAM Authentication

Instead of passwords, authenticate with IAM:

1. Enable IAM auth on your RDS instance
2. Create IAM policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "rds-db:connect",
      "Resource": "arn:aws:rds-db:us-east-1:123456789:dbuser:db-XXXXX/boards"
    }
  ]
}
```

3. Generate auth token in your application:

```bash
aws rds generate-db-auth-token \
  --hostname boards-db.xxxxxxxx.us-east-1.rds.amazonaws.com \
  --port 5432 \
  --username boards
```

## Backups and Recovery

### Automated Backups

Configure backup retention (up to 35 days):

```bash
aws rds modify-db-instance \
  --db-instance-identifier boards-db \
  --backup-retention-period 7
```

### Manual Snapshots

```bash
aws rds create-db-snapshot \
  --db-instance-identifier boards-db \
  --db-snapshot-identifier boards-backup-$(date +%Y%m%d)
```

### Point-in-Time Recovery

Restore to any point within retention period:

```bash
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier boards-db \
  --target-db-instance-identifier boards-db-restored \
  --restore-time 2024-01-15T10:00:00Z
```

## Multi-AZ Deployment

For high availability, enable Multi-AZ:

```bash
aws rds modify-db-instance \
  --db-instance-identifier boards-db \
  --multi-az
```

This provides:
- Automatic failover (60-120 seconds)
- Synchronous replication
- No endpoint changes on failover

## Monitoring

### CloudWatch Metrics

Key metrics to monitor:
- `CPUUtilization`
- `DatabaseConnections`
- `FreeStorageSpace`
- `ReadLatency` / `WriteLatency`

### Performance Insights

Enable Performance Insights for query-level monitoring:

```bash
aws rds modify-db-instance \
  --db-instance-identifier boards-db \
  --enable-performance-insights \
  --performance-insights-retention-period 7
```

## Pricing Considerations

| Instance | vCPU | RAM | On-Demand (us-east-1) |
|----------|------|-----|----------------------|
| db.t3.micro | 2 | 1 GB | ~$12/month |
| db.t3.small | 2 | 2 GB | ~$24/month |
| db.t3.medium | 2 | 4 GB | ~$48/month |
| db.r6g.large | 2 | 16 GB | ~$150/month |

Additional costs:
- Storage: ~$0.115/GB/month (gp3)
- Backups: Free up to DB size
- Data transfer: Standard AWS rates

## Next Steps

- [ECS Deployment](../cloud/elastic-beanstalk.md) - Deploy Boards on AWS
- [Storage with S3](../storage.md) - Configure S3 storage

---
title: AWS Elastic Beanstalk
description: Deploy Boards to AWS Elastic Beanstalk.
sidebar_position: 2
---

# AWS Elastic Beanstalk

[Elastic Beanstalk](https://aws.amazon.com/elasticbeanstalk/) provides an easy way to deploy containerized applications on AWS with automatic scaling, load balancing, and managed infrastructure.

## Architecture

```mermaid
flowchart TB
    subgraph EB["Elastic Beanstalk"]
        ALB["Application Load Balancer"]

        subgraph ASG["Auto Scaling Group"]
            EC2_1["EC2<br/>API+Worker"]
            EC2_2["EC2<br/>API+Worker"]
            EC2_3["EC2<br/>API+Worker"]
        end

        ALB --> ASG
    end

    ASG --> RDS["RDS<br/>(Postgres)"]
    ASG --> ElastiCache["ElastiCache<br/>(Redis)"]
    ASG --> S3["S3<br/>(Storage)"]
```

## Prerequisites

- AWS account with appropriate permissions
- EB CLI installed (`pip install awsebcli`)
- RDS PostgreSQL instance ([setup guide](../database/aws-rds.md))
- ElastiCache Redis cluster

## Project Setup

### 1. Create Application Directory

```bash
mkdir boards-eb && cd boards-eb
```

### 2. Create docker-compose.yml

Elastic Beanstalk uses Docker Compose for multi-container deployments:

```yaml
version: "3.8"

services:
  api:
    image: ghcr.io/weirdfingers/boards-backend:latest
    command: ["uvicorn", "boards.api.app:app", "--host", "0.0.0.0", "--port", "8800"]
    ports:
      - "80:8800"
    environment:
      - BOARDS_DATABASE_URL=${BOARDS_DATABASE_URL}
      - BOARDS_REDIS_URL=${BOARDS_REDIS_URL}
      - BOARDS_GENERATOR_API_KEYS=${BOARDS_GENERATOR_API_KEYS}
      - BOARDS_AUTH_PROVIDER=${BOARDS_AUTH_PROVIDER}
      - BOARDS_LOG_FORMAT=json
      - BOARDS_GENERATORS_CONFIG_PATH=/app/config/generators.yaml
      - BOARDS_STORAGE_CONFIG_PATH=/app/config/storage_config.yaml
    volumes:
      - ./config:/app/config:ro

  worker:
    image: ghcr.io/weirdfingers/boards-backend:latest
    command: ["boards-worker", "--log-level", "info", "--processes", "1", "--threads", "1"]
    environment:
      - BOARDS_DATABASE_URL=${BOARDS_DATABASE_URL}
      - BOARDS_REDIS_URL=${BOARDS_REDIS_URL}
      - BOARDS_GENERATOR_API_KEYS=${BOARDS_GENERATOR_API_KEYS}
      - BOARDS_INTERNAL_API_URL=http://api:8800
      - BOARDS_LOG_FORMAT=json
      - BOARDS_GENERATORS_CONFIG_PATH=/app/config/generators.yaml
      - BOARDS_STORAGE_CONFIG_PATH=/app/config/storage_config.yaml
    volumes:
      - ./config:/app/config:ro
```

### 3. Create Configuration Files

```bash
mkdir config
```

Create `config/generators.yaml`:

```yaml
generators:
  - class: boards.generators.fal.flux.FluxProGenerator
    enabled: true
  - class: boards.generators.openai.dalle.DallE3Generator
    enabled: true
```

Create `config/storage_config.yaml`:

```yaml
default_provider: s3

providers:
  s3:
    type: s3
    bucket: my-boards-bucket
    region: us-east-1
```

## Initialize Elastic Beanstalk

```bash
eb init

# Select region
# Select "Create new Application"
# Name: boards
# Platform: Docker running on 64bit Amazon Linux 2023
# Select default options for remaining prompts
```

## Create Environment

```bash
eb create boards-production \
  --instance-type t3.small \
  --scale 2 \
  --elb-type application \
  --vpc.id vpc-xxxxx \
  --vpc.ec2subnets subnet-xxxxx,subnet-yyyyy \
  --vpc.elbsubnets subnet-xxxxx,subnet-yyyyy
```

## Configure Environment Variables

Store sensitive values securely:

```bash
# Database URL
eb setenv BOARDS_DATABASE_URL="postgresql://user:pass@rds-endpoint:5432/boards?sslmode=require"

# Redis URL
eb setenv BOARDS_REDIS_URL="redis://elasticache-endpoint:6379/0"

# Generator API keys
eb setenv BOARDS_GENERATOR_API_KEYS='{"fal": "your-key", "openai": "your-key"}'

# Auth configuration
eb setenv BOARDS_AUTH_PROVIDER=jwt
eb setenv BOARDS_JWT_SECRET="your-secret"

# AWS credentials for S3 (or use instance role)
eb setenv AWS_ACCESS_KEY_ID="xxxxx"
eb setenv AWS_SECRET_ACCESS_KEY="xxxxx"
```

## Security Groups

Configure security group rules to allow:

1. **Elastic Beanstalk → RDS**: Port 5432
2. **Elastic Beanstalk → ElastiCache**: Port 6379
3. **Load Balancer → EC2**: Port 80

```bash
# Allow EB instances to access RDS
aws ec2 authorize-security-group-ingress \
  --group-id sg-rds-xxxxx \
  --protocol tcp \
  --port 5432 \
  --source-group sg-eb-xxxxx

# Allow EB instances to access ElastiCache
aws ec2 authorize-security-group-ingress \
  --group-id sg-redis-xxxxx \
  --protocol tcp \
  --port 6379 \
  --source-group sg-eb-xxxxx
```

## Deploy

```bash
eb deploy
```

Check deployment status:

```bash
eb status
eb health
```

## HTTPS Configuration

### Using ACM Certificate

1. Request a certificate in AWS Certificate Manager
2. Configure the load balancer:

Create `.ebextensions/https.config`:

```yaml
option_settings:
  aws:elbv2:listener:443:
    ListenerEnabled: true
    Protocol: HTTPS
    SSLCertificateArns: arn:aws:acm:us-east-1:123456789:certificate/xxxxx
  aws:elbv2:listener:80:
    ListenerEnabled: true
    Protocol: HTTP
    Rules: redirect-to-https

Resources:
  AWSEBV2LoadBalancerListener80:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      DefaultActions:
        - Type: redirect
          RedirectConfig:
            Protocol: HTTPS
            Port: "443"
            StatusCode: HTTP_301
```

## Auto Scaling

Configure scaling in `.ebextensions/autoscaling.config`:

```yaml
option_settings:
  aws:autoscaling:asg:
    MinSize: 2
    MaxSize: 10
  aws:autoscaling:trigger:
    MeasureName: CPUUtilization
    Unit: Percent
    UpperThreshold: 70
    LowerThreshold: 30
    UpperBreakSize: 1
    LowerBreakSize: 1
```

## Instance Profile (IAM Role)

Create an instance profile with necessary permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::my-boards-bucket/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:boards/*"
    }
  ]
}
```

## Logging

### CloudWatch Logs

Enable log streaming in `.ebextensions/logs.config`:

```yaml
option_settings:
  aws:elasticbeanstalk:cloudwatch:logs:
    StreamLogs: true
    DeleteOnTerminate: false
    RetentionInDays: 30
```

View logs:

```bash
eb logs
```

### Application Logs

```bash
# Recent logs
eb logs --all

# Stream logs
eb logs --stream
```

## Monitoring

### CloudWatch Metrics

Key metrics to monitor:
- `EnvironmentHealth`
- `InstanceHealth`
- `CPUUtilization`
- `NetworkIn/NetworkOut`

### Health Dashboard

```bash
eb health --refresh
```

## Updates and Rollback

### Deploy New Version

```bash
# Update image version in docker-compose.yml
eb deploy
```

### Rollback

```bash
# List versions
eb appversion

# Rollback to previous version
eb deploy --version version-label
```

## Cost Optimization

- Use Spot Instances for workers
- Right-size instances based on usage
- Consider Reserved Instances for steady workloads

Enable Spot in `.ebextensions/spot.config`:

```yaml
option_settings:
  aws:ec2:instances:
    EnableSpot: true
    SpotMaxPrice: 0.05
```

## Troubleshooting

### View Instance Logs

```bash
eb ssh
cat /var/log/eb-docker/containers/eb-current-app/*.log
```

### Container Issues

```bash
eb ssh
docker ps
docker logs <container-id>
```

### Database Connection

```bash
eb ssh
docker exec -it <api-container> python -c "from boards.db import engine; print(engine.connect())"
```

## Next Steps

- [AWS RDS Setup](../database/aws-rds.md) - Database configuration
- [S3 Storage](../storage.md) - Configure S3 storage
- [Monitoring](../monitoring.md) - CloudWatch integration

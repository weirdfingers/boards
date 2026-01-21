---
title: Kubernetes Deployment
description: Deploy Boards on Kubernetes with manifests and configuration.
sidebar_position: 3
---

# Kubernetes Deployment

Deploy Boards on Kubernetes using the pre-built container images. This guide provides the manifests needed to run Boards in a Kubernetes cluster.

## Prerequisites

- Kubernetes cluster (1.24+)
- `kubectl` configured to access your cluster
- Container registry access to `ghcr.io` (or Docker Hub)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Kubernetes Cluster                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Ingress   │  │   Service   │  │      Service        │  │
│  │  (optional) │──│  boards-api │  │   boards-worker     │  │
│  └─────────────┘  └──────┬──────┘  └──────────┬──────────┘  │
│                          │                     │             │
│  ┌───────────────────────┴─────────────────────┴──────────┐ │
│  │                     Deployments                         │ │
│  │  ┌─────────────┐              ┌─────────────┐          │ │
│  │  │  API Pods   │              │ Worker Pods │          │ │
│  │  │  (replicas) │              │  (replicas) │          │ │
│  │  └─────────────┘              └─────────────┘          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          │                                   │
│  ┌───────────────────────┴─────────────────────────────────┐ │
│  │              ConfigMap / Secret                          │ │
│  └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   ┌─────────┐       ┌──────────┐      ┌───────────┐
   │PostgreSQL│       │  Redis   │      │  Storage  │
   │(managed) │       │(managed) │      │ (S3/GCS)  │
   └─────────┘       └──────────┘      └───────────┘
```

For production, use managed services for PostgreSQL, Redis, and object storage rather than running them in Kubernetes.

## Namespace

Create a dedicated namespace:

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: boards
```

Apply:

```bash
kubectl apply -f namespace.yaml
```

## Secrets

Store sensitive configuration in a Kubernetes Secret:

```yaml
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: boards-secrets
  namespace: boards
type: Opaque
stringData:
  # Database connection (use your managed PostgreSQL)
  database-url: "postgresql://user:password@your-db-host:5432/boards?sslmode=require"

  # Redis connection (use your managed Redis)
  redis-url: "rediss://user:password@your-redis-host:6379/0"

  # Generator API keys (JSON format)
  generator-api-keys: '{"fal": "your-fal-key", "openai": "your-openai-key"}'

  # Auth provider secrets (if using JWT)
  jwt-secret: "your-jwt-secret-key"

  # Storage credentials (if using S3)
  aws-access-key-id: "your-access-key"
  aws-secret-access-key: "your-secret-key"
```

Apply:

```bash
kubectl apply -f secret.yaml
```

:::warning
For production, use a secrets management solution like:
- Kubernetes External Secrets Operator
- HashiCorp Vault
- AWS Secrets Manager with IRSA
- Google Secret Manager with Workload Identity
:::

## ConfigMaps

Store non-sensitive configuration:

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: boards-config
  namespace: boards
data:
  # Auth configuration
  BOARDS_AUTH_PROVIDER: "jwt"

  # Logging
  BOARDS_LOG_LEVEL: "info"
  BOARDS_LOG_FORMAT: "json"

  # Storage configuration file
  storage_config.yaml: |
    default_provider: s3

    providers:
      s3:
        type: s3
        bucket: my-boards-bucket
        region: us-east-1

  # Generators configuration file
  generators.yaml: |
    generators:
      - class: boards.generators.fal.flux.FluxProGenerator
        enabled: true
      - class: boards.generators.openai.dalle.DallE3Generator
        enabled: true
```

Apply:

```bash
kubectl apply -f configmap.yaml
```

## API Deployment

```yaml
# api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: boards-api
  namespace: boards
  labels:
    app: boards
    component: api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: boards
      component: api
  template:
    metadata:
      labels:
        app: boards
        component: api
    spec:
      containers:
        - name: api
          image: ghcr.io/weirdfingers/boards-backend:latest
          command: ["uvicorn", "boards.api.app:app", "--host", "0.0.0.0", "--port", "8800"]
          ports:
            - containerPort: 8800
              name: http
          env:
            - name: BOARDS_DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: boards-secrets
                  key: database-url
            - name: BOARDS_REDIS_URL
              valueFrom:
                secretKeyRef:
                  name: boards-secrets
                  key: redis-url
            - name: BOARDS_GENERATOR_API_KEYS
              valueFrom:
                secretKeyRef:
                  name: boards-secrets
                  key: generator-api-keys
            - name: BOARDS_AUTH_PROVIDER
              valueFrom:
                configMapKeyRef:
                  name: boards-config
                  key: BOARDS_AUTH_PROVIDER
            - name: BOARDS_JWT_SECRET
              valueFrom:
                secretKeyRef:
                  name: boards-secrets
                  key: jwt-secret
            - name: BOARDS_LOG_LEVEL
              valueFrom:
                configMapKeyRef:
                  name: boards-config
                  key: BOARDS_LOG_LEVEL
            - name: BOARDS_LOG_FORMAT
              valueFrom:
                configMapKeyRef:
                  name: boards-config
                  key: BOARDS_LOG_FORMAT
            - name: BOARDS_GENERATORS_CONFIG_PATH
              value: /app/config/generators.yaml
            - name: BOARDS_STORAGE_CONFIG_PATH
              value: /app/config/storage_config.yaml
            - name: AWS_ACCESS_KEY_ID
              valueFrom:
                secretKeyRef:
                  name: boards-secrets
                  key: aws-access-key-id
            - name: AWS_SECRET_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: boards-secrets
                  key: aws-secret-access-key
          volumeMounts:
            - name: config
              mountPath: /app/config
              readOnly: true
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "1Gi"
              cpu: "1000m"
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
      volumes:
        - name: config
          configMap:
            name: boards-config
            items:
              - key: generators.yaml
                path: generators.yaml
              - key: storage_config.yaml
                path: storage_config.yaml
```

## Worker Deployment

```yaml
# worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: boards-worker
  namespace: boards
  labels:
    app: boards
    component: worker
spec:
  replicas: 2
  selector:
    matchLabels:
      app: boards
      component: worker
  template:
    metadata:
      labels:
        app: boards
        component: worker
    spec:
      containers:
        - name: worker
          image: ghcr.io/weirdfingers/boards-backend:latest
          command: ["boards-worker", "--log-level", "info", "--processes", "1", "--threads", "1"]
          env:
            - name: BOARDS_DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: boards-secrets
                  key: database-url
            - name: BOARDS_REDIS_URL
              valueFrom:
                secretKeyRef:
                  name: boards-secrets
                  key: redis-url
            - name: BOARDS_GENERATOR_API_KEYS
              valueFrom:
                secretKeyRef:
                  name: boards-secrets
                  key: generator-api-keys
            - name: BOARDS_INTERNAL_API_URL
              value: "http://boards-api:8800"
            - name: BOARDS_LOG_LEVEL
              valueFrom:
                configMapKeyRef:
                  name: boards-config
                  key: BOARDS_LOG_LEVEL
            - name: BOARDS_LOG_FORMAT
              valueFrom:
                configMapKeyRef:
                  name: boards-config
                  key: BOARDS_LOG_FORMAT
            - name: BOARDS_GENERATORS_CONFIG_PATH
              value: /app/config/generators.yaml
            - name: BOARDS_STORAGE_CONFIG_PATH
              value: /app/config/storage_config.yaml
            - name: AWS_ACCESS_KEY_ID
              valueFrom:
                secretKeyRef:
                  name: boards-secrets
                  key: aws-access-key-id
            - name: AWS_SECRET_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: boards-secrets
                  key: aws-secret-access-key
          volumeMounts:
            - name: config
              mountPath: /app/config
              readOnly: true
          resources:
            requests:
              memory: "512Mi"
              cpu: "200m"
            limits:
              memory: "2Gi"
              cpu: "2000m"
      volumes:
        - name: config
          configMap:
            name: boards-config
            items:
              - key: generators.yaml
                path: generators.yaml
              - key: storage_config.yaml
                path: storage_config.yaml
```

## Services

```yaml
# services.yaml
apiVersion: v1
kind: Service
metadata:
  name: boards-api
  namespace: boards
  labels:
    app: boards
    component: api
spec:
  type: ClusterIP
  ports:
    - port: 8800
      targetPort: 8800
      protocol: TCP
      name: http
  selector:
    app: boards
    component: api
```

## Ingress (Optional)

If using an Ingress controller:

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: boards-ingress
  namespace: boards
  annotations:
    # Adjust annotations for your ingress controller
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - api.boards.example.com
      secretName: boards-tls
  rules:
    - host: api.boards.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: boards-api
                port:
                  number: 8800
```

## Deploy All Manifests

Apply all manifests:

```bash
kubectl apply -f namespace.yaml
kubectl apply -f secret.yaml
kubectl apply -f configmap.yaml
kubectl apply -f api-deployment.yaml
kubectl apply -f worker-deployment.yaml
kubectl apply -f services.yaml
kubectl apply -f ingress.yaml  # if using ingress
```

Or combine into a single file and apply:

```bash
kubectl apply -f boards-k8s.yaml
```

Verify deployment:

```bash
kubectl -n boards get pods
kubectl -n boards get services
kubectl -n boards logs -l component=api -f
```

## Scaling

### Manual Scaling

```bash
# Scale API pods
kubectl -n boards scale deployment boards-api --replicas=3

# Scale worker pods
kubectl -n boards scale deployment boards-worker --replicas=5
```

### Horizontal Pod Autoscaler

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: boards-api-hpa
  namespace: boards
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: boards-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: boards-worker-hpa
  namespace: boards
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: boards-worker
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 80
```

## Updates and Rollbacks

### Rolling Update

```bash
# Update to a specific version
kubectl -n boards set image deployment/boards-api api=ghcr.io/weirdfingers/boards-backend:v1.2.0
kubectl -n boards set image deployment/boards-worker worker=ghcr.io/weirdfingers/boards-backend:v1.2.0

# Watch rollout status
kubectl -n boards rollout status deployment/boards-api
```

### Rollback

```bash
# Rollback to previous version
kubectl -n boards rollout undo deployment/boards-api
kubectl -n boards rollout undo deployment/boards-worker
```

## Troubleshooting

### Check Pod Status

```bash
kubectl -n boards get pods
kubectl -n boards describe pod <pod-name>
```

### View Logs

```bash
# API logs
kubectl -n boards logs -l component=api -f

# Worker logs
kubectl -n boards logs -l component=worker -f

# Specific pod logs
kubectl -n boards logs <pod-name> -f
```

### Debug Connectivity

```bash
# Test database connection from a pod
kubectl -n boards exec -it <api-pod> -- python -c "from boards.db import engine; print(engine.url)"

# Test Redis connection
kubectl -n boards exec -it <api-pod> -- python -c "import redis; r = redis.from_url('$BOARDS_REDIS_URL'); print(r.ping())"
```

### Check Resource Usage

```bash
kubectl -n boards top pods
```

## Next Steps

- [Configuration Reference](./configuration.md) - All environment variables
- [Database Setup](./database/managed-postgresql.md) - Configure managed PostgreSQL
- [Storage Configuration](./storage.md) - Configure S3 or GCS storage
- [Monitoring](./monitoring.md) - Set up logging and metrics

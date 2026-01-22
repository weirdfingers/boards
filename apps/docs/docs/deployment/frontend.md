---
title: Frontend Deployment
description: Build and deploy the Boards web frontend.
sidebar_position: 8
---

# Frontend Deployment

The Boards frontend requires a custom build because Next.js bakes environment variables into the bundle at build time. This guide covers building and deploying the frontend.

## Why Custom Builds?

Unlike the backend (which has pre-built images), the frontend needs:

1. **Build-time environment variables**: `NEXT_PUBLIC_*` variables are embedded during build
2. **Your API endpoint**: Must know where the backend is deployed
3. **Your auth configuration**: Provider-specific settings

## Dockerfile

Use this Dockerfile to build your frontend:

```dockerfile
FROM node:20-alpine AS base

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* pnpm-lock.yaml* ./
RUN corepack enable pnpm && pnpm install

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build-time environment variables
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_GRAPHQL_URL
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY

ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_GRAPHQL_URL=${NEXT_PUBLIC_GRAPHQL_URL}
ENV NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY}

RUN corepack enable pnpm && pnpm run build

# Production image
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy build output
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
```

## Building the Image

### Docker Build

```bash
docker build \
  --build-arg NEXT_PUBLIC_API_URL=https://api.boards.example.com \
  --build-arg NEXT_PUBLIC_GRAPHQL_URL=https://api.boards.example.com/graphql \
  -t my-boards-frontend:latest \
  -f Dockerfile.web \
  .
```

### With Supabase Auth

```bash
docker build \
  --build-arg NEXT_PUBLIC_API_URL=https://api.boards.example.com \
  --build-arg NEXT_PUBLIC_GRAPHQL_URL=https://api.boards.example.com/graphql \
  --build-arg NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co \
  --build-arg NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key \
  -t my-boards-frontend:latest \
  -f Dockerfile.web \
  .
```

## Docker Compose

Add the frontend to your `compose.yaml`:

```yaml
services:
  web:
    build:
      context: ./frontend
      dockerfile: Dockerfile.web
      args:
        NEXT_PUBLIC_API_URL: http://localhost:8800
        NEXT_PUBLIC_GRAPHQL_URL: http://localhost:8800/graphql
    ports:
      - "3000:3000"
    depends_on:
      - api

  api:
    image: ghcr.io/weirdfingers/boards-backend:latest
    # ... api config
```

For production with pre-built images:

```yaml
services:
  web:
    image: your-registry/boards-frontend:latest
    ports:
      - "3000:3000"
    depends_on:
      - api
```

## Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: boards-web
  namespace: boards
spec:
  replicas: 2
  selector:
    matchLabels:
      app: boards
      component: web
  template:
    metadata:
      labels:
        app: boards
        component: web
    spec:
      containers:
        - name: web
          image: your-registry/boards-frontend:latest
          ports:
            - containerPort: 3000
          resources:
            requests:
              memory: "128Mi"
              cpu: "50m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          readinessProbe:
            httpGet:
              path: /
              port: 3000
            initialDelaySeconds: 5
            periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: boards-web
  namespace: boards
spec:
  ports:
    - port: 3000
      targetPort: 3000
  selector:
    app: boards
    component: web
```

## Alternative: Static Hosting

For static hosting platforms, export the Next.js app:

### next.config.js

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  // Other config...
};

module.exports = nextConfig;
```

### Build and Deploy

```bash
pnpm build
# Output in ./out directory
```

Then deploy the `out` directory to your static host.

## Hosting Alternatives

### Vercel

[Vercel](https://vercel.com) provides the easiest deployment for Next.js:

1. Connect your repository
2. Set environment variables in dashboard
3. Deploy automatically on push

```bash
# Environment variables in Vercel dashboard
NEXT_PUBLIC_API_URL=https://api.boards.example.com
NEXT_PUBLIC_GRAPHQL_URL=https://api.boards.example.com/graphql
```

Vercel automatically detects Next.js and configures the build.

### Netlify

[Netlify](https://netlify.com) supports Next.js via their runtime:

1. Connect repository
2. Set build command: `pnpm build`
3. Set publish directory: `.next`
4. Add environment variables

### Cloudflare Pages

[Cloudflare Pages](https://pages.cloudflare.com) with Next.js:

1. Connect repository
2. Framework preset: Next.js
3. Build command: `pnpm build`
4. Add environment variables

### AWS Amplify

[AWS Amplify](https://aws.amazon.com/amplify/) for AWS-native deployment:

```yaml
# amplify.yml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - corepack enable pnpm
        - pnpm install
    build:
      commands:
        - pnpm build
  artifacts:
    baseDirectory: .next
    files:
      - "**/*"
  cache:
    paths:
      - node_modules/**/*
```

### Railway

[Railway](https://railway.app) auto-detects Next.js:

1. Create new project from repository
2. Add environment variables
3. Deploy

### Render

[Render](https://render.com) static site deployment:

1. Create new static site
2. Build command: `pnpm build && pnpm export`
3. Publish directory: `out`
4. Add environment variables

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Yes | Backend API base URL |
| `NEXT_PUBLIC_GRAPHQL_URL` | Yes | GraphQL endpoint URL |
| `NEXT_PUBLIC_SUPABASE_URL` | If Supabase | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | If Supabase | Supabase anonymous key |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | If Clerk | Clerk publishable key |

## CORS Configuration

Ensure your backend allows requests from your frontend domain:

```bash
# Backend environment
BOARDS_ALLOWED_ORIGINS=https://boards.example.com,https://www.boards.example.com
```

## SSL/TLS

Always use HTTPS in production:

- **Vercel/Netlify/Cloudflare**: Automatic SSL
- **Custom hosting**: Use Let's Encrypt or your SSL provider
- **Docker**: Put behind a reverse proxy (Caddy, nginx, Traefik)

## Next Steps

- [Docker Deployment](./docker.md) - Full Docker Compose setup
- [Kubernetes Deployment](./kubernetes.md) - K8s manifests
- [Authentication](./authentication.md) - Configure auth for frontend

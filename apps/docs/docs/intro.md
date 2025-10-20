---
sidebar_position: 1
---

# Introduction to Boards

**Boards** is an open-source creative toolkit for AI-generated content, supporting images, video, audio, and text generation through a unified interface.

## What is Boards?

Boards provides a **collaborative workspace** where users can organize AI-generated content into visual collections called "boards". Each board acts as a canvas for creative exploration, featuring:

- 🎨 **Multi-modal content generation** (images, video, audio, text)
- 🔌 **Pluggable provider system** (Replicate, Fal.ai, OpenAI, etc.)
- 📱 **Responsive interface** with drag-and-drop organization  
- 👥 **Collaborative features** with real-time updates
- 🗄️ **Flexible storage** options (Local, S3, GCS, Supabase)

## Architecture Overview

Boards is built as a **monorepo** with both Python and TypeScript components:

- **Backend**: Python 3.12 + FastAPI + GraphQL + SQLAlchemy
- **Frontend**: React + Next.js hooks-first design
- **Job System**: Framework-agnostic workers with real-time progress
- **Database**: PostgreSQL with multi-tenant support
- **Queue**: Redis for job management

## Getting Started

### Prerequisites

- **Node.js** 18+ 
- **Python** 3.12+
- **Docker** and **Docker Compose** (for local development)
- **pnpm** package manager

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/weirdfingers/boards.git
cd boards

# Install all dependencies
make install

# Start database and Redis services  
make docker-up

# Start development servers
make dev
```

This will start:
- Backend API server at `http://localhost:8088`
- Frontend example at `http://localhost:3033`
- Documentation at `http://localhost:4500`
- GraphQL playground at `http://localhost:8088/graphql`

## Next Steps

- 📖 **[Installation Guide](./installation)** - Detailed setup instructions
- 🏗️ **[Backend SDK](./backend/getting-started)** - Python backend development
- ⚛️ **[Frontend Hooks](./frontend/getting-started)** - React integration
- 🎨 **[Auth Providers](./auth/overview)** - Authentication system

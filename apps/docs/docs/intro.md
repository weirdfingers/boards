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

Choose your path based on what you want to do with Boards:

| Path | Best For | Time to Start | Prerequisites |
|------|----------|---------------|---------------|
| **[Install Baseboards](#-quickest-start-install-baseboards)** ⚡ | Using Boards immediately | ~5 minutes | Docker, Node.js 20+ |
| **[Clone Repository](#-contribute-to-boards)** | Contributing to Boards | ~10 minutes | Docker, Node.js 18+, Python 3.12+, pnpm |
| **[Custom Application](#-build-a-custom-app)** | Building your own app | Coming soon | Docker, Node.js 18+, Python 3.12+ |

### ⚡ Quickest Start: Install Baseboards

Baseboards is a production-ready Boards instance you can deploy with one command:

```bash
# Create and start Baseboards
npx @weirdfingers/baseboards up my-boards-app

# Access at http://localhost:3300
```

**Requirements:**
- Docker Desktop (macOS/Windows) or Docker Engine (Linux)
- Node.js 20+

**Next steps:**
- 📖 **[Baseboards Installation Guide](./installation/installing-baseboards)** - Complete setup and configuration
- 📘 **[Baseboards Documentation](./baseboards/overview)** - Learn more about Baseboards

### 🛠️ Contribute to Boards

Clone the repository to contribute or customize the toolkit:

```bash
git clone https://github.com/weirdfingers/boards.git
cd boards
make install
make docker-up
make dev
```

**Requirements:**
- Docker and Docker Compose
- Node.js 18+
- Python 3.12+
- pnpm package manager

**Next steps:**
- 📖 **[Repository Setup Guide](./installation/cloning-repository)** - Detailed installation
- 🤝 **[Contributing Guide](./guides/contributing)** - How to contribute

### 🚧 Build a Custom App

Create your own application using the Boards backend and frontend packages.

**Status:** 🚧 Under construction

**Requirements:**
- Docker and Docker Compose
- Node.js 18+
- Python 3.12+

**Next steps:**
- 📖 **[Custom Application Guide](./installation/custom-application)** - Coming soon
- 🏗️ **[Backend SDK](./backend/getting-started)** - Python backend development
- ⚛️ **[Frontend Hooks](./frontend/getting-started)** - React integration

## Community & Social

Join the Weirdfingers community:

- 🎥 **[TikTok](https://www.tiktok.com/@weirdfingers)** - Creative content and demos
- 🐦 **[X (Twitter)](https://x.com/_Weirdfingers_)** - Updates and announcements
- 📺 **[YouTube](https://www.youtube.com/@Weirdfingers)** - Tutorials and showcases
- 💬 **[Discord](https://discord.gg/rvVuHyuPEx)** - Community discussions
- 📸 **[Instagram](https://www.instagram.com/_weirdfingers_/)** - Visual updates

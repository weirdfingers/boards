---
sidebar_position: 2
---

# Installation

Choose the installation method that best fits your needs.

## Installation Options

There are three ways to get started with Boards:

### ⚡ Quickest Start: Install Baseboards

**Best for:** Using Boards immediately without development setup

Deploy a production-ready Boards instance with one command:

```bash
npx @weirdfingers/baseboards up my-boards-app
```

- **Time to start:** ~5 minutes
- **Prerequisites:** Docker, Node.js 20+
- **Learn more:** [Baseboards Installation Guide](./installation/installing-baseboards)

### 🛠️ Contribute to Boards

**Best for:** Contributing to the project or deep customization

Clone the repository to access the full source code:

```bash
git clone https://github.com/weirdfingers/boards.git
cd boards
make install
```

- **Time to start:** ~10 minutes
- **Prerequisites:** Docker, Node.js 18+, Python 3.12+, pnpm
- **Learn more:** [Repository Cloning Guide](./installation/cloning-repository)

### 🚧 Build a Custom Application

**Best for:** Building your own application with Boards packages

Create a custom app using the Boards backend and frontend packages.

- **Status:** Under construction
- **Prerequisites:** Docker, Node.js 18+, Python 3.12+
- **Learn more:** [Custom Application Guide](./installation/custom-application)

## Comparison

| Method | Setup Time | Prerequisites | Customization | Updates |
|--------|------------|---------------|---------------|---------|
| **Baseboards** | ~5 min | Docker, Node.js 20+ | Configuration files | `baseboards update` |
| **Clone Repo** | ~10 min | Docker, Node.js 18+, Python 3.12+, pnpm | Full source access | `git pull` + rebuild |
| **Custom App** | Coming soon | Docker, Node.js 18+, Python 3.12+ | Maximum flexibility | Package updates |

## Next Steps

Choose your path above to get started, or:

- 📘 **[Introduction](./intro)** - Learn more about Boards
- 📖 **[Baseboards Overview](./baseboards/overview)** - Understand the reference implementation
- 🏗️ **[Backend SDK](./backend/getting-started)** - Backend development
- ⚛️ **[Frontend Hooks](./frontend/getting-started)** - React integration

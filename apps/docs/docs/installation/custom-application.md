---
sidebar_position: 3
---

# Building a Custom Application

🚧 **This guide is under construction** 🚧

Learn how to build a custom application using the Boards backend and frontend packages.

## Overview

Instead of using Baseboards or cloning the full repository, you can build your own custom application by installing the Boards packages directly:

- **`@weirdfingers/boards`** (npm) - React hooks and frontend utilities
- **`boards`** (PyPI, coming soon) - Python backend SDK

This approach gives you:

- ✅ **Full customization** - Build your own UI and UX
- ✅ **Minimal dependencies** - Only include what you need
- ✅ **Framework flexibility** - Use with Remix, Vite, or any React setup
- ✅ **Production packages** - Stable, versioned releases

## What's Coming

This guide will cover:

1. **Backend Setup**
   - Installing the `boards` Python package
   - Configuring database and storage
   - Setting up GraphQL API
   - Running workers for job processing

2. **Frontend Setup**
   - Installing `@weirdfingers/boards` npm package
   - Configuring the GraphQL client
   - Using React hooks for boards, artifacts, and generators
   - Building custom UI components

3. **Authentication**
   - Integrating auth providers (Supabase, Clerk, Auth0)
   - Configuring multi-tenancy
   - Setting up authorization rules

4. **Deployment**
   - Containerizing your custom app
   - Deploying to cloud providers
   - Configuring production settings

## Current Status

**Backend Package (PyPI):** 🚧 In development
- The backend will be published as a pip-installable package
- Currently, you need to clone the repository to use the backend

**Frontend Package (npm):** ✅ Available
- `@weirdfingers/boards` is published and ready to use
- Documentation for standalone usage is being finalized

## Alternatives While This Guide is in Development

### Option 1: Install Baseboards

For the quickest start, use Baseboards:

```bash
npx @weirdfingers/baseboards up my-app
```

Then customize the generated code. See the [Baseboards Installation Guide](./installing-baseboards).

### Option 2: Clone the Repository

For full access to the source code:

```bash
git clone https://github.com/weirdfingers/boards.git
cd boards
make install
```

See the [Repository Cloning Guide](./cloning-repository).

### Option 3: Use Frontend Package Only (Experimental)

You can install the frontend package now and connect it to a Baseboards backend:

```bash
# Install the frontend package
npm install @weirdfingers/boards

# Or with pnpm
pnpm add @weirdfingers/boards
```

**Example usage:**

```tsx
import { BoardsProvider, useBoards, useBoard } from '@weirdfingers/boards';

function App() {
  return (
    <BoardsProvider graphqlUrl="http://localhost:8088/graphql">
      <BoardsList />
    </BoardsProvider>
  );
}

function BoardsList() {
  const { boards, loading, error } = useBoards();

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      {boards.map(board => (
        <div key={board.id}>{board.title}</div>
      ))}
    </div>
  );
}
```

**Note:** You still need a backend running (via Baseboards or cloned repository) to provide the GraphQL API.

## Prerequisites (When Available)

When this guide is complete, you'll need:

- **Docker and Docker Compose** - For database and Redis
- **Node.js 18+** - For frontend development
- **Python 3.12+** - For backend development
- **PostgreSQL** - Database (via Docker or external)
- **Redis** - Job queue (via Docker or external)

## Stay Updated

This guide is actively being developed. Follow progress:

- **GitHub**: [Boards Repository](https://github.com/weirdfingers/boards)
- **Discord**: [Join the Community](https://discord.gg/rvVuHyuPEx)
- **Documentation**: Check back regularly for updates

## Contributing

Want to help write this guide? Contributions are welcome!

1. Check the [Contributing Guide](../guides/contributing)
2. Join the discussion on [Discord](https://discord.gg/rvVuHyuPEx)
3. Open an issue or PR on [GitHub](https://github.com/weirdfingers/boards)

## Resources

While this guide is being written, these resources may help:

- 📘 **[Baseboards Overview](../baseboards/overview)** - See how Baseboards uses the packages
- 🏗️ **[Backend SDK](../backend/getting-started)** - Backend development guide
- ⚛️ **[Frontend Hooks](../frontend/getting-started)** - React hooks documentation
- 🎨 **[Generators](../generators/overview)** - Working with AI generators
- 🔐 **[Authentication](../auth/overview)** - Auth setup and configuration

## Example: Minimal Custom Setup (Preview)

Here's a preview of what the setup might look like when this guide is complete:

### Backend

```bash
# Install backend package (coming soon)
pip install boards

# Create main.py
cat > main.py << 'EOF'
from boards import create_app
from boards.config import Config

config = Config(
    database_url="postgresql://user:pass@localhost/boards",
    redis_url="redis://localhost:6379",
    storage_provider="local",
)

app = create_app(config)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8088)
EOF

# Run
python main.py
```

### Frontend

```bash
# Install frontend package
npm install @weirdfingers/boards urql graphql

# Create App.tsx
cat > App.tsx << 'EOF'
import { BoardsProvider, useBoards } from '@weirdfingers/boards';

export default function App() {
  return (
    <BoardsProvider graphqlUrl="http://localhost:8088/graphql">
      <MyBoardsApp />
    </BoardsProvider>
  );
}

function MyBoardsApp() {
  const { boards } = useBoards();
  return (
    <div>
      <h1>My Custom Boards App</h1>
      {boards.map(board => (
        <div key={board.id}>{board.title}</div>
      ))}
    </div>
  );
}
EOF
```

**Note:** This is a simplified preview. The actual implementation will include proper configuration, error handling, and more features.

---

Check back soon for the complete guide! 🚀

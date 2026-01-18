# Boards Basic Template

A minimal Next.js template for building applications with the Boards AI toolkit.

## What is This?

This is a lightweight starter template that demonstrates how to use the `@weirdfingers/boards` package to build custom AI-powered applications. It provides:

- **Next.js 14+ with App Router** - Modern React framework
- **Boards Hooks** - `useBoards`, `useCreateBoard`, and more
- **Minimal UI** - Basic shadcn/ui components (Button, Card)
- **TypeScript** - Full type safety
- **Tailwind CSS** - Utility-first styling

## Quick Start

### 1. Install Dependencies

```bash
cd web
pnpm install
```

### 2. Configure Environment

Copy the example environment file:

```bash
cp web/.env.example web/.env
```

Edit `web/.env` to point to your Boards API:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8800
NEXT_PUBLIC_GRAPHQL_URL=http://localhost:8800/graphql
```

### 3. Start Development Server

```bash
cd web
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) to see your app.

## Project Structure

```
basic-template/
├── web/                    # Next.js frontend application
│   ├── src/
│   │   ├── app/           # App router pages
│   │   │   ├── layout.tsx # Root layout with BoardsProvider
│   │   │   ├── page.tsx   # Home page with board listing
│   │   │   └── globals.css
│   │   └── components/
│   │       └── ui/        # Basic UI components
│   └── package.json
├── config/                # Backend configuration
│   ├── generators.yaml    # AI generator settings
│   └── storage_config.yaml # Storage provider config
├── extensions/            # Custom extensions
│   ├── generators/        # Custom generator implementations
│   └── plugins/           # Custom backend plugins
└── data/
    └── storage/           # File storage directory
```

## Using Boards Hooks

The template demonstrates basic usage of Boards hooks. Here's what's included in `page.tsx`:

```typescript
import { useBoards, useCreateBoard } from "@weirdfingers/boards";

// List boards
const { boards, loading } = useBoards();

// Create a board
const { createBoard } = useCreateBoard();
createBoard({ title: "My Board", description: "..." });
```

## Available Hooks

The `@weirdfingers/boards` package provides hooks for:

- `useBoards()` - List and manage boards
- `useBoard(id)` - Get a specific board
- `useCreateBoard()` - Create new boards
- `useGenerators()` - List available AI generators
- `useGenerate()` - Trigger AI generation
- And many more...

## Configuration

### Storage Configuration

Edit `config/storage_config.yaml` to configure where generated files are stored.

### Generators Configuration

Edit `config/generators.yaml` to enable/disable AI generators. Add your API keys to `docker/.env.example`.

### Custom Generators

Add custom generator implementations in `extensions/generators/`. See the README there for details.

## Building for Production

```bash
cd web
pnpm build
pnpm start
```

## Docker Deployment

Docker configuration files are included:

- `compose.yaml` - Full stack (API + DB + Redis)
- `compose.web.yaml` - Web frontend
- `Dockerfile.web` - Web build

These will be populated during scaffolding.

## What's Next?

This template is intentionally minimal. You can:

1. **Add more pages** - Create boards detail pages, generation views, etc.
2. **Customize UI** - Add your own components and styling
3. **Add generators** - Configure AI generators for your use case
4. **Extend backend** - Add custom generators or plugins

## Documentation

- [Boards Documentation](https://boards-docs.weirdfingers.com)
- [Generator Configuration](https://boards-docs.weirdfingers.com/docs/generators/configuration)
- [Next.js Documentation](https://nextjs.org/docs)
- [shadcn/ui Components](https://ui.shadcn.com)

## License

See the main Boards repository for license information.

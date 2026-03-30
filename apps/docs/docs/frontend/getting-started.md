---
sidebar_position: 1
---

# Frontend Getting Started

Learn how to integrate Boards into your React applications using the frontend hooks library.

## Overview

The Boards frontend is built with a **hooks-first philosophy**, providing React hooks rather than prescriptive UI components. This approach gives you maximum flexibility to build your own interface while leveraging Boards' powerful backend.

## Architecture

- **React 18+** with hooks and concurrent features
- **TypeScript** for type safety
- **Next.js** compatible (App Router and Pages Router)
- **Real-time updates** via Server-Sent Events (SSE)
- **Optimistic updates** for better UX
- **Provider pattern** for configuration

## Installation

Install the frontend hooks package:

```bash
# With pnpm (recommended)
pnpm add @weirdfingers/boards

# With npm
npm install @weirdfingers/boards

# With yarn
yarn add @weirdfingers/boards
```

## Basic Setup

### 1. Configure the Provider

Wrap your app with the `BoardsProvider`:

```tsx
// app/layout.tsx (Next.js App Router)
import { BoardsProvider } from "@weirdfingers/boards";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <BoardsProvider apiUrl="http://localhost:8088" tenant="your-tenant-id">
          {children}
        </BoardsProvider>
      </body>
    </html>
  );
}
```

```tsx
// pages/_app.tsx (Next.js Pages Router)
import { BoardsProvider } from "@weirdfingers/boards";
import type { AppProps } from "next/app";

export default function App({ Component, pageProps }: AppProps) {
  return (
    <BoardsProvider apiUrl="http://localhost:8088" tenant="your-tenant-id">
      <Component {...pageProps} />
    </BoardsProvider>
  );
}
```

### 2. Authentication Setup

Configure authentication with your preferred provider:

```tsx
// With Supabase
import { BoardsProvider } from "@weirdfingers/boards";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export default function RootLayout({ children }) {
  return (
    <BoardsProvider
      apiUrl="http://localhost:8088"
      tenant="your-tenant-id"
      auth={{
        type: "supabase",
        client: supabase,
      }}
    >
      {children}
    </BoardsProvider>
  );
}
```

## Core Hooks

### useBoards

Manage boards (collections) of generated content:

```tsx
import { useBoards } from "@weirdfingers/boards";

function BoardsList() {
  const { boards, createBoard, updateBoard, deleteBoard, isLoading } =
    useBoards();

  const handleCreateBoard = async () => {
    await createBoard({
      title: "My New Board",
      description: "A collection of AI-generated content",
    });
  };

  if (isLoading) return <div>Loading boards...</div>;

  return (
    <div>
      <button onClick={handleCreateBoard}>Create Board</button>
      {boards.map((board) => (
        <div key={board.id}>
          <h3>{board.title}</h3>
          <p>{board.description}</p>
        </div>
      ))}
    </div>
  );
}
```

### useBoard

Load and manage a single board with its generations:

```tsx
import { useBoard } from "@weirdfingers/boards";

function BoardDetail({ boardId }) {
  const { board, updateBoard, deleteBoard, isLoading } = useBoard(boardId);

  if (isLoading) return <div>Loading board...</div>;
  if (!board) return <div>Board not found</div>;

  return (
    <div>
      <h2>{board.title}</h2>
      <p>{board.description}</p>
      <button onClick={() => updateBoard({ title: "Updated Title" })}>
        Update
      </button>
      <button onClick={deleteBoard}>Delete</button>
    </div>
  );
}
```

### useGeneration

Handle AI content generation with real-time progress:

```tsx
import { useGeneration } from "@weirdfingers/boards";

function GenerationDetail({ generationId }) {
  const { generation, isLoading } = useGeneration(generationId);

  if (isLoading) return <div>Loading generation...</div>;
  if (!generation) return <div>Generation not found</div>;

  return (
    <div>
      <div>Status: {generation.status}</div>
      {generation.progress && <div>Progress: {generation.progress}%</div>}
      {generation.output?.url && (
        <img src={generation.output.url} alt={generation.prompt || ""} />
      )}
    </div>
  );
}
```

### useGenerators

Access available AI generators and their configurations:

```tsx
import { useGenerators } from "@weirdfingers/boards";

function GeneratorSelector({ onSelect }) {
  const { generators, isLoading } = useGenerators();

  if (isLoading) return <div>Loading generators...</div>;

  return (
    <select onChange={(e) => onSelect(e.target.value)}>
      <option value="">Select a generator</option>
      {generators.map((generator) => (
        <option key={generator.id} value={generator.id}>
          {generator.name}
        </option>
      ))}
    </select>
  );
}
```

### useManageTags

CRUD operations for managing tags within your tenant:

```tsx
import { useManageTags } from "@weirdfingers/boards";

function TagManager() {
  const { tags, createTag, updateTag, deleteTag, loading } = useManageTags();

  const handleCreate = async () => {
    await createTag({
      name: "Favorite",
      description: "My favorite generations",
    });
  };

  if (loading) return <div>Loading tags...</div>;

  return (
    <div>
      <button onClick={handleCreate}>Create Tag</button>
      {tags.map((tag) => (
        <div key={tag.id}>
          <span>{tag.name}</span>
          <button onClick={() => deleteTag(tag.id)}>Delete</button>
        </div>
      ))}
    </div>
  );
}
```

### useTagGeneration

Add and remove tags from a specific generation:

```tsx
import { useManageTags, useTagGeneration } from "@weirdfingers/boards";

function GenerationTags({ generationId }: { generationId: string }) {
  const { tags: allTags } = useManageTags();
  const { tags, addTag, removeTag, hasTag } = useTagGeneration(generationId);

  return (
    <div>
      <h3>Tags on this generation:</h3>
      {tags.map((tag) => (
        <span key={tag.id}>
          {tag.name}
          <button onClick={() => removeTag(tag.id)}>x</button>
        </span>
      ))}

      <h3>Available tags:</h3>
      {allTags
        .filter((t) => !hasTag(t.id))
        .map((tag) => (
          <button key={tag.id} onClick={() => addTag(tag.id)}>
            + {tag.name}
          </button>
        ))}
    </div>
  );
}
```

### useTag / useTagBySlug

Fetch a single tag by ID or by slug:

```tsx
import { useTag, useTagBySlug } from "@weirdfingers/boards";

// By ID
function TagDetail({ tagId }: { tagId: string }) {
  const { tag, loading } = useTag(tagId);
  if (loading) return <div>Loading...</div>;
  if (!tag) return <div>Tag not found</div>;
  return <h1>{tag.name}</h1>;
}

// By slug (useful for URL-based routing)
function TagPage({ slug }: { slug: string }) {
  const { tag, loading } = useTagBySlug(slug);
  if (loading) return <div>Loading...</div>;
  if (!tag) return <div>Tag not found</div>;
  return <h1>{tag.name}</h1>;
}
```

## Advanced Usage

### Combining Hooks

Build complex UIs by combining multiple hooks:

```tsx
import { useBoard, useGenerators } from "@weirdfingers/boards";

function BoardWithGenerators({ boardId }) {
  const { board, isLoading: boardLoading } = useBoard(boardId);
  const { generators, isLoading: generatorsLoading } = useGenerators();

  if (boardLoading || generatorsLoading) return <div>Loading...</div>;

  return (
    <div>
      <h2>{board.title}</h2>
      <div className="generators">
        {generators.map((generator) => (
          <div key={generator.id}>
            <h3>{generator.name}</h3>
            <p>{generator.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

## TypeScript Support

The hooks are fully typed with TypeScript. Import types as needed:

```tsx
import type {
  Board,
  Generation,
  Provider,
  GenerationRequest,
  GenerationStatus,
} from "@weirdfingers/boards";

interface BoardCardProps {
  board: Board;
  onSelect: (board: Board) => void;
}

function BoardCard({ board, onSelect }: BoardCardProps) {
  return (
    <div onClick={() => onSelect(board)}>
      <h3>{board.title}</h3>
      <p>{board.description}</p>
      <span>{board.generations?.length || 0} generations</span>
    </div>
  );
}
```

## Error Handling

Handle errors gracefully with built-in error states:

```tsx
import { useBoards } from "@weirdfingers/boards";

function BoardsWithErrorHandling() {
  const { boards, error, retry, isLoading } = useBoards();

  if (error) {
    return (
      <div className="error-state">
        <h3>Failed to load boards</h3>
        <p>{error.message}</p>
        <button onClick={retry}>Try Again</button>
      </div>
    );
  }

  if (isLoading) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      {boards.map((board) => (
        <BoardCard key={board.id} board={board} />
      ))}
    </div>
  );
}
```

## Next Steps

- 🎨 **[UI Examples](./ui-examples)** - Ready-to-use component examples
- 📡 **[Real-time Features](./realtime)** - Build live collaborative features
- 🔧 **[Configuration](./configuration)** - Advanced provider setup
- 🧪 **[Testing](./testing)** - Test your Boards integration

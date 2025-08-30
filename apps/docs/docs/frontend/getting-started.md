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
import { BoardsProvider } from '@weirdfingers/boards';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <BoardsProvider
          apiUrl="http://localhost:8000"
          tenant="your-tenant-id"
        >
          {children}
        </BoardsProvider>
      </body>
    </html>
  );
}
```

```tsx
// pages/_app.tsx (Next.js Pages Router)
import { BoardsProvider } from '@weirdfingers/boards';
import type { AppProps } from 'next/app';

export default function App({ Component, pageProps }: AppProps) {
  return (
    <BoardsProvider
      apiUrl="http://localhost:8000"
      tenant="your-tenant-id"
    >
      <Component {...pageProps} />
    </BoardsProvider>
  );
}
```

### 2. Authentication Setup

Configure authentication with your preferred provider:

```tsx
// With Supabase
import { BoardsProvider } from '@weirdfingers/boards';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export default function RootLayout({ children }) {
  return (
    <BoardsProvider
      apiUrl="http://localhost:8000"
      tenant="your-tenant-id"
      auth={{
        type: 'supabase',
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
import { useBoards } from '@weirdfingers/boards';

function BoardsList() {
  const { boards, createBoard, updateBoard, deleteBoard, isLoading } = useBoards();

  const handleCreateBoard = async () => {
    await createBoard({
      title: 'My New Board',
      description: 'A collection of AI-generated content',
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

### useGenerations

Handle AI content generation with real-time progress:

```tsx
import { useGenerations } from '@weirdfingers/boards';

function GenerationPanel({ boardId }) {
  const { 
    generations, 
    createGeneration, 
    isGenerating 
  } = useGenerations(boardId);

  const handleGenerate = async () => {
    await createGeneration({
      boardId,
      provider: 'replicate',
      generator: 'stable-diffusion',
      prompt: 'A beautiful landscape painting',
      params: {
        width: 1024,
        height: 1024,
        steps: 20,
      },
    });
  };

  return (
    <div>
      <button 
        onClick={handleGenerate}
        disabled={isGenerating}
      >
        {isGenerating ? 'Generating...' : 'Generate Image'}
      </button>

      {generations.map((generation) => (
        <div key={generation.id}>
          <div>Status: {generation.status}</div>
          {generation.progress && (
            <div>Progress: {generation.progress}%</div>
          )}
          {generation.output?.url && (
            <img src={generation.output.url} alt={generation.prompt} />
          )}
        </div>
      ))}
    </div>
  );
}
```

### useProviders

Access available AI providers and their capabilities:

```tsx
import { useProviders } from '@weirdfingers/boards';

function ProviderSelector({ onSelect }) {
  const { providers, isLoading } = useProviders();

  if (isLoading) return <div>Loading providers...</div>;

  return (
    <select onChange={(e) => onSelect(e.target.value)}>
      <option value="">Select a provider</option>
      {providers.map((provider) => (
        <option key={provider.name} value={provider.name}>
          {provider.displayName}
        </option>
      ))}
    </select>
  );
}
```

### useRealtime

Subscribe to real-time updates:

```tsx
import { useRealtime } from '@weirdfingers/boards';

function RealtimeUpdates({ boardId }) {
  const { isConnected, lastEvent } = useRealtime({
    topics: [`board:${boardId}`, 'generations'],
  });

  return (
    <div>
      <div>Connection: {isConnected ? '🟢 Connected' : '🔴 Disconnected'}</div>
      {lastEvent && (
        <div>Last update: {lastEvent.type} at {lastEvent.timestamp}</div>
      )}
    </div>
  );
}
```

## Advanced Usage

### Custom Generation Progress

Create a custom progress component with detailed feedback:

```tsx
import { useGeneration } from '@weirdfingers/boards';

function GenerationProgress({ generationId }) {
  const { generation, progress, logs } = useGeneration(generationId);

  return (
    <div className="generation-progress">
      <div className="progress-bar">
        <div 
          className="progress-fill"
          style={{ width: `${progress}%` }}
        />
      </div>
      
      <div className="status">
        Status: {generation.status}
      </div>

      {logs.length > 0 && (
        <div className="logs">
          <h4>Generation Logs</h4>
          {logs.map((log, index) => (
            <div key={index} className={`log-entry log-${log.level}`}>
              <span className="timestamp">{log.timestamp}</span>
              <span className="message">{log.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

### Batch Operations

Handle multiple generations simultaneously:

```tsx
import { useBatchGenerations } from '@weirdfingers/boards';

function BatchGenerator({ boardId }) {
  const { 
    batchGenerate, 
    activeBatch, 
    isBatchRunning 
  } = useBatchGenerations(boardId);

  const handleBatchGenerate = async () => {
    const prompts = [
      'A serene mountain landscape',
      'A bustling city street at night',
      'An abstract digital artwork',
    ];

    await batchGenerate({
      provider: 'replicate',
      generator: 'stable-diffusion',
      requests: prompts.map(prompt => ({
        prompt,
        params: { width: 512, height: 512 },
      })),
    });
  };

  return (
    <div>
      <button 
        onClick={handleBatchGenerate}
        disabled={isBatchRunning}
      >
        Generate Batch ({activeBatch?.total || 0})
      </button>

      {activeBatch && (
        <div>
          Progress: {activeBatch.completed}/{activeBatch.total}
          ({Math.round((activeBatch.completed / activeBatch.total) * 100)}%)
        </div>
      )}
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
  GenerationStatus 
} from '@weirdfingers/boards';

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
import { useBoards } from '@weirdfingers/boards';

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
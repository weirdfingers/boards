# @weirdfingers/boards

React hooks and components for building AI-powered creative applications with the Boards toolkit.

## Overview

`@weirdfingers/boards` provides a React-first interface to the Boards creative toolkit. Build applications for AI-generated content (images, video, audio, text) using simple, composable hooks.

**Key Features:**

- 🎣 **Hooks-first design** - Clean, React-native API without opinionated UI
- 🔐 **Pluggable auth** - Works with Supabase, Clerk, Auth0, or custom providers
- 📡 **Real-time updates** - SSE for generation progress, GraphQL subscriptions for live data
- 🎨 **Multi-modal support** - Images, video, audio, text generation
- 📦 **Framework agnostic** - Works with Next.js, Remix, Vite, or any React framework
- 🔒 **Type-safe** - Full TypeScript support with generated GraphQL types

## Installation

```bash
npm install @weirdfingers/boards react react-dom
# or
pnpm add @weirdfingers/boards react react-dom
# or
yarn add @weirdfingers/boards react react-dom
```

**Peer Dependencies:**

- `react` ^18.0.0
- `react-dom` ^18.0.0

## Quick Start

### 1. Set up the provider

Wrap your application with `BoardsProvider` to configure the GraphQL client and auth:

```tsx
import { BoardsProvider, NoAuthProvider } from '@weirdfingers/boards';

function App() {
  const authProvider = new NoAuthProvider(); // For development only

  return (
    <BoardsProvider
      apiUrl="http://localhost:8088"
      authProvider={authProvider}
    >
      <YourApp />
    </BoardsProvider>
  );
}
```

### 2. Use hooks in your components

```tsx
import { useBoards, useGeneration } from '@weirdfingers/boards';

function BoardsPage() {
  const { boards, loading, createBoard } = useBoards();
  const { submit, progress, isGenerating } = useGeneration();

  const handleGenerate = async (boardId: string) => {
    await submit({
      boardId,
      model: 'flux-1-schnell',
      artifactType: 'IMAGE',
      inputs: {
        prompt: 'A serene mountain landscape at sunset',
      },
    });
  };

  if (loading) return <div>Loading boards...</div>;

  return (
    <div>
      {boards.map((board) => (
        <div key={board.id}>
          <h2>{board.title}</h2>
          <button onClick={() => handleGenerate(board.id)}>
            Generate Image
          </button>
        </div>
      ))}

      {progress && (
        <div>Progress: {progress.progress}%</div>
      )}
    </div>
  );
}
```

## API Reference

### Provider

#### `<BoardsProvider>`

Main provider component that sets up GraphQL client, auth, and configuration.

**Props:**

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `apiUrl` | `string` | Yes | Base URL for the backend API (e.g., `http://localhost:8088`) |
| `authProvider` | `BaseAuthProvider` | Yes | Authentication provider instance |
| `graphqlUrl` | `string` | No | GraphQL endpoint URL (defaults to `${apiUrl}/graphql`) |
| `subscriptionUrl` | `string` | No | WebSocket URL for GraphQL subscriptions |
| `tenantId` | `string` | No | Tenant ID for multi-tenant deployments |

```tsx
<BoardsProvider
  apiUrl="https://api.example.com"
  authProvider={authProvider}
  tenantId="my-tenant"
>
  {children}
</BoardsProvider>
```

### Hooks

#### `useBoards(options?)`

Manage multiple boards - fetch, create, delete, and search.

**Options:**

```typescript
interface UseBoardsOptions {
  limit?: number;   // Default: 50
  offset?: number;  // Default: 0
}
```

**Returns:**

```typescript
interface BoardsHook {
  boards: Board[];
  loading: boolean;
  error: Error | null;

  // Operations
  createBoard: (data: CreateBoardInput) => Promise<Board>;
  deleteBoard: (boardId: string) => Promise<void>;
  searchBoards: (query: string) => Promise<Board[]>;
  refresh: () => Promise<void>;

  // Search state
  setSearchQuery: (query: string) => void;
  searchQuery: string;
}
```

**Example:**

```tsx
function BoardsList() {
  const { boards, loading, createBoard, deleteBoard } = useBoards({ limit: 20 });

  const handleCreate = async () => {
    await createBoard({
      title: 'My New Board',
      description: 'A board for my creative projects',
    });
  };

  return (
    <div>
      <button onClick={handleCreate}>Create Board</button>
      {boards.map((board) => (
        <div key={board.id}>
          <h3>{board.title}</h3>
          <button onClick={() => deleteBoard(board.id)}>Delete</button>
        </div>
      ))}
    </div>
  );
}
```

#### `useBoard(boardId)`

Manage a single board - update, delete, and handle members/permissions.

**Returns:**

```typescript
interface BoardHook {
  board: Board | null;
  members: BoardMember[];
  permissions: BoardPermissions;
  loading: boolean;
  error: Error | null;

  // Board operations
  updateBoard: (updates: Partial<UpdateBoardInput>) => Promise<Board>;
  deleteBoard: () => Promise<void>;
  refresh: () => Promise<void>;

  // Member management
  addMember: (email: string, role: MemberRole) => Promise<BoardMember>;
  removeMember: (memberId: string) => Promise<void>;
  updateMemberRole: (memberId: string, role: MemberRole) => Promise<BoardMember>;

  // Sharing (placeholder - backend implementation pending)
  generateShareLink: (options: ShareLinkOptions) => Promise<ShareLink>;
  revokeShareLink: (linkId: string) => Promise<void>;
}
```

**Example:**

```tsx
function BoardDetail({ boardId }: { boardId: string }) {
  const {
    board,
    permissions,
    updateBoard,
    addMember,
  } = useBoard(boardId);

  const handleUpdate = async () => {
    await updateBoard({
      title: 'Updated Title',
      description: 'Updated description',
    });
  };

  const handleAddMember = async (email: string) => {
    await addMember(email, 'EDITOR');
  };

  return (
    <div>
      <h1>{board?.title}</h1>
      {permissions.canEdit && (
        <button onClick={handleUpdate}>Update Board</button>
      )}
      {permissions.canAddMembers && (
        <button onClick={() => handleAddMember('user@example.com')}>
          Add Member
        </button>
      )}
    </div>
  );
}
```

#### `useGeneration()`

Submit AI generation requests and track progress in real-time via Server-Sent Events (SSE).

**Returns:**

```typescript
interface GenerationHook {
  // Current generation state
  progress: GenerationProgress | null;
  result: GenerationResult | null;
  error: Error | null;
  isGenerating: boolean;

  // Operations
  submit: (request: GenerationRequest) => Promise<string>;
  cancel: (jobId: string) => Promise<void>;
  retry: (jobId: string) => Promise<void>;

  // History
  history: GenerationResult[];
  clearHistory: () => void;
}
```

**Example:**

```tsx
function ImageGenerator({ boardId }: { boardId: string }) {
  const { submit, progress, result, isGenerating, cancel } = useGeneration();
  const [prompt, setPrompt] = useState('');

  const handleGenerate = async () => {
    const jobId = await submit({
      boardId,
      model: 'flux-1-schnell',
      artifactType: 'IMAGE',
      inputs: {
        prompt,
        steps: 4,
        guidance: 3.5,
      },
      options: {
        priority: 'normal',
      },
    });
    console.log('Generation started:', jobId);
  };

  return (
    <div>
      <input
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Enter your prompt..."
      />
      <button onClick={handleGenerate} disabled={isGenerating}>
        Generate
      </button>

      {progress && (
        <div>
          <p>Status: {progress.status}</p>
          <p>Progress: {progress.progress}%</p>
          {progress.message && <p>{progress.message}</p>}
          {isGenerating && <button onClick={() => cancel(progress.jobId)}>Cancel</button>}
        </div>
      )}

      {result && (
        <div>
          <h3>Generation Complete!</h3>
          {result.artifacts.map((artifact) => (
            <img key={artifact.id} src={artifact.url} alt="Generated" />
          ))}
        </div>
      )}
    </div>
  );
}
```

#### `useGenerators()`

Fetch available AI generators and their input schemas.

**Returns:**

```typescript
interface GeneratorsHook {
  generators: Generator[];
  loading: boolean;
  error: Error | null;

  // Utilities
  getGenerator: (name: string) => Generator | undefined;
  refresh: () => Promise<void>;
}

interface Generator {
  name: string;
  displayName: string;
  description: string;
  artifactType: ArtifactType;
  version: string;
  inputSchema: JSONSchema7;  // JSON Schema for inputs
  enabled: boolean;
  creditCost: number;
  estimatedDuration: number;
  maxDuration: number;
  metadata: Record<string, unknown>;
}
```

**Example:**

```tsx
function GeneratorSelector() {
  const { generators, loading, getGenerator } = useGenerators();

  const fluxGenerator = getGenerator('flux-1-schnell');

  return (
    <div>
      <h2>Available Generators</h2>
      {generators
        .filter((g) => g.enabled)
        .map((generator) => (
          <div key={generator.name}>
            <h3>{generator.displayName}</h3>
            <p>{generator.description}</p>
            <p>Cost: {generator.creditCost} credits</p>
            <p>Type: {generator.artifactType}</p>
          </div>
        ))}
    </div>
  );
}
```

#### `useAuth()`

Access authentication state and user information.

**Returns:**

```typescript
interface UseAuthReturn {
  user: User | null;
  loading: boolean;
  error: Error | null;

  // Auth operations
  getToken: () => Promise<string | null>;
  signOut: () => Promise<void>;
}

interface User {
  id: string;
  email: string;
  displayName: string;
  avatarUrl?: string;
  createdAt: string;
}
```

**Example:**

```tsx
function UserProfile() {
  const { user, loading, signOut } = useAuth();

  if (loading) return <div>Loading...</div>;
  if (!user) return <div>Not authenticated</div>;

  return (
    <div>
      <h2>Welcome, {user.displayName}</h2>
      <p>{user.email}</p>
      <button onClick={signOut}>Sign Out</button>
    </div>
  );
}
```

## Authentication

The package supports multiple auth providers through a plugin system.

### Development (No Auth)

For local development and testing:

```tsx
import { NoAuthProvider } from '@weirdfingers/boards';

const authProvider = new NoAuthProvider();
```

### Custom Auth Provider

Implement `BaseAuthProvider` for custom authentication:

```tsx
import { BaseAuthProvider, AuthState } from '@weirdfingers/boards';

class CustomAuthProvider extends BaseAuthProvider {
  async initialize(): Promise<void> {
    // Initialize your auth system
  }

  async getAuthState(): Promise<AuthState> {
    // Return current auth state
    return {
      isAuthenticated: true,
      userId: 'user-id',
      getToken: async () => 'your-jwt-token',
    };
  }

  async signOut(): Promise<void> {
    // Handle sign out
  }
}
```

### Auth Adapter Packages (Coming Soon)

Dedicated packages for popular auth providers:

- `@weirdfingers/boards-auth-supabase` - Supabase authentication
- `@weirdfingers/boards-auth-clerk` - Clerk authentication
- `@weirdfingers/boards-auth-auth0` - Auth0 authentication

## TypeScript Support

This package is written in TypeScript and includes full type definitions. All hooks and components are fully typed:

```tsx
import type {
  Board,
  Generator,
  GenerationRequest,
  GenerationProgress,
  BoardRole,
  ArtifactType,
} from '@weirdfingers/boards';

// Types are automatically inferred
const { boards } = useBoards(); // boards: Board[]
```

## Examples

### Complete Application Setup

```tsx
// App.tsx
import { BoardsProvider, NoAuthProvider } from '@weirdfingers/boards';
import { BoardsPage } from './BoardsPage';

const authProvider = new NoAuthProvider();

export function App() {
  return (
    <BoardsProvider
      apiUrl={import.meta.env.VITE_API_URL || 'http://localhost:8088'}
      authProvider={authProvider}
    >
      <BoardsPage />
    </BoardsProvider>
  );
}

// BoardsPage.tsx
import { useBoards, useGeneration } from '@weirdfingers/boards';

export function BoardsPage() {
  const { boards, loading, createBoard } = useBoards();
  const { submit, progress, isGenerating } = useGeneration();

  const handleCreateBoard = async () => {
    const board = await createBoard({
      title: 'My Creative Board',
      description: 'A space for AI-generated art',
    });
    console.log('Created board:', board.id);
  };

  const handleGenerate = async (boardId: string) => {
    await submit({
      boardId,
      model: 'flux-1-schnell',
      artifactType: 'IMAGE',
      inputs: {
        prompt: 'A futuristic cityscape at night',
        steps: 4,
        guidance: 3.5,
      },
    });
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <h1>My Boards</h1>
      <button onClick={handleCreateBoard}>Create New Board</button>

      <div className="boards-grid">
        {boards.map((board) => (
          <div key={board.id}>
            <h2>{board.title}</h2>
            <p>{board.description}</p>
            <p>Generations: {board.generationCount}</p>
            <button onClick={() => handleGenerate(board.id)}>
              Generate Image
            </button>
          </div>
        ))}
      </div>

      {progress && (
        <div className="progress-bar">
          <p>Generating: {progress.progress}%</p>
          <p>{progress.message}</p>
        </div>
      )}
    </div>
  );
}
```

### Handling Real-time Progress

```tsx
import { useGeneration } from '@weirdfingers/boards';
import { useEffect, useState } from 'react';

function ProgressTracker() {
  const { submit, progress, result, error } = useGeneration();
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    if (progress?.message) {
      setLogs((prev) => [...prev, `${progress.status}: ${progress.message}`]);
    }
  }, [progress]);

  const handleGenerate = async () => {
    setLogs([]);
    await submit({
      boardId: 'board-id',
      model: 'flux-1-schnell',
      artifactType: 'IMAGE',
      inputs: { prompt: 'A magical forest' },
    });
  };

  return (
    <div>
      <button onClick={handleGenerate}>Generate</button>

      <div className="logs">
        {logs.map((log, i) => (
          <div key={i}>{log}</div>
        ))}
      </div>

      {result && (
        <div>
          <h3>Complete!</h3>
          <p>Time: {result.performance.totalTime}ms</p>
          <p>Cost: {result.credits.cost} credits</p>
        </div>
      )}

      {error && <div className="error">{error.message}</div>}
    </div>
  );
}
```

## Related Packages

- **Backend**: [`@weirdfingers/boards-backend`](https://pypi.org/project/boards/) - Python backend package (GraphQL API, database models, job workers)
- **CLI**: [`@weirdfingers/boards-cli`](https://www.npmjs.com/package/@weirdfingers/boards-cli) - CLI for scaffolding and deployment

## Documentation

For comprehensive documentation, guides, and tutorials, visit:

**[docs.weirdfingers.com](https://docs.weirdfingers.com)**

## Contributing

Contributions are welcome! Please see the [main repository](https://github.com/weirdfingers/boards) for:

- [Contributing Guidelines](https://github.com/weirdfingers/boards/blob/main/CONTRIBUTING.md)
- [Code of Conduct](https://github.com/weirdfingers/boards/blob/main/CODE_OF_CONDUCT.md)
- [Development Setup](https://github.com/weirdfingers/boards#development)

## License

MIT License - see [LICENSE](https://github.com/weirdfingers/boards/blob/main/LICENSE) for details.

## Support

- **GitHub Issues**: [github.com/weirdfingers/boards/issues](https://github.com/weirdfingers/boards/issues)
- **Documentation**: [docs.weirdfingers.com](https://docs.weirdfingers.com)
- **Discord**: [Join our community](https://discord.gg/weirdfingers) *(coming soon)*

---

Built with ❤️ by the Weirdfingers team

# Frontend Hooks - Detailed Technical Design

## Overview

This document provides a detailed technical specification for the frontend hooks API in the Boards creative toolkit. The hooks follow a "hooks-first" design philosophy, providing React hooks that encapsulate data access, authentication, and generation APIs without mandating specific UI components.

## Architecture Principles

### 1. Framework Agnostic
- **Requirement**: All hooks must work across React environments (Next.js, Vite, Create React App, etc.)
- **Implementation**: No framework-specific dependencies, pure React hooks using standard APIs
- **Dependencies**: React Query for data fetching, Zustand for state management

### 2. Provider Pluggability
- **Requirement**: Support multiple auth providers, API endpoints, and transport layers
- **Implementation**: Configuration-based provider system with adapters
- **Extensibility**: Easy to add new providers without breaking existing code

### 3. Type Safety
- **Requirement**: Full TypeScript support with strict type inference
- **Implementation**: Comprehensive type definitions for all hooks, inputs, and outputs
- **Developer Experience**: IntelliSense and compile-time error detection

## Core Hook Categories

### 1. Authentication Hooks (`useAuth`)

```typescript
interface AuthHook {
  user: User | null;
  status: 'loading' | 'authenticated' | 'unauthenticated' | 'error';
  signIn: (provider?: AuthProvider, options?: SignInOptions) => Promise<void>;
  signOut: () => Promise<void>;
  getToken: () => Promise<string | null>;
  refreshToken: () => Promise<string | null>;
}

interface AuthProvider {
  id: string;
  name: string;
  type: 'oauth' | 'email' | 'magic-link' | 'custom';
  config: Record<string, unknown>;
}

interface User {
  id: string;
  email: string;
  name?: string;
  avatar?: string;
  metadata: Record<string, unknown>;
  credits: {
    balance: number;
    reserved: number;
  };
}
```

#### Implementation Details
- **State Management**: Zustand store for auth state persistence
- **Token Management**: Automatic refresh with configurable intervals
- **Provider Support**: Supabase, Clerk, Auth0, custom JWT/OIDC
- **Error Handling**: Standardized error types with retry mechanisms
- **Persistence**: Secure token storage (localStorage with encryption for web, secure storage for mobile)

#### Configuration Example
```typescript
const authConfig = {
  provider: 'supabase',
  config: {
    url: process.env.NEXT_PUBLIC_SUPABASE_URL,
    anonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  },
  tokenRefreshInterval: 15 * 60 * 1000, // 15 minutes
};
```

### 2. Board Management Hooks

#### `useBoards`
```typescript
interface BoardsHook {
  boards: Board[];
  loading: boolean;
  error: Error | null;
  createBoard: (data: CreateBoardInput) => Promise<Board>;
  deleteBoard: (boardId: string) => Promise<void>;
  searchBoards: (query: string) => Promise<Board[]>;
  refresh: () => Promise<void>;
}

interface Board {
  id: string;
  name: string;
  description?: string;
  createdAt: Date;
  updatedAt: Date;
  createdBy: string;
  isPublic: boolean;
  tags: string[];
  artifactCount: number;
  storageUsed: number; // in bytes
}
```

#### `useBoard(boardId: string)`
```typescript
interface BoardHook {
  board: Board | null;
  members: BoardMember[];
  permissions: BoardPermissions;
  loading: boolean;
  error: Error | null;
  
  // Board operations
  updateBoard: (updates: Partial<Board>) => Promise<Board>;
  deleteBoard: () => Promise<void>;
  
  // Member management
  addMember: (email: string, role: MemberRole) => Promise<BoardMember>;
  removeMember: (memberId: string) => Promise<void>;
  updateMemberRole: (memberId: string, role: MemberRole) => Promise<BoardMember>;
  
  // Sharing
  generateShareLink: (options: ShareLinkOptions) => Promise<ShareLink>;
  revokeShareLink: (linkId: string) => Promise<void>;
}

interface BoardMember {
  id: string;
  userId: string;
  boardId: string;
  role: MemberRole;
  user: Pick<User, 'id' | 'email' | 'name' | 'avatar'>;
  joinedAt: Date;
}

type MemberRole = 'owner' | 'admin' | 'editor' | 'viewer';

interface BoardPermissions {
  canEdit: boolean;
  canDelete: boolean;
  canAddMembers: boolean;
  canRemoveMembers: boolean;
  canGenerate: boolean;
  canExport: boolean;
}
```

### 3. Artifact Management Hooks

#### `useArtifacts(boardId: string, options?: ArtifactOptions)`
```typescript
interface ArtifactsHook {
  artifacts: Artifact[];
  loading: boolean;
  error: Error | null;
  hasNextPage: boolean;
  
  // CRUD operations
  uploadInput: (file: File, metadata?: ArtifactMetadata) => Promise<Artifact>;
  deleteArtifact: (artifactId: string) => Promise<void>;
  updateArtifact: (artifactId: string, updates: Partial<Artifact>) => Promise<Artifact>;
  
  // Data access
  download: (artifactId: string, format?: DownloadFormat) => Promise<Blob>;
  getDownloadUrl: (artifactId: string, expiresIn?: number) => Promise<string>;
  
  // Pagination & filtering
  loadMore: () => Promise<void>;
  refresh: () => Promise<void>;
  filter: (criteria: ArtifactFilter) => void;
  sort: (criteria: ArtifactSort) => void;
}

interface Artifact {
  id: string;
  boardId: string;
  type: ArtifactType;
  name: string;
  description?: string;
  url: string;
  thumbnailUrl?: string;
  size: number; // in bytes
  dimensions?: { width: number; height: number };
  duration?: number; // for audio/video in seconds
  mimeType: string;
  metadata: ArtifactMetadata;
  createdAt: Date;
  createdBy: string;
  tags: string[];
  isGenerated: boolean;
  generationId?: string;
}

type ArtifactType = 'image' | 'video' | 'audio' | 'text' | 'lora' | 'model';

interface ArtifactMetadata {
  prompt?: string;
  model?: string;
  provider?: string;
  seed?: number;
  steps?: number;
  guidance?: number;
  [key: string]: unknown;
}
```

### 4. Generation Hooks

#### `useGeneration()`
```typescript
interface GenerationHook {
  // Current generation state
  progress: GenerationProgress | null;
  result: GenerationResult | null;
  error: GenerationError | null;
  isGenerating: boolean;
  
  // Operations
  submit: (request: GenerationRequest) => Promise<string>; // returns jobId
  cancel: (jobId: string) => Promise<void>;
  retry: (jobId: string) => Promise<void>;
  
  // History
  history: GenerationResult[];
  clearHistory: () => void;
}

interface GenerationRequest {
  provider: string;
  model: string;
  inputs: GenerationInputs;
  boardId: string;
  options?: GenerationOptions;
}

interface GenerationInputs {
  prompt: string;
  negativePrompt?: string;
  image?: string | File; // URL or file for img2img
  mask?: string | File;   // For inpainting
  loras?: LoRAInput[];
  seed?: number;
  steps?: number;
  guidance?: number;
  aspectRatio?: string;
  style?: string;
  [key: string]: unknown; // Provider-specific inputs
}

interface GenerationProgress {
  jobId: string;
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number; // 0-100
  estimatedTimeRemaining?: number; // seconds
  currentStep?: string;
  logs?: string[];
}

interface GenerationResult {
  id: string;
  jobId: string;
  boardId: string;
  request: GenerationRequest;
  artifacts: Artifact[];
  credits: {
    cost: number;
    balance: number;
  };
  performance: {
    queueTime: number; // seconds
    processingTime: number; // seconds
    totalTime: number; // seconds
  };
  createdAt: Date;
}
```

#### `useGenerationHistory(boardId?: string)`
```typescript
interface GenerationHistoryHook {
  generations: GenerationResult[];
  loading: boolean;
  error: Error | null;
  hasNextPage: boolean;
  
  loadMore: () => Promise<void>;
  refresh: () => Promise<void>;
  deleteGeneration: (generationId: string) => Promise<void>;
  resubmit: (generationId: string) => Promise<string>;
}
```

### 5. Credits Management Hooks

#### `useCredits()`
```typescript
interface CreditsHook {
  balance: number;
  reserved: number;
  available: number; // balance - reserved
  loading: boolean;
  error: Error | null;
  
  // Operations
  reserve: (amount: number, purpose: string) => Promise<ReservationId>;
  finalize: (reservationId: ReservationId, actualAmount?: number) => Promise<void>;
  refund: (reservationId: ReservationId) => Promise<void>;
  
  // History and reporting
  history: CreditTransaction[];
  loadHistory: (options?: HistoryOptions) => Promise<void>;
  
  // Purchasing (if enabled)
  purchaseCredits: (amount: number, paymentMethod: PaymentMethod) => Promise<void>;
  getPricingTiers: () => Promise<PricingTier[]>;
}

interface CreditTransaction {
  id: string;
  type: 'purchase' | 'generation' | 'refund' | 'adjustment';
  amount: number; // positive for credits added, negative for credits used
  balance: number; // balance after transaction
  description: string;
  metadata: Record<string, unknown>;
  createdAt: Date;
}

type ReservationId = string;
```

### 6. LoRA Management Hooks

#### `useLoras()`
```typescript
interface LorasHook {
  loras: LoRA[];
  loading: boolean;
  error: Error | null;
  
  // LoRA management
  uploadLora: (file: File, metadata: LoRAMetadata) => Promise<LoRA>;
  deleteLora: (loraId: string) => Promise<void>;
  
  // Training (if supported)
  trainLora: (request: LoRATrainingRequest) => Promise<string>; // returns jobId
  getTrainingStatus: (jobId: string) => Promise<TrainingProgress>;
  
  // Usage
  applyToInputs: (loraIds: string[], inputs: GenerationInputs) => GenerationInputs;
}

interface LoRA {
  id: string;
  name: string;
  description?: string;
  type: LoRAType;
  baseModel: string;
  version: string;
  url: string;
  size: number;
  isPublic: boolean;
  createdBy: string;
  createdAt: Date;
  downloadCount: number;
  rating: number;
  tags: string[];
}

type LoRAType = 'style' | 'character' | 'concept' | 'pose' | 'clothing' | 'other';

interface LoRATrainingRequest {
  name: string;
  baseModel: string;
  trainingImages: File[];
  concept: string;
  style?: string;
  steps?: number;
  learningRate?: number;
  boardId: string;
}
```

## Configuration and Extensibility

### Provider Configuration
```typescript
interface BoardsConfig {
  auth: AuthConfig;
  api: ApiConfig;
  storage: StorageConfig;
  features: FeatureFlags;
}

interface AuthConfig {
  provider: 'supabase' | 'clerk' | 'auth0' | 'custom';
  config: Record<string, unknown>;
}

interface ApiConfig {
  baseUrl: string;
  transport: 'graphql' | 'rest';
  timeout: number;
  retries: number;
  headers?: Record<string, string>;
}

interface StorageConfig {
  provider: 'supabase' | 's3' | 'gcs' | 'custom';
  config: Record<string, unknown>;
}

interface FeatureFlags {
  credits: boolean;
  loras: boolean;
  collaboration: boolean;
  realtime: boolean;
}
```

### Custom Provider Interface
```typescript
interface Provider {
  id: string;
  name: string;
  models: Model[];
  authenticate: (config: Record<string, unknown>) => Promise<void>;
  generate: (request: GenerationRequest) => Promise<GenerationJob>;
  getStatus: (jobId: string) => Promise<GenerationProgress>;
  cancel: (jobId: string) => Promise<void>;
}

interface Model {
  id: string;
  name: string;
  type: ModelType;
  inputSchema: JSONSchema;
  outputTypes: ArtifactType[];
  pricing: ModelPricing;
}
```

## Error Handling Strategy

### Error Types
```typescript
class BoardsError extends Error {
  code: string;
  statusCode?: number;
  details?: Record<string, unknown>;
  retryable: boolean;
}

class AuthenticationError extends BoardsError {
  code = 'AUTH_ERROR';
}

class AuthorizationError extends BoardsError {
  code = 'FORBIDDEN';
}

class ValidationError extends BoardsError {
  code = 'VALIDATION_ERROR';
  fields: Record<string, string[]>;
}

class RateLimitError extends BoardsError {
  code = 'RATE_LIMIT';
  retryAfter: number; // seconds
}

class InsufficientCreditsError extends BoardsError {
  code = 'INSUFFICIENT_CREDITS';
  required: number;
  available: number;
}
```

### Retry Strategy
- Exponential backoff for transient errors
- Circuit breaker pattern for provider failures
- User-configurable retry policies
- Automatic retry for network issues
- Manual retry option for failed generations

## Performance Considerations

### Caching Strategy
- React Query for server state caching
- Optimistic updates for user actions
- Background prefetching for related data
- CDN integration for artifact URLs
- Local storage for offline capability

### Data Loading
- Infinite scroll/pagination for large datasets
- Virtual scrolling for artifact grids
- Lazy loading for images and videos
- Progressive image loading with thumbnails
- Background synchronization

### Bundle Size
- Tree-shakeable exports
- Lazy loading of provider adapters
- Dynamic imports for heavy dependencies
- Minimal core bundle size
- Optional feature modules

## Security Considerations

### Token Management
- Secure token storage (encrypted localStorage)
- Automatic token rotation
- XSS protection for token access
- CSRF protection for API calls
- Secure transmission (HTTPS only)

### Data Protection
- Client-side encryption for sensitive data
- Secure file uploads with virus scanning
- Input validation and sanitization
- Rate limiting on client side
- Audit logging for sensitive operations

## Testing Strategy

### Unit Tests
- Hook behavior with React Testing Library
- State management logic
- Error handling scenarios
- Provider adapters
- Utility functions

### Integration Tests
- End-to-end workflows
- Provider integrations
- Authentication flows
- File upload/download
- Real-time updates

### Performance Tests
- Bundle size monitoring
- Memory leak detection
- Rendering performance
- Network request optimization
- Cache effectiveness

## Documentation and Examples

### API Documentation
- TypeScript interfaces with JSDoc
- Usage examples for each hook
- Common patterns and recipes
- Migration guides
- Troubleshooting guides

### Code Examples
- Basic usage examples
- Advanced patterns
- Custom provider implementation
- Integration with popular frameworks
- Performance optimization techniques

## Migration and Versioning

### Semantic Versioning
- Patch: Bug fixes, performance improvements
- Minor: New features, backward compatible changes
- Major: Breaking changes, API redesigns

### Migration Strategy
- Deprecation warnings for old APIs
- Codemods for automated migrations
- Compatibility layers for major versions
- Clear migration documentation
- Automated testing for migrations

## Implementation Roadmap

### Phase 1: Core Hooks
- [ ] Authentication (`useAuth`)
- [ ] Basic board management (`useBoards`, `useBoard`)
- [ ] Artifact management (`useArtifacts`)
- [ ] Provider configuration system

### Phase 2: Generation System
- [ ] Generation hooks (`useGeneration`)
- [ ] Provider adapters (Replicate, fal.ai)
- [ ] Progress tracking and SSE integration
- [ ] Error handling and retry logic

### Phase 3: Advanced Features
- [ ] Credits management (`useCredits`)
- [ ] LoRA support (`useLoras`)
- [ ] Real-time collaboration
- [ ] Advanced search and filtering

### Phase 4: Polish and Performance
- [ ] Performance optimizations
- [ ] Bundle size optimization
- [ ] Comprehensive testing
- [ ] Documentation and examples

This detailed technical design provides a comprehensive foundation for implementing the frontend hooks system while maintaining flexibility, type safety, and excellent developer experience.
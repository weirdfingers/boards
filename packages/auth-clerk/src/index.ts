/**
 * Clerk authentication provider package for Boards.
 */

export { ClerkAuthProvider } from './ClerkAuthProvider';
export type { ClerkConfig } from './types';

// Re-export core types for convenience
export type { 
  AuthState, 
  User, 
  AuthProviderConfig,
  AuthContextValue 
} from '@weirdfingers/boards';
/**
 * Supabase authentication provider package for Boards.
 * 
 * This package provides a tree-shakable Supabase auth provider
 * that can be used independently of the main boards-frontend package.
 */

export { SupabaseAuthProvider } from './SupabaseAuthProvider';
export type { SupabaseConfig } from './types';

// Re-export core types for convenience
export type { 
  AuthState, 
  User, 
  AuthProviderConfig,
  AuthContextValue 
} from '@weirdfingers/boards';
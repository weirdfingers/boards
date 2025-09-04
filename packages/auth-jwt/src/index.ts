/**
 * JWT authentication provider package for Boards.
 */

export { JWTAuthProvider } from './JWTAuthProvider';
export type { JWTConfig } from './types';

// Re-export core types for convenience
export type { 
  AuthState, 
  User, 
  AuthProviderConfig,
  AuthContextValue 
} from '@weirdfingers/boards';
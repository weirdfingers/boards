export const VERSION = '0.1.0'

// Core auth exports
export * from './auth/types';
export * from './auth/hooks/useAuth';
export { AuthProvider } from './auth/context';
export { BaseAuthProvider } from './auth/providers/base';
export { NoAuthProvider } from './auth/providers/none'; // Only no-auth included for dev

// GraphQL exports
export { createGraphQLClient } from './graphql/client';
export * from './graphql/operations';

// Core hooks
export { useBoards } from './hooks/useBoards';
export { useBoard } from './hooks/useBoard';
export { useGeneration } from './hooks/useGeneration';

// Provider components
export { BoardsProvider } from './providers/BoardsProvider';
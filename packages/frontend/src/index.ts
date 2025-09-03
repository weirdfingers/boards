export const VERSION = '0.1.0'

// Core auth exports (no provider dependencies)
export * from './auth/types';
export * from './auth/hooks/useAuth';
export { AuthProvider } from './auth/context';
export { BaseAuthProvider } from './auth/providers/base';
export { NoAuthProvider } from './auth/providers/none'; // Only no-auth included for dev

// GraphQL exports (temporarily disabled due to type issues)
// export { createGraphQLClient } from './graphql/client';
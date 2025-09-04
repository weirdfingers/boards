/**
 * Core authentication types and interfaces.
 */

export interface User {
  id: string;
  email?: string;
  displayName?: string;
  avatarUrl?: string;
  provider: 'supabase' | 'clerk' | 'auth0' | 'oidc' | 'jwt' | 'none';
  subject: string;
}

export interface AuthState {
  user: User | null;
  status: 'unauthenticated' | 'loading' | 'authenticated';
  signIn: (opts?: Record<string, unknown>) => Promise<void>;
  signOut: () => Promise<void>;
  getToken: () => Promise<string | null>;
}

export interface AuthProviderConfig {
  /**
   * Tenant identifier for multi-tenant applications.
   * If not provided, defaults to single-tenant mode.
   */
  tenantId?: string;

  /**
   * Additional configuration specific to the auth provider.
   */
  [key: string]: unknown;
}

export interface AuthContextValue extends AuthState {
  /**
   * Whether the auth system is initializing.
   */
  isInitializing: boolean;

  /**
   * Any error that occurred during authentication.
   */
  error: Error | null;

  /**
   * Clear any authentication errors.
   */
  clearError: () => void;
}
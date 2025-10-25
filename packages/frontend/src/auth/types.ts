/**
 * Core authentication types and interfaces.
 */

export interface User {
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

export interface AuthProvider {
  id: string;
  name: string;
  type: 'oauth' | 'email' | 'magic-link' | 'custom';
  config: Record<string, unknown>;
}

export interface SignInOptions {
  provider?: string;
  redirectTo?: string;
  [key: string]: unknown;
}

export interface AuthState {
  user: User | null;
  status: 'loading' | 'authenticated' | 'unauthenticated' | 'error';
  signIn: (provider?: AuthProvider, options?: SignInOptions) => Promise<void>;
  signOut: () => Promise<void>;
  getToken: () => Promise<string | null>;
  refreshToken: () => Promise<string | null>;
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

/**
 * Base authentication provider abstract class.
 */

import { AuthState, User, AuthProviderConfig } from '../types';

export abstract class BaseAuthProvider {
  protected config: AuthProviderConfig;

  constructor(config: AuthProviderConfig = {}) {
    this.config = config;
  }

  /**
   * Initialize the auth provider.
   * Called once when the provider is created.
   */
  abstract initialize(): Promise<void>;

  /**
   * Get the current authentication state.
   */
  abstract getAuthState(): Promise<AuthState>;

  /**
   * Sign in with the provider.
   */
  abstract signIn(opts?: Record<string, unknown>): Promise<void>;

  /**
   * Sign out from the provider.
   */
  abstract signOut(): Promise<void>;

  /**
   * Get the current authentication token.
   */
  abstract getToken(): Promise<string | null>;

  /**
   * Get the current user information.
   */
  abstract getUser(): Promise<User | null>;

  /**
   * Listen for auth state changes.
   * Returns an unsubscribe function.
   */
  abstract onAuthStateChange(callback: (state: AuthState) => void): () => void;

  /**
   * Clean up resources when the provider is destroyed.
   */
  abstract destroy(): Promise<void>;

  /**
   * Get the tenant ID from config.
   */
  protected getTenantId(): string {
    return this.config.tenantId || 'default';
  }
}

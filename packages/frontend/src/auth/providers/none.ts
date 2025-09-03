/**
 * No-auth provider for local development without authentication.
 */

import { BaseAuthProvider } from './base';
import { AuthState, User, AuthProviderConfig } from '../types';

interface NoAuthConfig extends AuthProviderConfig {
  /**
   * Default user ID for development.
   * Defaults to 'dev-user'.
   */
  defaultUserId?: string;

  /**
   * Default user email for development.
   * Defaults to 'dev@example.com'.
   */
  defaultEmail?: string;

  /**
   * Default display name for development.
   * Defaults to 'Development User'.
   */
  defaultDisplayName?: string;
}

export class NoAuthProvider extends BaseAuthProvider {
  protected config: NoAuthConfig;
  private listeners: ((state: AuthState) => void)[] = [];
  private currentState: AuthState;
  private defaultUser: User;

  constructor(config: NoAuthConfig = {}) {
    super(config);
    this.config = {
      defaultUserId: 'dev-user',
      defaultEmail: 'dev@example.com',
      defaultDisplayName: 'Development User',
      ...config,
    };

    this.defaultUser = {
      id: this.config.defaultUserId!,
      email: this.config.defaultEmail,
      displayName: this.config.defaultDisplayName,
      avatarUrl: undefined,
      provider: 'none',
      subject: this.config.defaultUserId!,
    };

    this.currentState = {
      user: this.defaultUser,
      status: 'authenticated', // Always authenticated in no-auth mode
      signIn: this.signIn.bind(this),
      signOut: this.signOut.bind(this),
      getToken: this.getToken.bind(this),
    };

    console.warn(
      '🚨 NoAuthProvider is active - authentication is disabled! ' +
      'This should ONLY be used in development environments.'
    );
  }

  async initialize(): Promise<void> {
    // No initialization needed - always authenticated
    this.updateState({ user: this.defaultUser, status: 'authenticated' });
  }

  async getAuthState(): Promise<AuthState> {
    return this.currentState;
  }

  async signIn(_opts?: Record<string, unknown>): Promise<void> {
    // No-op in no-auth mode - already signed in
    console.log('SignIn called in no-auth mode - no action taken');
  }

  async signOut(): Promise<void> {
    // No-op in no-auth mode - can't sign out
    console.log('SignOut called in no-auth mode - no action taken');
  }

  async getToken(): Promise<string | null> {
    // Return a fake development token
    return 'dev-token|no-auth-mode|always-valid';
  }

  async getUser(): Promise<User | null> {
    return this.defaultUser;
  }

  onAuthStateChange(callback: (state: AuthState) => void): () => void {
    // Call immediately with current state
    callback(this.currentState);
    
    this.listeners.push(callback);
    return () => {
      const index = this.listeners.indexOf(callback);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }

  async destroy(): Promise<void> {
    this.listeners = [];
  }

  private updateState(updates: Partial<AuthState>): void {
    this.currentState = { ...this.currentState, ...updates };
    this.listeners.forEach(listener => listener(this.currentState));
  }
}
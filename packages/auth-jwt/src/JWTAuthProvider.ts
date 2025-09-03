/**
 * JWT authentication provider for self-issued tokens.
 */

import { BaseAuthProvider, AuthState, User } from '@weirdfingers/boards';
import type { JWTConfig, JWTPayload } from './types';

export class JWTAuthProvider extends BaseAuthProvider {
  protected config: JWTConfig;
  private listeners: ((state: AuthState) => void)[] = [];
  private currentState: AuthState;

  constructor(config: JWTConfig) {
    super(config);
    this.config = {
      tokenStorageKey: 'boards_jwt_token',
      userStorageKey: 'boards_user_info',
      ...config,
    };

    this.currentState = {
      user: null,
      status: 'loading',
      signIn: this.signIn.bind(this),
      signOut: this.signOut.bind(this),
      getToken: this.getToken.bind(this),
    };
  }

  async initialize(): Promise<void> {
    // Check for existing token
    const token = localStorage.getItem(this.config.tokenStorageKey!);
    if (token) {
      try {
        const user = await this.getUserFromToken(token);
        if (user && !this.isTokenExpired(token)) {
          this.updateState({ user, status: 'authenticated' });
          return;
        }
      } catch (error) {
        console.warn('Failed to restore user session:', error);
      }
    }

    this.updateState({ user: null, status: 'unauthenticated' });
  }

  async getAuthState(): Promise<AuthState> {
    return this.currentState;
  }

  async signIn(opts: Record<string, unknown> = {}): Promise<void> {
    const { email, password } = opts as { email: string; password: string };
    this.updateState({ status: 'loading' });

    try {
      const response = await fetch(`${this.config.apiUrl}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.config.tenantId && { 'X-Tenant': this.config.tenantId }),
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        throw new Error(`Authentication failed: ${response.statusText}`);
      }

      const data = await response.json();
      const { token } = data;

      if (!token) {
        throw new Error('No token received from server');
      }

      // Store token
      localStorage.setItem(this.config.tokenStorageKey!, token);

      // Get user info from token
      const user = await this.getUserFromToken(token);
      this.updateState({ user, status: 'authenticated' });
    } catch (error) {
      this.updateState({ user: null, status: 'unauthenticated' });
      throw error;
    }
  }

  async signOut(): Promise<void> {
    // Clear stored data
    localStorage.removeItem(this.config.tokenStorageKey!);
    localStorage.removeItem(this.config.userStorageKey!);

    this.updateState({ user: null, status: 'unauthenticated' });
  }

  async getToken(): Promise<string | null> {
    const token = localStorage.getItem(this.config.tokenStorageKey!);
    if (!token || this.isTokenExpired(token)) {
      return null;
    }
    return token;
  }

  async getUser(): Promise<User | null> {
    return this.currentState.user;
  }

  onAuthStateChange(callback: (state: AuthState) => void): () => void {
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

  private async getUserFromToken(token: string): Promise<User | null> {
    try {
      const payload = this.parseJWT(token);
      
      return {
        id: payload.sub,
        email: payload.email,
        displayName: payload.name,
        avatarUrl: payload.picture,
        provider: 'jwt',
        subject: payload.sub,
      };
    } catch (error) {
      console.error('Failed to parse user from token:', error);
      return null;
    }
  }

  private parseJWT(token: string): JWTPayload {
    const parts = token.split('.');
    if (parts.length !== 3) {
      throw new Error('Invalid JWT format');
    }

    const payload = JSON.parse(atob(parts[1]));
    return payload;
  }

  private isTokenExpired(token: string): boolean {
    try {
      const payload = this.parseJWT(token);
      const now = Math.floor(Date.now() / 1000);
      return payload.exp < now;
    } catch {
      return true;
    }
  }

  private updateState(updates: Partial<AuthState>): void {
    this.currentState = { ...this.currentState, ...updates };
    this.listeners.forEach(listener => listener(this.currentState));
  }
}
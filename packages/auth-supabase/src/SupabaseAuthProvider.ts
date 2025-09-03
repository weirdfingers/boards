/**
 * Supabase authentication provider.
 */

import { BaseAuthProvider, AuthState, User } from '@weirdfingers/boards';
import type { SupabaseConfig } from './types';

export class SupabaseAuthProvider extends BaseAuthProvider {
  protected config: SupabaseConfig;
  private listeners: ((state: AuthState) => void)[] = [];
  private currentState: AuthState;
  private supabase: any; // Will be typed properly when @supabase/supabase-js is available

  constructor(config: SupabaseConfig) {
    super(config);
    this.config = {
      options: {
        persistSession: true,
        detectSessionInUrl: true,
      },
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
    try {
      // Dynamically import Supabase
      const { createClient } = await import('@supabase/supabase-js');
      
      this.supabase = createClient(this.config.url, this.config.anonKey, {
        auth: {
          ...this.config.options,
        },
      });

      // Set up auth state listener
      this.supabase.auth.onAuthStateChange((_event: string, session: any) => {
        this.handleAuthStateChange(_event, session);
      });

      // Get initial session
      const { data: { session } } = await this.supabase.auth.getSession();
      this.handleAuthStateChange('INITIAL_SESSION', session);

    } catch (error) {
      console.error('Failed to initialize Supabase:', error);
      this.updateState({ user: null, status: 'unauthenticated' });
      throw error;
    }
  }

  async getAuthState(): Promise<AuthState> {
    return this.currentState;
  }

  async signIn(opts: {
    email?: string;
    password?: string;
    provider?: 'google' | 'github' | 'discord' | 'twitter' | 'facebook';
    type?: 'signup' | 'signin' | 'magic_link';
    options?: {
      data?: Record<string, any>;
      redirectTo?: string;
      shouldCreateUser?: boolean;
    };
  } = {}): Promise<void> {
    if (!this.supabase) {
      throw new Error('Supabase not initialized');
    }

    this.updateState({ status: 'loading' });

    try {
      // Social provider login
      if (opts.provider) {
        const { error } = await this.supabase.auth.signInWithOAuth({
          provider: opts.provider,
          options: {
            redirectTo: opts.options?.redirectTo || window.location.origin,
            ...this.config.tenantId && { 
              queryParams: { tenant: this.config.tenantId } 
            },
          },
        });

        if (error) throw error;
        return; // OAuth redirects, so we don't update state here
      }

      // Magic link
      if (opts.type === 'magic_link' && opts.email) {
        const { error } = await this.supabase.auth.signInWithOtp({
          email: opts.email,
          options: opts.options,
        });

        if (error) throw error;
        this.updateState({ status: 'unauthenticated' }); // Wait for email click
        return;
      }

      // Email/password signup
      if (opts.type === 'signup' && opts.email && opts.password) {
        const { error } = await this.supabase.auth.signUp({
          email: opts.email,
          password: opts.password,
          options: opts.options,
        });

        if (error) throw error;
        return; // May need email confirmation
      }

      // Email/password signin (default)
      if (opts.email && opts.password) {
        const { error } = await this.supabase.auth.signInWithPassword({
          email: opts.email,
          password: opts.password,
        });

        if (error) throw error;
        return; // State will update via onAuthStateChange
      }

      throw new Error('Invalid sign in options provided');

    } catch (error) {
      this.updateState({ user: null, status: 'unauthenticated' });
      throw error;
    }
  }

  async signOut(): Promise<void> {
    if (!this.supabase) {
      throw new Error('Supabase not initialized');
    }

    const { error } = await this.supabase.auth.signOut();
    if (error) throw error;

    // State will update via onAuthStateChange
  }

  async getToken(): Promise<string | null> {
    if (!this.supabase) return null;

    try {
      const { data: { session } } = await this.supabase.auth.getSession();
      return session?.access_token || null;
    } catch (error) {
      console.error('Failed to get token:', error);
      return null;
    }
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
    // Supabase client cleanup is handled automatically
  }

  private handleAuthStateChange(_event: string, session: any): void {
    if (session) {
      const user: User = {
        id: session.user.id,
        email: session.user.email,
        displayName: 
          session.user.user_metadata?.display_name ||
          session.user.user_metadata?.full_name ||
          session.user.user_metadata?.name ||
          session.user.email?.split('@')[0],
        avatarUrl: 
          session.user.user_metadata?.avatar_url ||
          session.user.user_metadata?.picture,
        provider: 'supabase',
        subject: session.user.id,
      };

      this.updateState({ user, status: 'authenticated' });
    } else {
      this.updateState({ user: null, status: 'unauthenticated' });
    }
  }

  private updateState(updates: Partial<AuthState>): void {
    this.currentState = { ...this.currentState, ...updates };
    this.listeners.forEach(listener => listener(this.currentState));
  }

  /**
   * Get the underlying Supabase client for advanced operations.
   */
  getSupabaseClient() {
    return this.supabase;
  }

  /**
   * Reset password for email.
   */
  async resetPassword(email: string, redirectTo?: string): Promise<void> {
    if (!this.supabase) {
      throw new Error('Supabase not initialized');
    }

    const { error } = await this.supabase.auth.resetPasswordForEmail(email, {
      redirectTo: redirectTo || `${window.location.origin}/reset-password`,
    });

    if (error) throw error;
  }

  /**
   * Update user password.
   */
  async updatePassword(newPassword: string): Promise<void> {
    if (!this.supabase) {
      throw new Error('Supabase not initialized');
    }

    const { error } = await this.supabase.auth.updateUser({
      password: newPassword,
    });

    if (error) throw error;
  }
}
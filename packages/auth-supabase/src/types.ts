/**
 * Supabase auth provider types.
 */

import type { AuthProviderConfig } from '@weirdfingers/boards';

export interface SupabaseConfig extends AuthProviderConfig {
  /**
   * Supabase project URL.
   */
  url: string;

  /**
   * Supabase anonymous/public key.
   */
  anonKey: string;

  /**
   * Additional Supabase client options.
   */
  options?: {
    debug?: boolean;
    persistSession?: boolean;
    detectSessionInUrl?: boolean;
    headers?: Record<string, string>;
    [key: string]: unknown;
  };
}
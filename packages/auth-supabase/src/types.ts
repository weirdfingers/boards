/**
 * Supabase auth provider types.
 */

import type { AuthProviderConfig } from "@weirdfingers/boards";
import type { SupabaseClient } from "@supabase/supabase-js";

/**
 * Options for Supabase client configuration.
 */
export interface SupabaseAuthOptions {
  debug?: boolean;
  persistSession?: boolean;
  detectSessionInUrl?: boolean;
  headers?: Record<string, string>;
}

/**
 * Base configuration shared by all config variants.
 */
interface SupabaseConfigBase extends AuthProviderConfig {
  /**
   * Optional tenant ID for multi-tenant setups.
   */
  tenantId?: string;
}

/**
 * Configuration for creating a new Supabase client.
 */
export interface SupabaseConfigWithCredentials extends SupabaseConfigBase {
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
  options?: SupabaseAuthOptions;

  /**
   * When using credentials, client should not be provided.
   */
  client?: never;
}

/**
 * Configuration for using an existing Supabase client.
 */
export interface SupabaseConfigWithClient extends SupabaseConfigBase {
  /**
   * Pre-configured Supabase client instance.
   */
  client: SupabaseClient;

  /**
   * When using an existing client, credentials should not be provided.
   */
  url?: never;
  anonKey?: never;
  options?: never;
}

/**
 * Supabase configuration - either provide credentials to create a new client,
 * or provide an existing client instance.
 */
export type SupabaseConfig = SupabaseConfigWithCredentials | SupabaseConfigWithClient;

/**
 * Type guard to check if config uses credentials.
 */
export function isCredentialsConfig(
  config: SupabaseConfig
): config is SupabaseConfigWithCredentials {
  return "url" in config && "anonKey" in config && !("client" in config && config.client);
}

/**
 * Type guard to check if config uses an existing client.
 */
export function isClientConfig(config: SupabaseConfig): config is SupabaseConfigWithClient {
  return "client" in config && config.client !== undefined;
}

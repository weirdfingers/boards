/**
 * Clerk auth provider types.
 */

import type { AuthProviderConfig } from '@weirdfingers/boards';

export interface ClerkConfig extends AuthProviderConfig {
  /**
   * Clerk publishable key.
   */
  publishableKey: string;

  /**
   * Optional Clerk options.
   */
  options?: {
    debug?: boolean;
    localization?: unknown;
    appearance?: unknown;
    [key: string]: unknown;
  };
}

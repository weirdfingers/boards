/**
 * JWT auth provider types.
 */

import type { AuthProviderConfig } from '@weirdfingers/boards';

export interface JWTConfig extends AuthProviderConfig {
  /**
   * API endpoint for authentication operations.
   */
  apiUrl: string;

  /**
   * Storage key for the JWT token.
   * Defaults to 'boards_jwt_token'.
   */
  tokenStorageKey?: string;

  /**
   * Storage key for user information.
   * Defaults to 'boards_user_info'.
   */
  userStorageKey?: string;
}

export interface JWTPayload {
  sub: string;
  email?: string;
  name?: string;
  picture?: string;
  exp: number;
  iat: number;
  iss: string;
  aud: string;
}

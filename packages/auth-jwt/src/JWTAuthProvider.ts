/**
 * JWT authentication provider for self-issued tokens.
 */

import { BaseAuthProvider, AuthState, User } from "@weirdfingers/boards";
import type { JWTConfig, JWTPayload } from "./types";

export class JWTAuthProvider extends BaseAuthProvider {
  protected config: JWTConfig;
  private listeners: ((state: AuthState) => void)[] = [];
  private currentState: AuthState;

  constructor(config: JWTConfig) {
    super(config);
    this.config = {
      tokenStorageKey: "boards_jwt_token",
      userStorageKey: "boards_user_info",
      ...config,
    };

    this.currentState = {
      user: null,
      status: "loading",
      signIn: this.signIn.bind(this) as any,
      signOut: this.signOut.bind(this),
      getToken: this.getToken.bind(this),
      refreshToken: this.refreshToken.bind(this),
    };
  }

  async initialize(): Promise<void> {
    // Check for existing token
    const token = localStorage.getItem(this.config.tokenStorageKey!);
    if (token) {
      try {
        const user = await this.getUserFromToken(token);
        if (user && !this.isTokenExpired(token)) {
          this.updateState({ user, status: "authenticated" });
          return;
        }
      } catch (error) {
        console.warn("Failed to restore user session:", error);
      }
    }

    this.updateState({ user: null, status: "unauthenticated" });
  }

  async getAuthState(): Promise<AuthState> {
    return this.currentState;
  }

  async signIn(
    options?: import("@weirdfingers/boards").SignInOptions
  ): Promise<void> {
    const email = (options as any)?.email as string | undefined;
    const password = (options as any)?.password as string | undefined;
    this.updateState({ status: "loading" });

    try {
      const response = await fetch(`${this.config.apiUrl}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(this.config.tenantId && { "X-Tenant": this.config.tenantId }),
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        throw new Error(`Authentication failed: ${response.statusText}`);
      }

      const data = await response.json();
      const { token } = data;

      if (!token) {
        throw new Error("No token received from server");
      }

      // Store token
      localStorage.setItem(this.config.tokenStorageKey!, token);

      // Get user info from token
      const user = await this.getUserFromToken(token);
      this.updateState({ user, status: "authenticated" });
    } catch (error) {
      this.updateState({ user: null, status: "unauthenticated" });
      throw error;
    }
  }

  async signOut(): Promise<void> {
    // Clear stored data
    localStorage.removeItem(this.config.tokenStorageKey!);
    localStorage.removeItem(this.config.userStorageKey!);

    this.updateState({ user: null, status: "unauthenticated" });
  }

  async getToken(): Promise<string | null> {
    const token = localStorage.getItem(this.config.tokenStorageKey!);
    if (!token || this.isTokenExpired(token)) {
      return null;
    }
    return token;
  }

  async refreshToken(): Promise<string | null> {
    // For JWT provider, there may be no refresh flow; return current token if valid
    return this.getToken();
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
        email: payload.email ?? "",
        name: payload.name,
        avatar: payload.picture,
        metadata: { provider: "jwt", subject: payload.sub },
        credits: { balance: 0, reserved: 0 },
      };
    } catch (error) {
      console.error("Failed to parse user from token:", error);
      return null;
    }
  }

  /**
   * Parse a JWT and return its payload, with robust error handling.
   */
  private parseJWT(token: string): JWTPayload {
    const parts = token.split(".");
    if (parts.length !== 3) {
      throw new Error(
        "Invalid JWT format: token must have exactly 3 parts separated by dots"
      );
    }

    try {
      const payloadJson = this.base64UrlDecode(parts[1]);
      const payload = JSON.parse(payloadJson);

      if (typeof payload !== "object" || payload === null) {
        throw new Error("Invalid JWT payload: payload must be a JSON object");
      }

      return payload;
    } catch (err) {
      if (err instanceof Error && err.message.startsWith("Invalid JWT")) {
        // Re-throw our own validation errors
        throw err;
      }
      throw new Error(
        "Failed to decode or parse JWT payload: " +
          (err instanceof Error ? err.message : String(err))
      );
    }
  }

  /**
   * Decodes a base64url-encoded string.
   */
  private base64UrlDecode(input: string): string {
    // Replace non-url compatible chars with base64 standard chars
    input = input.replace(/-/g, "+").replace(/_/g, "/");

    // Pad out with standard base64 required padding characters
    const pad = input.length % 4;
    if (pad) {
      if (pad === 1) {
        throw new Error("Invalid base64url encoding: incorrect padding");
      }
      input += "=".repeat(4 - pad);
    }

    try {
      return atob(input);
    } catch (e) {
      throw new Error(
        "Invalid base64url encoding: " +
          (e instanceof Error ? e.message : String(e))
      );
    }
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
    this.listeners.forEach((listener) => listener(this.currentState));
  }
}

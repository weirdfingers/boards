/**
 * Clerk authentication provider.
 */

import { BaseAuthProvider, AuthState, User } from "@weirdfingers/boards";
import type { ClerkConfig } from "./types";

export class ClerkAuthProvider extends BaseAuthProvider {
  protected config: ClerkConfig;
  private listeners: ((state: AuthState) => void)[] = [];
  private currentState: AuthState;
  private clerk: any; // Will be typed properly when @clerk/clerk-js is available

  constructor(config: ClerkConfig) {
    super(config);
    this.config = config;

    this.currentState = {
      user: null,
      status: "loading",
      signIn: this.signIn.bind(this) as any,
      signOut: this.signOut.bind(this),
      getToken: this.getToken.bind(this),
      refreshToken: async () => null,
    };
  }

  async initialize(): Promise<void> {
    try {
      // Dynamically import Clerk
      const Clerk = (await import("@clerk/clerk-js")).default;

      this.clerk = new Clerk(this.config.publishableKey);

      await this.clerk.load({
        ...this.config.options,
      });

      // Set up auth state listener
      this.clerk.addListener(this.handleClerkUpdate.bind(this));

      // Get initial state
      this.handleClerkUpdate();
    } catch (error) {
      console.error("Failed to initialize Clerk:", error);
      this.updateState({ user: null, status: "unauthenticated" });
      throw error;
    }
  }

  async getAuthState(): Promise<AuthState> {
    return this.currentState;
  }

  async signIn(
    options: {
      strategy?:
        | "oauth_google"
        | "oauth_github"
        | "oauth_discord"
        | "email_code"
        | "password";
      identifier?: string; // email or username
      password?: string;
      code?: string;
      redirectUrl?: string;
      [key: string]: unknown;
    } = {}
  ): Promise<void> {
    if (!this.clerk) {
      throw new Error("Clerk not initialized");
    }

    this.updateState({ status: "loading" });

    try {
      // OAuth strategies
      if (options.strategy?.startsWith("oauth_")) {
        await this.clerk.authenticateWithRedirect({
          strategy: options.strategy,
          redirectUrl: options.redirectUrl || window.location.href,
          redirectUrlComplete: options.redirectUrl || window.location.origin,
        });
        return; // Redirects, so we don't update state here
      }

      // Email code strategy
      if (options.strategy === "email_code" && options.identifier) {
        const signIn = await this.clerk.client.signIn.create({
          identifier: options.identifier,
        });

        await signIn.prepareFirstFactor({
          strategy: "email_code",
          emailAddressId: signIn.supportedFirstFactors[0].emailAddressId,
        });

        // Return so user can enter code
        this.updateState({ status: "unauthenticated" });
        return;
      }

      // Password strategy
      if (
        options.strategy === "password" &&
        options.identifier &&
        options.password
      ) {
        const signIn = await this.clerk.client.signIn.create({
          identifier: options.identifier,
          password: options.password,
        });

        if (signIn.status === "complete") {
          await this.clerk.setActive({ session: signIn.createdSessionId });
          return; // State will update via listener
        }

        throw new Error("Sign in incomplete");
      }

      // Default: open Clerk sign-in modal
      await this.clerk.openSignIn({
        redirectUrl: options.redirectUrl || window.location.href,
      });
    } catch (error) {
      this.updateState({ user: null, status: "unauthenticated" });
      throw error;
    }
  }

  async signOut(): Promise<void> {
    if (!this.clerk) {
      throw new Error("Clerk not initialized");
    }

    await this.clerk.signOut();
    // State will update via listener
  }

  async getToken(): Promise<string | null> {
    if (!this.clerk || !this.clerk.session) return null;

    try {
      return await this.clerk.session.getToken();
    } catch (error) {
      console.error("Failed to get token:", error);
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
    if (this.clerk) {
      this.clerk.removeListener(this.handleClerkUpdate.bind(this));
    }
  }

  private handleClerkUpdate(): void {
    if (!this.clerk) return;

    if (this.clerk.user) {
      const user: User = {
        id: this.clerk.user.id,
        email: this.clerk.user.primaryEmailAddress?.emailAddress,
        name:
          this.clerk.user.fullName ||
          this.clerk.user.firstName ||
          this.clerk.user.username ||
          this.clerk.user.primaryEmailAddress?.emailAddress?.split("@")[0],
        avatar: this.clerk.user.imageUrl,
        metadata: { provider: "clerk", subject: this.clerk.user.id },
        credits: { balance: 0, reserved: 0 },
      };

      this.updateState({ user, status: "authenticated" });
    } else {
      this.updateState({ user: null, status: "unauthenticated" });
    }
  }

  private updateState(updates: Partial<AuthState>): void {
    this.currentState = { ...this.currentState, ...updates };
    this.listeners.forEach((listener) => listener(this.currentState));
  }

  /**
   * Get the underlying Clerk instance for advanced operations.
   */
  getClerkInstance() {
    return this.clerk;
  }

  /**
   * Open Clerk user profile modal.
   */
  async openUserProfile(): Promise<void> {
    if (!this.clerk) {
      throw new Error("Clerk not initialized");
    }

    await this.clerk.openUserProfile();
  }

  /**
   * Open Clerk organization switcher.
   */
  async openOrganizationSwitcher(): Promise<void> {
    if (!this.clerk) {
      throw new Error("Clerk not initialized");
    }

    await this.clerk.openOrganizationSwitcher();
  }

  /**
   * Verify an email code (after email_code sign in).
   */
  async verifyEmailCode(code: string): Promise<void> {
    if (!this.clerk) {
      throw new Error("Clerk not initialized");
    }

    const signIn = this.clerk.client.signIn;
    if (!signIn) {
      throw new Error("No active sign in attempt");
    }

    const result = await signIn.attemptFirstFactor({
      strategy: "email_code",
      code,
    });

    if (result.status === "complete") {
      await this.clerk.setActive({ session: result.createdSessionId });
    } else {
      throw new Error("Verification failed");
    }
  }
}

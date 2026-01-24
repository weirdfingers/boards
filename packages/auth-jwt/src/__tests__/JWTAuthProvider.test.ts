/**
 * Tests for JWTAuthProvider.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { JWTAuthProvider } from "../JWTAuthProvider";

// Mock localStorage
const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};

Object.defineProperty(window, "localStorage", {
  value: mockLocalStorage,
});

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("JWTAuthProvider", () => {
  let provider: JWTAuthProvider;

  beforeEach(() => {
    vi.clearAllMocks();
    provider = new JWTAuthProvider({
      apiUrl: "http://localhost:3033/api",
      tenantId: "test-tenant",
    });
  });

  afterEach(() => {
    provider.destroy();
  });

  describe("initialization", () => {
    it("should restore user from valid stored token", async () => {
      const validToken = createMockJWT({
        sub: "user-123",
        email: "test@example.com",
        name: "Test User",
        exp: Math.floor(Date.now() / 1000) + 3600, // 1 hour from now
      });

      mockLocalStorage.getItem.mockReturnValue(validToken);

      await provider.initialize();
      const state = await provider.getAuthState();

      expect(state.status).toBe("authenticated");
      expect(state.user).toEqual({
        id: "user-123",
        email: "test@example.com",
        name: "Test User",
        avatar: undefined,
        metadata: {
          provider: "jwt",
          subject: "user-123",
        },
        credits: {
          balance: 0,
          reserved: 0,
        },
      });
    });

    it("should not restore user from expired token", async () => {
      const expiredToken = createMockJWT({
        sub: "user-123",
        exp: Math.floor(Date.now() / 1000) - 3600, // 1 hour ago
      });

      mockLocalStorage.getItem.mockReturnValue(expiredToken);

      await provider.initialize();
      const state = await provider.getAuthState();

      expect(state.status).toBe("unauthenticated");
      expect(state.user).toBeNull();
    });

    it("should handle no stored token", async () => {
      mockLocalStorage.getItem.mockReturnValue(null);

      await provider.initialize();
      const state = await provider.getAuthState();

      expect(state.status).toBe("unauthenticated");
      expect(state.user).toBeNull();
    });

    it("should handle invalid stored token", async () => {
      mockLocalStorage.getItem.mockReturnValue("invalid-jwt-token");
      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      await provider.initialize();
      const state = await provider.getAuthState();

      expect(state.status).toBe("unauthenticated");
      expect(state.user).toBeNull();
      expect(consoleSpy).toHaveBeenCalled();

      consoleSpy.mockRestore();
    });
  });

  describe("signIn", () => {
    it("should sign in successfully with valid credentials", async () => {
      const mockToken = createMockJWT({
        sub: "user-123",
        email: "test@example.com",
        name: "Test User",
        exp: Math.floor(Date.now() / 1000) + 3600,
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ token: mockToken }),
      });

      await provider.signIn({
        email: "test@example.com",
        password: "password123",
      });

      expect(fetch).toHaveBeenCalledWith(
        "http://localhost:3033/api/auth/login",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Tenant": "test-tenant",
          },
          body: JSON.stringify({
            email: "test@example.com",
            password: "password123",
          }),
        }
      );

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        "boards_jwt_token",
        mockToken
      );

      const state = await provider.getAuthState();
      expect(state.status).toBe("authenticated");
    });

    it("should handle sign in failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Unauthorized",
      });

      await expect(
        provider.signIn({
          email: "wrong@example.com",
          password: "wrongpassword",
        })
      ).rejects.toThrow("Authentication failed: Unauthorized");

      const state = await provider.getAuthState();
      expect(state.status).toBe("unauthenticated");
    });

    it("should handle network error", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      await expect(
        provider.signIn({
          email: "test@example.com",
          password: "password123",
        })
      ).rejects.toThrow("Network error");
    });

    it("should handle missing token in response", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}), // No token in response
      });

      await expect(
        provider.signIn({
          email: "test@example.com",
          password: "password123",
        })
      ).rejects.toThrow("No token received from server");
    });
  });

  describe("signOut", () => {
    it("should sign out and clear stored data", async () => {
      await provider.signOut();

      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(
        "boards_jwt_token"
      );
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(
        "boards_user_info"
      );

      const state = await provider.getAuthState();
      expect(state.status).toBe("unauthenticated");
      expect(state.user).toBeNull();
    });
  });

  describe("getToken", () => {
    it("should return valid stored token", async () => {
      const validToken = createMockJWT({
        sub: "user-123",
        exp: Math.floor(Date.now() / 1000) + 3600,
      });

      mockLocalStorage.getItem.mockReturnValue(validToken);

      const token = await provider.getToken();
      expect(token).toBe(validToken);
    });

    it("should return null for expired token", async () => {
      const expiredToken = createMockJWT({
        sub: "user-123",
        exp: Math.floor(Date.now() / 1000) - 3600,
      });

      mockLocalStorage.getItem.mockReturnValue(expiredToken);

      const token = await provider.getToken();
      expect(token).toBeNull();
    });

    it("should return null when no token stored", async () => {
      mockLocalStorage.getItem.mockReturnValue(null);

      const token = await provider.getToken();
      expect(token).toBeNull();
    });
  });

  describe("auth state change listeners", () => {
    it("should notify listeners on state change", async () => {
      const mockCallback = vi.fn();
      const unsubscribe = provider.onAuthStateChange(mockCallback);

      const mockToken = createMockJWT({
        sub: "user-123",
        email: "test@example.com",
        exp: Math.floor(Date.now() / 1000) + 3600,
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ token: mockToken }),
      });

      await provider.signIn({
        email: "test@example.com",
        password: "password123",
      });

      expect(mockCallback).toHaveBeenCalledWith(
        expect.objectContaining({
          status: "loading",
        })
      );

      expect(mockCallback).toHaveBeenCalledWith(
        expect.objectContaining({
          status: "authenticated",
          user: expect.objectContaining({
            id: "user-123",
            email: "test@example.com",
          }),
        })
      );

      unsubscribe();
    });

    it("should handle unsubscribe correctly", async () => {
      const mockCallback = vi.fn();
      const unsubscribe = provider.onAuthStateChange(mockCallback);

      unsubscribe();
      mockCallback.mockClear();

      await provider.signOut();

      expect(mockCallback).not.toHaveBeenCalled();
    });
  });

  describe("configuration", () => {
    it("should use custom storage keys", () => {
      const customProvider = new JWTAuthProvider({
        apiUrl: "http://localhost:3033/api",
        tokenStorageKey: "custom_token_key",
        userStorageKey: "custom_user_key",
      });

      expect(customProvider["config"].tokenStorageKey).toBe("custom_token_key");
      expect(customProvider["config"].userStorageKey).toBe("custom_user_key");
    });

    it("should use default storage keys", () => {
      expect(provider["config"].tokenStorageKey).toBe("boards_jwt_token");
      expect(provider["config"].userStorageKey).toBe("boards_user_info");
    });
  });
});

// Helper function to create mock JWT tokens
interface MockJWTPayload {
  sub: string;
  email?: string;
  name?: string;
  picture?: string;
  exp: number;
}

function createMockJWT(payload: MockJWTPayload): string {
  const header = { alg: "HS256", typ: "JWT" };
  const encodedHeader = btoa(JSON.stringify(header));
  const encodedPayload = btoa(JSON.stringify(payload));
  const signature = "mock-signature";

  return `${encodedHeader}.${encodedPayload}.${signature}`;
}

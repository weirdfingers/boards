/**
 * Tests for NoAuthProvider.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { NoAuthProvider } from '../none';

// Mock console.warn to avoid warnings in tests
const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

describe('NoAuthProvider', () => {
  let provider: NoAuthProvider;

  beforeEach(() => {
    consoleSpy.mockClear();
    provider = new NoAuthProvider({
      defaultUserId: 'test-user',
      defaultEmail: 'test@example.com',
      defaultDisplayName: 'Test User',
    });
  });

  afterEach(() => {
    provider.destroy();
  });

  it('should initialize with default user', async () => {
    await provider.initialize();
    const state = await provider.getAuthState();
    
    expect(state.status).toBe('authenticated');
    expect(state.user).toEqual({
      id: 'test-user',
      email: 'test@example.com',
      name: 'Test User',
      avatar: undefined,
      metadata: { provider: 'none' },
      credits: {
        balance: 1000,
        reserved: 0,
      },
    });
  });

  it('should show warning on initialization', () => {
    new NoAuthProvider();
    expect(consoleSpy).toHaveBeenCalledWith(
      '🚨 [AUTH] NoAuthProvider is active - authentication is disabled!',
      expect.objectContaining({
        environment: 'test',
        message: 'This should ONLY be used in development environments',
        provider: 'none',
      })
    );
  });

  it('should handle signIn as no-op', async () => {
    await provider.initialize();
    const infoSpy = vi.spyOn(console, 'info').mockImplementation(() => {});
    
    await provider.signIn({ email: 'test@example.com', password: 'password' });
    
    expect(infoSpy).toHaveBeenCalledWith(
      '[AUTH] SignIn called in no-auth mode - no action taken',
      expect.objectContaining({
        provider: 'none',
        action: 'signIn',
        status: 'ignored',
      })
    );
    
    const state = await provider.getAuthState();
    expect(state.status).toBe('authenticated');
    
    infoSpy.mockRestore();
  });

  it('should handle signOut as no-op', async () => {
    await provider.initialize();
    const infoSpy = vi.spyOn(console, 'info').mockImplementation(() => {});
    
    await provider.signOut();
    
    expect(infoSpy).toHaveBeenCalledWith(
      '[AUTH] SignOut called in no-auth mode - no action taken',
      expect.objectContaining({
        provider: 'none',
        action: 'signOut',
        status: 'ignored',
      })
    );
    
    const state = await provider.getAuthState();
    expect(state.status).toBe('authenticated'); // Still authenticated
    
    infoSpy.mockRestore();
  });

  it('should return fake token', async () => {
    await provider.initialize();
    const token = await provider.getToken();
    
    expect(token).toBe('dev-token|no-auth-mode|always-valid');
  });

  it('should return current user', async () => {
    await provider.initialize();
    const user = await provider.getUser();
    
    expect(user).toEqual({
      id: 'test-user',
      email: 'test@example.com',
      name: 'Test User',
      avatar: undefined,
      metadata: { provider: 'none' },
      credits: {
        balance: 1000,
        reserved: 0,
      },
    });
  });

  it('should notify listeners immediately', async () => {
    await provider.initialize();
    const mockCallback = vi.fn();
    
    const unsubscribe = provider.onAuthStateChange(mockCallback);
    
    // Should be called immediately with current state
    expect(mockCallback).toHaveBeenCalledWith({
      user: expect.objectContaining({
        id: 'test-user',
        metadata: { provider: 'none' },
      }),
      status: 'authenticated',
      signIn: expect.any(Function),
      signOut: expect.any(Function),
      getToken: expect.any(Function),
      refreshToken: expect.any(Function),
    });
    
    unsubscribe();
  });

  it('should handle unsubscribe correctly', async () => {
    await provider.initialize();
    const mockCallback = vi.fn();
    
    const unsubscribe = provider.onAuthStateChange(mockCallback);
    mockCallback.mockClear();
    
    unsubscribe();
    
    // Simulate state change
    await provider.signIn();
    
    // Callback should not be called after unsubscribe
    expect(mockCallback).not.toHaveBeenCalled();
  });

  it('should use default configuration', () => {
    const defaultProvider = new NoAuthProvider();
    
    expect(defaultProvider['config'].defaultUserId).toBe('dev-user');
    expect(defaultProvider['config'].defaultEmail).toBe('dev@example.com');
    expect(defaultProvider['config'].defaultDisplayName).toBe('Development User');
  });

  it('should handle custom tenant ID', () => {
    const provider = new NoAuthProvider({
      tenantId: 'custom-tenant',
    });
    
    expect(provider['getTenantId']()).toBe('custom-tenant');
  });

  it('should clean up listeners on destroy', async () => {
    await provider.initialize();
    const mockCallback = vi.fn();
    
    provider.onAuthStateChange(mockCallback);
    expect(provider['listeners']).toHaveLength(1);
    
    await provider.destroy();
    expect(provider['listeners']).toHaveLength(0);
  });
});
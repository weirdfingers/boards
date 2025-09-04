/**
 * React context for authentication.
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { AuthContextValue, AuthState } from './types';
import { BaseAuthProvider } from './providers/base';

const AuthContext = createContext<AuthContextValue | null>(null);

interface AuthProviderProps {
  provider: BaseAuthProvider;
  children: React.ReactNode;
}

export function AuthProvider({ provider, children }: AuthProviderProps) {
  const [state, setState] = useState<AuthState>({
    user: null,
    status: 'loading',
    signIn: async () => {},
    signOut: async () => {},
    getToken: async () => null,
    refreshToken: async () => null,
  });
  const [isInitializing, setIsInitializing] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  useEffect(() => {
    let mounted = true;
    let unsubscribe: (() => void) | null = null;

    const initializeAuth = async () => {
      try {
        await provider.initialize();
        
        if (!mounted) return;

        // Set up state change listener
        unsubscribe = provider.onAuthStateChange((newState) => {
          if (mounted) {
            setState(newState);
          }
        });

        // Get initial state
        const initialState = await provider.getAuthState();
        if (mounted) {
          setState(initialState);
          setIsInitializing(false);
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err : new Error('Auth initialization failed'));
          setIsInitializing(false);
        }
      }
    };

    initializeAuth();

    return () => {
      mounted = false;
      if (unsubscribe) {
        unsubscribe();
      }
    };
  }, [provider]);

  // Clean up provider on unmount
  useEffect(() => {
    return () => {
      provider.destroy();
    };
  }, [provider]);

  const contextValue: AuthContextValue = {
    ...state,
    isInitializing,
    error,
    clearError,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export function useAuthOptional(): AuthContextValue | null {
  return useContext(AuthContext);
}
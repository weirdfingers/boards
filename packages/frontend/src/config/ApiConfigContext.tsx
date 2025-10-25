/**
 * API configuration context for providing backend URLs to hooks.
 */

import { createContext, useContext, ReactNode } from "react";

export interface ApiConfig {
  /**
   * Base URL for the backend API (e.g., "http://localhost:8088")
   * Used for REST endpoints like SSE streams
   */
  apiUrl: string;
  /**
   * GraphQL endpoint URL (e.g., "http://localhost:8088/graphql")
   */
  graphqlUrl: string;
  /**
   * WebSocket URL for GraphQL subscriptions
   */
  subscriptionUrl?: string;
}

const ApiConfigContext = createContext<ApiConfig | null>(null);

interface ApiConfigProviderProps {
  children: ReactNode;
  config: ApiConfig;
}

export function ApiConfigProvider({
  children,
  config,
}: ApiConfigProviderProps) {
  return (
    <ApiConfigContext.Provider value={config}>
      {children}
    </ApiConfigContext.Provider>
  );
}

export function useApiConfig(): ApiConfig {
  const context = useContext(ApiConfigContext);
  if (!context) {
    throw new Error("useApiConfig must be used within ApiConfigProvider");
  }
  return context;
}

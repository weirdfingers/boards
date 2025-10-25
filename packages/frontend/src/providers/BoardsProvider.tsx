/**
 * Main provider component that sets up GraphQL client and auth context.
 */

import { ReactNode } from "react";
import { Provider as UrqlProvider } from "urql";
import { createGraphQLClient } from "../graphql/client";
import { AuthProvider } from "../auth/context";
import { BaseAuthProvider } from "../auth/providers/base";
import { ApiConfigProvider, ApiConfig } from "../config/ApiConfigContext";

interface BoardsProviderProps {
  children: ReactNode;
  /**
   * Base URL for the backend API (e.g., "http://localhost:8088")
   * Used for REST endpoints like SSE streams
   */
  apiUrl: string;
  /**
   * GraphQL endpoint URL (e.g., "http://localhost:8088/graphql")
   * If not provided, defaults to `${apiUrl}/graphql`
   */
  graphqlUrl?: string;
  /**
   * WebSocket URL for GraphQL subscriptions
   */
  subscriptionUrl?: string;
  authProvider: BaseAuthProvider;
  tenantId?: string;
}

export function BoardsProvider({
  children,
  apiUrl,
  graphqlUrl,
  subscriptionUrl,
  authProvider,
  tenantId,
}: BoardsProviderProps) {
  // Default graphqlUrl if not provided
  const resolvedGraphqlUrl = graphqlUrl || `${apiUrl}/graphql`;

  // Create API config for hooks
  const apiConfig: ApiConfig = {
    apiUrl,
    graphqlUrl: resolvedGraphqlUrl,
    subscriptionUrl,
  };

  // Create the GraphQL client with auth integration
  const client = createGraphQLClient({
    url: resolvedGraphqlUrl,
    subscriptionUrl,
    auth: {
      getToken: () =>
        authProvider.getAuthState().then((state) => state.getToken()),
    },
    tenantId,
  });

  return (
    <AuthProvider provider={authProvider}>
      <ApiConfigProvider config={apiConfig}>
        <UrqlProvider value={client}>{children}</UrqlProvider>
      </ApiConfigProvider>
    </AuthProvider>
  );
}

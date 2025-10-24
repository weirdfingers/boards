/**
 * Main provider component that sets up GraphQL client and auth context.
 */

import { ReactNode } from "react";
import { Provider as UrqlProvider } from "urql";
import { createGraphQLClient } from "../graphql/client";
import { AuthProvider } from "../auth/context";
import { BaseAuthProvider } from "../auth/providers/base";

interface BoardsProviderProps {
  children: ReactNode;
  graphqlUrl: string;
  subscriptionUrl?: string;
  authProvider: BaseAuthProvider;
  tenantId?: string;
}

export function BoardsProvider({
  children,
  graphqlUrl,
  subscriptionUrl,
  authProvider,
  tenantId,
}: BoardsProviderProps) {
  // Create the GraphQL client with auth integration
  const client = createGraphQLClient({
    url: graphqlUrl,
    subscriptionUrl,
    auth: {
      getToken: () =>
        authProvider.getAuthState().then((state) => state.getToken()),
    },
    tenantId,
  });

  return (
    <AuthProvider provider={authProvider}>
      <UrqlProvider value={client}>{children}</UrqlProvider>
    </AuthProvider>
  );
}

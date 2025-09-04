/**
 * GraphQL client configuration with authentication.
 */

import { createClient, fetchExchange, subscriptionExchange } from 'urql';
import { authExchange } from '@urql/exchange-auth';
import { createClient as createWSClient } from 'graphql-ws';

interface AuthState {
  getToken(): Promise<string | null>;
}

interface ClientConfig {
  url: string;
  subscriptionUrl?: string;
  auth: AuthState;
  tenantId?: string;
}

export function createGraphQLClient({ url, subscriptionUrl, auth, tenantId }: ClientConfig) {
  const wsClient = subscriptionUrl 
    ? createWSClient({
        url: subscriptionUrl,
        connectionParams: async () => {
          const token = await auth.getToken();
          const headers: Record<string, string> = {};
          
          if (token) {
            headers.Authorization = `Bearer ${token}`;
          }
          
          if (tenantId) {
            headers['X-Tenant'] = tenantId;
          }
          
          return headers;
        },
      })
    : null;

  return createClient({
    url,
    exchanges: [
      authExchange(async (_utilities) => ({
        addAuthToOperation: (operation) => {
          // For now, use a simpler approach - token will be added via context
          // TODO: Implement proper async token fetching
          return operation;
        },

        willAuthError: () => false,

        didAuthError: (error) => {
          return error.graphQLErrors.some(e => 
            e.extensions?.code === 'UNAUTHENTICATED' ||
            e.extensions?.code === 'UNAUTHORIZED'
          );
        },

        refreshAuth: async () => {
          await auth.getToken();
          return;
        },
      })),
      fetchExchange,
      ...(wsClient ? [subscriptionExchange({ 
        forwardSubscription: (operation) => ({
          subscribe: (sink) => ({
            unsubscribe: wsClient.subscribe({
              query: operation.query || '',
              variables: operation.variables,
            }, sink),
          }),
        })
      })] : []),
    ],
    fetchOptions: () => ({
      // Will be overridden by authExchange
    }),
  });
}
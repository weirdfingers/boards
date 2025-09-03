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
      authExchange(async (utilities) => {
        return {
          addAuthToOperation(operation) {
            const token = operation.context.authToken;
            if (!token) {
              return operation;
            }

            const headers: Record<string, string> = {
              ...operation.context.fetchOptions?.headers,
              Authorization: `Bearer ${token}`,
            };

            if (tenantId) {
              headers['X-Tenant'] = tenantId;
            }

            return utilities.appendHeaders(operation, headers);
          },

          willAuthError() {
            // Check if we should expect an auth error
            return false;
          },

          didAuthError(error) {
            // Check if the error is an auth error
            return error.graphQLErrors.some(e => 
              e.extensions?.code === 'UNAUTHENTICATED' ||
              e.extensions?.code === 'UNAUTHORIZED'
            );
          },

          async refreshAuth() {
            // Get fresh token
            const token = await auth.getToken();
            return { authToken: token };
          },
        };
      }),
      fetchExchange,
      ...(wsClient ? [subscriptionExchange({ forwardSubscription: (operation) => {
        return {
          subscribe: (sink) => ({
            unsubscribe: wsClient.subscribe(operation, sink),
          }),
        };
      }})] : []),
    ],
    fetchOptions: () => ({
      // Will be overridden by authExchange
    }),
  });
}
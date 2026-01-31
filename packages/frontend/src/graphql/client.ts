/**
 * GraphQL client configuration with authentication.
 */

import {
  createClient,
  fetchExchange,
  cacheExchange,
  subscriptionExchange,
  makeOperation,
} from "urql";
import { authExchange } from "@urql/exchange-auth";
import { createClient as createWSClient } from "graphql-ws";

interface AuthState {
  getToken(): Promise<string | null>;
}

interface ClientConfig {
  url: string;
  subscriptionUrl?: string;
  auth: AuthState;
  tenantId?: string;
}

export function createGraphQLClient({
  url,
  subscriptionUrl,
  auth,
  tenantId,
}: ClientConfig) {
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
            headers["X-Tenant"] = tenantId;
          }

          return headers;
        },
      })
    : null;

  return createClient({
    url,
    preferGetMethod: false,
    exchanges: [
      cacheExchange,
      authExchange(async () => {
        // Initialize auth state by fetching token
        let token = await auth.getToken();

        return {
          addAuthToOperation: (operation) => {
            // Build headers
            const headers: Record<string, string> = {};

            if (token) {
              headers.Authorization = `Bearer ${token}`;
            }

            if (tenantId) {
              headers["X-Tenant"] = tenantId;
            }
            const fetchOptions =
              typeof operation.context.fetchOptions === "function"
                ? operation.context.fetchOptions()
                : operation.context.fetchOptions || {};

            // Add headers to operation context
            return makeOperation(operation.kind, operation, {
              ...operation.context,
              fetchOptions: {
                ...operation.context.fetchOptions,
                headers: {
                  ...fetchOptions.headers,
                  ...headers,
                },
              },
            });
          },

          didAuthError: (error) => {
            // Check if error is auth-related
            return error.graphQLErrors.some(
              (e) =>
                e.extensions?.code === "UNAUTHENTICATED" ||
                e.extensions?.code === "UNAUTHORIZED",
            );
          },

          willAuthError: () => {
            // We don't preemptively block requests
            return false;
          },

          refreshAuth: async () => {
            // Re-fetch token on auth error and update the closure variable
            token = await auth.getToken();
          },
        };
      }),
      fetchExchange,
      ...(wsClient
        ? [
            subscriptionExchange({
              forwardSubscription: (operation) => ({
                subscribe: (sink) => ({
                  unsubscribe: wsClient.subscribe(
                    {
                      query: operation.query || "",
                      variables: operation.variables,
                    },
                    sink,
                  ),
                }),
              }),
            }),
          ]
        : []),
    ],
  });
}

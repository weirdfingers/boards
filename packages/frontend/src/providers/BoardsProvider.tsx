/**
 * Main provider component that sets up GraphQL client and auth context.
 */

import { ReactNode } from 'react';
import { Provider as UrqlProvider } from 'urql';
import { createGraphQLClient } from '../graphql/client';
import { AuthProvider } from '../auth/context';
import { BaseAuthProvider } from '../auth/providers/base';

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
  tenantId 
}: BoardsProviderProps) {
  // Create the GraphQL client with auth integration
  const client = createGraphQLClient({
    url: graphqlUrl,
    subscriptionUrl,
    auth: {
      getToken: () => authProvider.getAuthState().then(state => state.getToken()),
    },
    tenantId,
  });

  return (
    <AuthProvider provider={authProvider}>
      <UrqlProvider value={client}>
        {children}
      </UrqlProvider>
    </AuthProvider>
  );
}

// Example usage component
import { useBoards } from '../hooks/useBoards';
import { useAuth } from '../auth/hooks/useAuth';
import { useGeneration } from '../hooks/useGeneration';

export function ExampleUsage() {
  const { boards, loading, createBoard } = useBoards();
  const { user, signIn, signOut } = useAuth();
  const { submit, progress, isGenerating } = useGeneration();

  const handleCreateBoard = async () => {
    try {
      const board = await createBoard({
        title: 'My New Board',
        description: 'Created from the hooks example',
        isPublic: false,
      });
      console.log('Created board:', board);
    } catch (error) {
      console.error('Failed to create board:', error);
    }
  };

  const handleGenerate = async (boardId: string) => {
    try {
      const jobId = await submit({
        provider: 'replicate',
        model: 'stable-diffusion',
        inputs: {
          prompt: 'A beautiful landscape with mountains',
          steps: 50,
        },
        boardId,
      });
      console.log('Started generation:', jobId);
    } catch (error) {
      console.error('Failed to start generation:', error);
    }
  };

  if (loading) return <div>Loading boards...</div>;

  return (
    <div>
      <div>
        <h1>Boards</h1>
        {user ? (
          <div>
            <p>Welcome, {user.name || user.email}!</p>
            <p>Credits: {user.credits.balance - user.credits.reserved}</p>
            <button onClick={signOut}>Sign Out</button>
          </div>
        ) : (
          <button onClick={() => signIn()}>Sign In</button>
        )}
      </div>

      <div>
        <button onClick={handleCreateBoard}>Create Board</button>
        {boards.map((board) => (
          <div key={board.id}>
            <h3>{board.title}</h3>
            <p>{board.description}</p>
            <button onClick={() => handleGenerate(board.id)}>
              Generate Content
            </button>
          </div>
        ))}
      </div>

      {isGenerating && progress && (
        <div>
          <h3>Generation Progress</h3>
          <p>Status: {progress.status}</p>
          <p>Progress: {progress.progress}%</p>
          {progress.estimatedTimeRemaining && (
            <p>ETA: {progress.estimatedTimeRemaining}s</p>
          )}
        </div>
      )}
    </div>
  );
}
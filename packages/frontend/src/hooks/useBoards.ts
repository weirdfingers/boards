/**
 * Hook for managing multiple boards.
 */

import { useCallback, useMemo } from 'react';
import { useQuery, useMutation } from 'urql';
import { GET_BOARDS, CREATE_BOARD, DELETE_BOARD, CreateBoardInput } from '../graphql/operations';

interface Board {
  id: string;
  tenantId: string;
  ownerId: string;
  title: string;
  description?: string;
  isPublic: boolean;
  settings: Record<string, unknown>;
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
  generationCount: number;
  owner: {
    id: string;
    email: string;
    displayName: string;
    avatarUrl?: string;
    createdAt: string;
  };
}

interface UseBoardsOptions {
  limit?: number;
  offset?: number;
  search?: string;
}

interface BoardsHook {
  boards: Board[];
  loading: boolean;
  error: Error | null;
  createBoard: (data: CreateBoardInput) => Promise<Board>;
  deleteBoard: (boardId: string) => Promise<void>;
  searchBoards: (query: string) => Promise<Board[]>;
  refresh: () => Promise<void>;
}

export function useBoards(options: UseBoardsOptions = {}): BoardsHook {
  const { limit = 50, offset = 0, search } = options;
  
  // Query for boards
  const [{ data, fetching, error }, reexecuteQuery] = useQuery({
    query: GET_BOARDS,
    variables: { limit, offset, search },
  });

  // Mutations
  const [, createBoardMutation] = useMutation(CREATE_BOARD);
  const [, deleteBoardMutation] = useMutation(DELETE_BOARD);

  const boards = useMemo(() => data?.boards || [], [data?.boards]);

  const createBoard = useCallback(async (input: CreateBoardInput): Promise<Board> => {
    const result = await createBoardMutation({ input });
    
    if (result.error) {
      throw new Error(result.error.message);
    }
    
    if (!result.data?.createBoard) {
      throw new Error('Failed to create board');
    }

    // Refresh the boards list to include the new board
    reexecuteQuery({ requestPolicy: 'network-only' });
    
    return result.data.createBoard;
  }, [createBoardMutation, reexecuteQuery]);

  const deleteBoard = useCallback(async (boardId: string): Promise<void> => {
    const result = await deleteBoardMutation({ id: boardId });
    
    if (result.error) {
      throw new Error(result.error.message);
    }
    
    if (!result.data?.deleteBoard?.success) {
      throw new Error('Failed to delete board');
    }

    // Refresh the boards list to remove the deleted board
    reexecuteQuery({ requestPolicy: 'network-only' });
  }, [deleteBoardMutation, reexecuteQuery]);

  const searchBoards = useCallback(async (query: string): Promise<Board[]> => {
    // For search, we trigger a new query execution
    reexecuteQuery({
      variables: { limit, offset: 0, search: query },
      requestPolicy: 'network-only'
    });
    
    // Return current boards - this is a simplified implementation
    // In practice, you might want to use a separate query for search
    return boards.filter((board: Board) => 
      board.title.toLowerCase().includes(query.toLowerCase()) ||
      board.description?.toLowerCase().includes(query.toLowerCase())
    );
  }, [reexecuteQuery, limit, boards]);

  const refresh = useCallback(async (): Promise<void> => {
    await reexecuteQuery({ requestPolicy: 'network-only' });
  }, [reexecuteQuery]);

  return {
    boards,
    loading: fetching,
    error: error ? new Error(error.message) : null,
    createBoard,
    deleteBoard,
    searchBoards,
    refresh,
  };
}
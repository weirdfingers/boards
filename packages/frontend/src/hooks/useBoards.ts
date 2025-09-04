/**
 * Hook for managing multiple boards.
 */

import { useCallback, useMemo, useState, useEffect } from 'react';
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
  setSearchQuery: (query: string) => void;
  searchQuery: string;
}

// Custom hook for debouncing search queries
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

export function useBoards(options: UseBoardsOptions = {}): BoardsHook {
  const { limit = 50, offset = 0 } = options;
  const [searchQuery, setSearchQuery] = useState(options.search || '');
  
  // Debounce search query to avoid excessive API calls
  const debouncedSearchQuery = useDebounce(searchQuery, 300);
  
  // Query for boards with debounced search
  const [{ data, fetching, error }, reexecuteQuery] = useQuery({
    query: GET_BOARDS,
    variables: { limit, offset, search: debouncedSearchQuery },
  });

  // Mutations
  const [, createBoardMutation] = useMutation(CREATE_BOARD);
  const [, deleteBoardMutation] = useMutation(DELETE_BOARD);

  const boards = useMemo(() => data?.boards || [], [data?.boards]);

  const createBoard = useCallback(async (input: CreateBoardInput): Promise<Board> => {

    // Retry logic for network failures
    let lastError: Error | null = null;
    const maxRetries = 3;
    
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        const result = await createBoardMutation({ input });
        
        if (result.error) {
          throw new Error(result.error.message);
        }
        
        if (!result.data?.createBoard) {
          throw new Error('Failed to create board');
        }

        return result.data.createBoard;
      } catch (error) {
        lastError = error instanceof Error ? error : new Error('Unknown error');
        
        // Don't retry on certain types of errors
        if (lastError.message.includes('validation') || 
            lastError.message.includes('unauthorized') ||
            lastError.message.includes('forbidden')) {
          throw lastError;
        }
        
        // If this was the last attempt, throw the error
        if (attempt === maxRetries) {
          throw lastError;
        }
        
        // Wait with exponential backoff before retrying
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt - 1) * 1000));
      }
    }
    
    throw lastError || new Error('Failed to create board after retries');
  }, [createBoardMutation]);

  const deleteBoard = useCallback(async (boardId: string): Promise<void> => {
    const result = await deleteBoardMutation({ id: boardId });
    
    if (result.error) {
      throw new Error(result.error.message);
    }
    
    if (!result.data?.deleteBoard?.success) {
      throw new Error('Failed to delete board');
    }
  }, [deleteBoardMutation]);

  const searchBoards = useCallback(async (query: string): Promise<Board[]> => {
    // Set search query which will trigger debounced search via useEffect
    setSearchQuery(query);
    
    // Return promise that resolves when search completes
    // This is a simplified implementation - in a real app you might want
    // to return the actual search results from the API
    return new Promise((resolve) => {
      // Wait for debounce delay plus a bit more for API response
      setTimeout(() => {
        resolve(boards.filter((board: Board) => 
          board.title.toLowerCase().includes(query.toLowerCase()) ||
          board.description?.toLowerCase().includes(query.toLowerCase())
        ));
      }, 350);
    });
  }, [boards]);

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
    setSearchQuery,
    searchQuery,
  };
}
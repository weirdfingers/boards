/**
 * Hook for managing multiple boards.
 */

import { useCallback, useMemo, useState } from "react";
import { useQuery, useMutation } from "urql";
// import { Cache } from '@urql/core';
import {
  GET_BOARDS,
  CREATE_BOARD,
  DELETE_BOARD,
  CreateBoardInput,
} from "../graphql/operations";

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

export function useBoards(options: UseBoardsOptions = {}): BoardsHook {
  const { limit = 50, offset = 0 } = options;
  const [searchQuery, setSearchQuery] = useState("");

  // Query for boards
  const [{ data, fetching, error }, reexecuteQuery] = useQuery({
    query: GET_BOARDS,
    variables: { limit, offset },
  });

  // Mutations
  const [, createBoardMutation] = useMutation(CREATE_BOARD);
  const [, deleteBoardMutation] = useMutation(DELETE_BOARD);

  const boards = useMemo(() => data?.myBoards || [], [data?.myBoards]);

  const createBoard = useCallback(
    async (input: CreateBoardInput): Promise<Board> => {
      const result = await createBoardMutation({ input });
      if (result.error) {
        throw new Error(result.error.message);
      }
      if (!result.data?.createBoard) {
        throw new Error("Failed to create board");
      }
      return result.data.createBoard;
    },
    [createBoardMutation]
  );

  const deleteBoard = useCallback(
    async (boardId: string): Promise<void> => {
      const result = await deleteBoardMutation({ id: boardId });

      if (result.error) {
        throw new Error(result.error.message);
      }

      if (!result.data?.deleteBoard?.success) {
        throw new Error("Failed to delete board");
      }
      reexecuteQuery({ requestPolicy: "network-only" });
    },
    [deleteBoardMutation, reexecuteQuery]
  );

  const searchBoards = useCallback(
    async (query: string): Promise<Board[]> => {
      // Set search query which will trigger debounced search via useEffect
      setSearchQuery(query);

      // Return promise that resolves when search completes
      // This is a simplified implementation - in a real app you might want
      // to return the actual search results from the API
      return new Promise((resolve) => {
        // Wait for debounce delay plus a bit more for API response
        setTimeout(() => {
          resolve(
            boards.filter(
              (board: Board) =>
                board.title.toLowerCase().includes(query.toLowerCase()) ||
                board.description?.toLowerCase().includes(query.toLowerCase())
            )
          );
        }, 350);
      });
    },
    [boards]
  );

  const refresh = useCallback(async (): Promise<void> => {
    await reexecuteQuery({ requestPolicy: "network-only" });
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

/**
 * Hook for managing a single board.
 */

import { useCallback, useMemo } from "react";
import { useQuery, useMutation } from "urql";
import { useAuth } from "../auth/hooks/useAuth";
import {
  GET_BOARD,
  UPDATE_BOARD,
  DELETE_BOARD,
  ADD_BOARD_MEMBER,
  UPDATE_BOARD_MEMBER_ROLE,
  REMOVE_BOARD_MEMBER,
  UpdateBoardInput,
  BoardRole,
} from "../graphql/operations";

interface User {
  id: string;
  email: string;
  displayName: string;
  avatarUrl?: string;
  createdAt: string;
}

interface BoardMember {
  id: string;
  boardId: string;
  userId: string;
  role: BoardRole;
  invitedBy?: string;
  joinedAt: string;
  user: User;
  inviter?: User;
}

interface Generation {
  id: string;
  boardId: string;
  userId: string;
  generatorName: string;
  artifactType: string;
  status: string;
  progress: number;
  storageUrl?: string | null;
  thumbnailUrl?: string | null;
  inputParams: Record<string, unknown>;
  outputMetadata: Record<string, unknown>;
  errorMessage?: string | null;
  createdAt: string;
  updatedAt: string;
  completedAt?: string | null;
}

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
  owner: User;
  members: BoardMember[];
  generations: Generation[];
}

type MemberRole = BoardRole;

interface BoardPermissions {
  canEdit: boolean;
  canDelete: boolean;
  canAddMembers: boolean;
  canRemoveMembers: boolean;
  canGenerate: boolean;
  canExport: boolean;
}

interface ShareLinkOptions {
  expiresIn?: number;
  permissions?: string[];
}

interface ShareLink {
  id: string;
  url: string;
  expiresAt?: string;
  permissions: string[];
}

interface BoardHook {
  board: Board | null;
  members: BoardMember[];
  permissions: BoardPermissions;
  loading: boolean;
  error: Error | null;

  // Board operations
  updateBoard: (updates: Partial<UpdateBoardInput>) => Promise<Board>;
  deleteBoard: () => Promise<void>;
  refresh: () => Promise<void>;

  // Member management
  addMember: (email: string, role: MemberRole) => Promise<BoardMember>;
  removeMember: (memberId: string) => Promise<void>;
  updateMemberRole: (
    memberId: string,
    role: MemberRole
  ) => Promise<BoardMember>;

  // Sharing (placeholder - would need backend implementation)
  generateShareLink: (options: ShareLinkOptions) => Promise<ShareLink>;
  revokeShareLink: (linkId: string) => Promise<void>;
}

export function useBoard(boardId: string): BoardHook {
  const { user } = useAuth();

  // Query for board data
  const [{ data, fetching, error }, reexecuteQuery] = useQuery({
    query: GET_BOARD,
    variables: { id: boardId },
    pause: !boardId,
    requestPolicy: "cache-and-network", // Always fetch fresh data while showing cached data
  });

  // Mutations
  const [, updateBoardMutation] = useMutation(UPDATE_BOARD);
  const [, deleteBoardMutation] = useMutation(DELETE_BOARD);
  const [, addMemberMutation] = useMutation(ADD_BOARD_MEMBER);
  const [, updateMemberRoleMutation] = useMutation(UPDATE_BOARD_MEMBER_ROLE);
  const [, removeMemberMutation] = useMutation(REMOVE_BOARD_MEMBER);

  const board = useMemo(() => data?.board || null, [data?.board]);
  const members = useMemo(() => board?.members || [], [board?.members]);

  // Calculate permissions based on user role
  const permissions = useMemo((): BoardPermissions => {
    if (!board || !user) {
      return {
        canEdit: false,
        canDelete: false,
        canAddMembers: false,
        canRemoveMembers: false,
        canGenerate: false,
        canExport: false,
      };
    }

    // Check if user is the board owner
    const isOwner = board.ownerId === user.id;

    // Find user's role in board members
    const userMember = members.find(
      (member: BoardMember) => member.userId === user.id
    );
    const userRole = userMember?.role;

    const isAdmin = userRole === BoardRole.ADMIN;
    const isEditor = userRole === BoardRole.EDITOR || isAdmin;
    const isViewer = userRole === BoardRole.VIEWER || isEditor;

    return {
      canEdit: isOwner || isAdmin || isEditor,
      canDelete: isOwner,
      canAddMembers: isOwner || isAdmin,
      canRemoveMembers: isOwner || isAdmin,
      canGenerate: isOwner || isAdmin || isEditor,
      canExport: isViewer, // Even viewers can export
    };
  }, [board, user, members]);

  const updateBoard = useCallback(
    async (updates: Partial<UpdateBoardInput>): Promise<Board> => {
      if (!boardId) {
        throw new Error("Board ID is required");
      }

      const result = await updateBoardMutation({
        id: boardId,
        input: updates,
      });

      if (result.error) {
        throw new Error(result.error.message);
      }

      if (!result.data?.updateBoard) {
        throw new Error("Failed to update board");
      }

      return result.data.updateBoard;
    },
    [boardId, updateBoardMutation]
  );

  const deleteBoard = useCallback(async (): Promise<void> => {
    if (!boardId) {
      throw new Error("Board ID is required");
    }

    const result = await deleteBoardMutation({ id: boardId });

    if (result.error) {
      throw new Error(result.error.message);
    }

    if (!result.data?.deleteBoard?.success) {
      throw new Error("Failed to delete board");
    }
  }, [boardId, deleteBoardMutation]);

  const addMember = useCallback(
    async (email: string, role: MemberRole): Promise<BoardMember> => {
      if (!boardId) {
        throw new Error("Board ID is required");
      }

      const result = await addMemberMutation({
        boardId,
        email,
        role,
      });

      if (result.error) {
        throw new Error(result.error.message);
      }

      if (!result.data?.addBoardMember) {
        throw new Error("Failed to add member");
      }

      // Refresh board data to get updated members list
      reexecuteQuery({ requestPolicy: "network-only" });

      return result.data.addBoardMember;
    },
    [boardId, addMemberMutation, reexecuteQuery]
  );

  const removeMember = useCallback(
    async (memberId: string): Promise<void> => {
      const result = await removeMemberMutation({ id: memberId });

      if (result.error) {
        throw new Error(result.error.message);
      }

      if (!result.data?.removeBoardMember?.success) {
        throw new Error("Failed to remove member");
      }

      // Refresh board data to get updated members list
      reexecuteQuery({ requestPolicy: "network-only" });
    },
    [removeMemberMutation, reexecuteQuery]
  );

  const updateMemberRole = useCallback(
    async (memberId: string, role: MemberRole): Promise<BoardMember> => {
      const result = await updateMemberRoleMutation({
        id: memberId,
        role,
      });

      if (result.error) {
        throw new Error(result.error.message);
      }

      if (!result.data?.updateBoardMemberRole) {
        throw new Error("Failed to update member role");
      }

      // Refresh board data to get updated members list
      reexecuteQuery({ requestPolicy: "network-only" });

      return result.data.updateBoardMemberRole;
    },
    [updateMemberRoleMutation, reexecuteQuery]
  );

  // Placeholder implementations for sharing features
  const generateShareLink = useCallback(
    async (_options: ShareLinkOptions): Promise<ShareLink> => {
      // TODO: Implement share link generation
      throw new Error("Share links not implemented yet");
    },
    []
  );

  const revokeShareLink = useCallback(
    async (_linkId: string): Promise<void> => {
      // TODO: Implement share link revocation
      throw new Error("Share link revocation not implemented yet");
    },
    []
  );

  const refresh = useCallback(async (): Promise<void> => {
    await reexecuteQuery({ requestPolicy: "network-only" });
  }, [reexecuteQuery]);

  return {
    board,
    members,
    permissions,
    loading: fetching,
    error: error ? new Error(error.message) : null,
    updateBoard,
    deleteBoard,
    refresh,
    addMember,
    removeMember,
    updateMemberRole,
    generateShareLink,
    revokeShareLink,
  };
}

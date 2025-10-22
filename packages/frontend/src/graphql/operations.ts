/**
 * GraphQL queries and mutations for the Boards API.
 */

import { gql } from "urql";

// Fragments for reusable query parts
export const USER_FRAGMENT = gql`
  fragment UserFragment on User {
    id
    email
    displayName
    avatarUrl
    createdAt
  }
`;

export const BOARD_FRAGMENT = gql`
  fragment BoardFragment on Board {
    id
    tenantId
    ownerId
    title
    description
    isPublic
    settings
    metadata
    createdAt
    updatedAt
    generationCount
  }
`;

export const GENERATION_FRAGMENT = gql`
  fragment GenerationFragment on Generation {
    id
    boardId
    userId
    providerName
    generatorName
    artifactType
    status
    progress
    storageUrl
    thumbnailUrl
    inputParams
    outputMetadata
    errorMessage
    createdAt
    updatedAt
    completedAt
  }
`;

// Auth queries
export const GET_CURRENT_USER = gql`
  ${USER_FRAGMENT}
  query GetCurrentUser {
    me {
      ...UserFragment
    }
  }
`;

// Board queries
export const GET_BOARDS = gql`
  ${BOARD_FRAGMENT}
  ${USER_FRAGMENT}
  query GetBoards($limit: Int, $offset: Int) {
    myBoards(limit: $limit, offset: $offset) {
      ...BoardFragment
      owner {
        ...UserFragment
      }
    }
  }
`;

export const GET_BOARD = gql`
  ${BOARD_FRAGMENT}
  ${USER_FRAGMENT}
  ${GENERATION_FRAGMENT}
  query GetBoard($id: UUID!) {
    board(id: $id) {
      ...BoardFragment
      owner {
        ...UserFragment
      }
      members {
        id
        boardId
        userId
        role
        invitedBy
        joinedAt
        user {
          ...UserFragment
        }
        inviter {
          ...UserFragment
        }
      }
      generations(limit: 10) {
        ...GenerationFragment
      }
    }
  }
`;

// Generator queries
export const GET_GENERATORS = gql`
  query GetGenerators($artifactType: String) {
    generators(artifactType: $artifactType) {
      name
      description
      artifactType
      inputSchema
      outputSchema
    }
  }
`;

// Generation queries
export const GET_GENERATIONS = gql`
  ${GENERATION_FRAGMENT}
  query GetGenerations($boardId: UUID, $limit: Int, $offset: Int) {
    generations(boardId: $boardId, limit: $limit, offset: $offset) {
      ...GenerationFragment
      board {
        id
        title
      }
      user {
        ...UserFragment
      }
    }
  }
`;

export const GET_GENERATION = gql`
  ${GENERATION_FRAGMENT}
  query GetGeneration($id: UUID!) {
    generation(id: $id) {
      ...GenerationFragment
      board {
        ...BoardFragment
      }
      user {
        ...UserFragment
      }
    }
  }
`;

// Board mutations
export const CREATE_BOARD = gql`
  ${BOARD_FRAGMENT}
  ${USER_FRAGMENT}
  mutation CreateBoard($input: CreateBoardInput!) {
    createBoard(input: $input) {
      ...BoardFragment
      owner {
        ...UserFragment
      }
    }
  }
`;

export const UPDATE_BOARD = gql`
  ${BOARD_FRAGMENT}
  mutation UpdateBoard($id: UUID!, $input: UpdateBoardInput!) {
    updateBoard(id: $id, input: $input) {
      ...BoardFragment
    }
  }
`;

export const DELETE_BOARD = gql`
  mutation DeleteBoard($id: UUID!) {
    deleteBoard(id: $id) {
      success
    }
  }
`;

// Board member mutations
export const ADD_BOARD_MEMBER = gql`
  mutation AddBoardMember($boardId: UUID!, $email: String!, $role: BoardRole!) {
    addBoardMember(boardId: $boardId, email: $email, role: $role) {
      id
      boardId
      userId
      role
      invitedBy
      joinedAt
      user {
        ...UserFragment
      }
    }
  }
`;

export const UPDATE_BOARD_MEMBER_ROLE = gql`
  mutation UpdateBoardMemberRole($id: UUID!, $role: BoardRole!) {
    updateBoardMemberRole(id: $id, role: $role) {
      id
      role
    }
  }
`;

export const REMOVE_BOARD_MEMBER = gql`
  mutation RemoveBoardMember($id: UUID!) {
    removeBoardMember(id: $id) {
      success
    }
  }
`;

// Generation mutations
export const CREATE_GENERATION = gql`
  ${GENERATION_FRAGMENT}
  mutation CreateGeneration($input: CreateGenerationInput!) {
    createGeneration(input: $input) {
      ...GenerationFragment
    }
  }
`;

export const CANCEL_GENERATION = gql`
  mutation CancelGeneration($id: UUID!) {
    cancelGeneration(id: $id) {
      id
      status
    }
  }
`;

export const RETRY_GENERATION = gql`
  ${GENERATION_FRAGMENT}
  mutation RetryGeneration($id: UUID!) {
    retryGeneration(id: $id) {
      ...GenerationFragment
    }
  }
`;

// Input types (these should match your backend GraphQL schema)
export interface CreateBoardInput {
  title: string;
  description?: string;
  isPublic?: boolean;
  settings?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface UpdateBoardInput {
  title?: string;
  description?: string;
  isPublic?: boolean;
  settings?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface CreateGenerationInput {
  boardId: string;
  generatorName: string;
  artifactType: ArtifactType; // Allow string for flexibility with new types
  inputParams: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

// Enums (should match backend)
export enum BoardRole {
  VIEWER = "VIEWER",
  EDITOR = "EDITOR",
  ADMIN = "ADMIN",
}

export enum GenerationStatus {
  PENDING = "PENDING",
  RUNNING = "RUNNING",
  COMPLETED = "COMPLETED",
  FAILED = "FAILED",
  CANCELLED = "CANCELLED",
}

export enum ArtifactType {
  IMAGE = "image",
  VIDEO = "video",
  AUDIO = "audio",
  TEXT = "text",
  LORA = "lora",
  MODEL = "model",
}

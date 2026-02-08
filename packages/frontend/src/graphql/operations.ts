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

// Lineage fragments
export const ARTIFACT_LINEAGE_FRAGMENT = gql`
  fragment ArtifactLineageFragment on ArtifactLineage {
    generationId
    role
    artifactType
  }
`;

export const ANCESTRY_NODE_FRAGMENT = gql`
  ${GENERATION_FRAGMENT}
  fragment AncestryNodeFragment on AncestryNode {
    depth
    role
    generation {
      ...GenerationFragment
    }
    parents {
      depth
      role
      generation {
        ...GenerationFragment
      }
    }
  }
`;

export const DESCENDANT_NODE_FRAGMENT = gql`
  ${GENERATION_FRAGMENT}
  fragment DescendantNodeFragment on DescendantNode {
    depth
    role
    generation {
      ...GenerationFragment
    }
    children {
      depth
      role
      generation {
        ...GenerationFragment
      }
    }
  }
`;

// Tag fragment
export const TAG_FRAGMENT = gql`
  fragment TagFragment on Tag {
    id
    tenantId
    name
    slug
    description
    metadata
    createdAt
    updatedAt
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
  query GetBoard($id: UUID!, $limit: Int, $offset: Int) {
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
      generations(limit: $limit, offset: $offset) {
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

// Lineage queries
export const GET_ANCESTRY = gql`
  ${ANCESTRY_NODE_FRAGMENT}
  query GetAncestry($id: UUID!, $maxDepth: Int = 25) {
    generation(id: $id) {
      ancestry(maxDepth: $maxDepth) {
        ...AncestryNodeFragment
      }
    }
  }
`;

export const GET_DESCENDANTS = gql`
  ${DESCENDANT_NODE_FRAGMENT}
  query GetDescendants($id: UUID!, $maxDepth: Int = 25) {
    generation(id: $id) {
      descendants(maxDepth: $maxDepth) {
        ...DescendantNodeFragment
      }
    }
  }
`;

export const GET_INPUT_ARTIFACTS = gql`
  ${ARTIFACT_LINEAGE_FRAGMENT}
  query GetInputArtifacts($id: UUID!) {
    generation(id: $id) {
      inputArtifacts {
        ...ArtifactLineageFragment
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
  mutation UpdateBoard($input: UpdateBoardInput!) {
    updateBoard(input: $input) {
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

export const DELETE_GENERATION = gql`
  mutation DeleteGeneration($id: UUID!) {
    deleteGeneration(id: $id)
  }
`;

export const UPLOAD_ARTIFACT_FROM_URL = gql`
  ${GENERATION_FRAGMENT}
  mutation UploadArtifactFromUrl($input: UploadArtifactInput!) {
    uploadArtifact(input: $input) {
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
  id: string;
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

export interface UploadArtifactInput {
  boardId: string;
  artifactType: ArtifactType;
  fileUrl?: string;
  originalFilename?: string;
  userDescription?: string;
  parentGenerationId?: string;
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
  IMAGE = "IMAGE",
  VIDEO = "VIDEO",
  AUDIO = "AUDIO",
  TEXT = "TEXT",
  LORA = "LORA",
  MODEL = "MODEL",
}

// Tag queries
export const GET_TAGS = gql`
  ${TAG_FRAGMENT}
  query GetTags($limit: Int, $offset: Int) {
    tags(limit: $limit, offset: $offset) {
      ...TagFragment
    }
  }
`;

export const GET_TAG = gql`
  ${TAG_FRAGMENT}
  query GetTag($id: UUID!) {
    tag(id: $id) {
      ...TagFragment
    }
  }
`;

export const GET_TAG_BY_SLUG = gql`
  ${TAG_FRAGMENT}
  query GetTagBySlug($slug: String!) {
    tagBySlug(slug: $slug) {
      ...TagFragment
    }
  }
`;

export const GET_GENERATION_TAGS = gql`
  ${TAG_FRAGMENT}
  query GetGenerationTags($id: UUID!) {
    generation(id: $id) {
      tags {
        ...TagFragment
      }
    }
  }
`;

// Tag mutations
export const CREATE_TAG = gql`
  ${TAG_FRAGMENT}
  mutation CreateTag($input: CreateTagInput!) {
    createTag(input: $input) {
      ...TagFragment
    }
  }
`;

export const UPDATE_TAG = gql`
  ${TAG_FRAGMENT}
  mutation UpdateTag($input: UpdateTagInput!) {
    updateTag(input: $input) {
      ...TagFragment
    }
  }
`;

export const DELETE_TAG = gql`
  mutation DeleteTag($id: UUID!) {
    deleteTag(id: $id)
  }
`;

export const ADD_TAG_TO_GENERATION = gql`
  ${TAG_FRAGMENT}
  mutation AddTagToGeneration($generationId: UUID!, $tagId: UUID!) {
    addTagToGeneration(generationId: $generationId, tagId: $tagId) {
      ...TagFragment
    }
  }
`;

export const REMOVE_TAG_FROM_GENERATION = gql`
  mutation RemoveTagFromGeneration($generationId: UUID!, $tagId: UUID!) {
    removeTagFromGeneration(generationId: $generationId, tagId: $tagId)
  }
`;

// Tag input types
export interface CreateTagInput {
  name: string;
  slug?: string;
  description?: string;
  metadata?: Record<string, unknown>;
}

export interface UpdateTagInput {
  id: string;
  name?: string;
  slug?: string;
  description?: string;
  metadata?: Record<string, unknown>;
}

// Tag type
export interface Tag {
  id: string;
  tenantId: string;
  name: string;
  slug: string;
  description: string | null;
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

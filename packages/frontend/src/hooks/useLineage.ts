/**
 * Hook for accessing generation lineage (ancestry and descendants).
 */

import { useMemo } from "react";
import { useQuery } from "urql";
import {
  GET_ANCESTRY,
  GET_DESCENDANTS,
  GET_INPUT_ARTIFACTS,
} from "../graphql/operations";

export interface ArtifactLineage {
  generationId: string;
  role: string;
  artifactType: string;
}

export interface AncestryNode {
  generation: {
    id: string;
    generatorName: string;
    artifactType: string;
    status: string;
    storageUrl?: string;
    thumbnailUrl?: string;
    createdAt: string;
    [key: string]: unknown;
  };
  depth: number;
  role: string | null;
  parents: AncestryNode[];
}

export interface DescendantNode {
  generation: {
    id: string;
    generatorName: string;
    artifactType: string;
    status: string;
    storageUrl?: string;
    thumbnailUrl?: string;
    createdAt: string;
    [key: string]: unknown;
  };
  depth: number;
  role: string | null;
  children: DescendantNode[];
}

interface UseAncestryOptions {
  maxDepth?: number;
  pause?: boolean;
}

interface UseAncestryHook {
  ancestry: AncestryNode | null;
  loading: boolean;
  error: Error | null;
}

/**
 * Hook for fetching the ancestry tree of a generation.
 * @param generationId - The ID of the generation to fetch ancestry for
 * @param options - Optional configuration (maxDepth, pause)
 */
export function useAncestry(
  generationId: string,
  options: UseAncestryOptions = {}
): UseAncestryHook {
  const { maxDepth = 25, pause = false } = options;

  const [{ data, fetching, error }] = useQuery({
    query: GET_ANCESTRY,
    variables: { id: generationId, maxDepth },
    pause,
  });

  const ancestry = useMemo(
    () => data?.generation?.ancestry || null,
    [data?.generation?.ancestry]
  );

  return {
    ancestry,
    loading: fetching,
    error: error ? new Error(error.message) : null,
  };
}

interface UseDescendantsOptions {
  maxDepth?: number;
  pause?: boolean;
}

interface UseDescendantsHook {
  descendants: DescendantNode | null;
  loading: boolean;
  error: Error | null;
}

/**
 * Hook for fetching the descendants tree of a generation.
 * @param generationId - The ID of the generation to fetch descendants for
 * @param options - Optional configuration (maxDepth, pause)
 */
export function useDescendants(
  generationId: string,
  options: UseDescendantsOptions = {}
): UseDescendantsHook {
  const { maxDepth = 25, pause = false } = options;

  const [{ data, fetching, error }] = useQuery({
    query: GET_DESCENDANTS,
    variables: { id: generationId, maxDepth },
    pause,
  });

  const descendants = useMemo(
    () => data?.generation?.descendants || null,
    [data?.generation?.descendants]
  );

  return {
    descendants,
    loading: fetching,
    error: error ? new Error(error.message) : null,
  };
}

interface UseInputArtifactsOptions {
  pause?: boolean;
}

interface UseInputArtifactsHook {
  inputArtifacts: ArtifactLineage[];
  loading: boolean;
  error: Error | null;
}

/**
 * Hook for fetching the input artifacts of a generation.
 * @param generationId - The ID of the generation to fetch input artifacts for
 * @param options - Optional configuration (pause)
 */
export function useInputArtifacts(
  generationId: string,
  options: UseInputArtifactsOptions = {}
): UseInputArtifactsHook {
  const { pause = false } = options;

  const [{ data, fetching, error }] = useQuery({
    query: GET_INPUT_ARTIFACTS,
    variables: { id: generationId },
    pause,
  });

  const inputArtifacts = useMemo(
    () => data?.generation?.inputArtifacts || [],
    [data?.generation?.inputArtifacts]
  );

  return {
    inputArtifacts,
    loading: fetching,
    error: error ? new Error(error.message) : null,
  };
}

/**
 * Combined hook for fetching both ancestry and descendants.
 * Useful for lineage explorer pages that show both trees.
 */
interface UseLineageOptions {
  maxDepth?: number;
  pause?: boolean;
}

interface UseLineageHook {
  ancestry: AncestryNode | null;
  descendants: DescendantNode | null;
  inputArtifacts: ArtifactLineage[];
  loading: boolean;
  error: Error | null;
}

export function useLineage(
  generationId: string,
  options: UseLineageOptions = {}
): UseLineageHook {
  const ancestryResult = useAncestry(generationId, options);
  const descendantsResult = useDescendants(generationId, options);
  const inputArtifactsResult = useInputArtifacts(generationId, options);

  const loading =
    ancestryResult.loading ||
    descendantsResult.loading ||
    inputArtifactsResult.loading;

  const error =
    ancestryResult.error || descendantsResult.error || inputArtifactsResult.error;

  return {
    ancestry: ancestryResult.ancestry,
    descendants: descendantsResult.descendants,
    inputArtifacts: inputArtifactsResult.inputArtifacts,
    loading,
    error,
  };
}

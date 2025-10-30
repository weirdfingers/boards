/**
 * Hook for fetching available generators.
 */

import { useMemo } from "react";
import { useQuery } from "urql";
import { ArtifactType, GET_GENERATORS } from "../graphql/operations";

interface Generator {
  name: string;
  description: string;
  artifactType: ArtifactType;
  inputSchema: Record<string, unknown>;
}

interface UseGeneratorsOptions {
  artifactType?: string;
}

interface GeneratorsHook {
  generators: Generator[];
  loading: boolean;
  error: Error | null;
}

export function useGenerators(
  options: UseGeneratorsOptions = {}
): GeneratorsHook {
  const { artifactType } = options;

  // Query for generators
  const [{ data, fetching, error }] = useQuery({
    query: GET_GENERATORS,
    variables: artifactType ? { artifactType } : {},
  });

  const generators = useMemo(() => data?.generators || [], [data?.generators]);

  return {
    generators,
    loading: fetching,
    error: error ? new Error(error.message) : null,
  };
}

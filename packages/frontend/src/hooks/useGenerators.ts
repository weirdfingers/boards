/**
 * Hook for fetching available generators.
 */

import { useMemo } from "react";
import { useQuery } from "urql";
import type { JSONSchema7 } from "json-schema";
import { ArtifactType, GET_GENERATORS } from "../graphql/operations";

export interface Generator {
  name: string;
  description: string;
  artifactType: ArtifactType;
  inputSchema: JSONSchema7;
}

// Re-export JSONSchema7 for applications
export type { JSONSchema7 } from "json-schema";

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

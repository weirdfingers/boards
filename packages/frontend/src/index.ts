export const VERSION = "0.1.0";

// Core auth exports
export * from "./auth/types";
export * from "./auth/hooks/useAuth";
export { AuthProvider } from "./auth/context";
export { BaseAuthProvider } from "./auth/providers/base";
export { NoAuthProvider } from "./auth/providers/none"; // Only no-auth included for dev

// API configuration
export { useApiConfig } from "./config/ApiConfigContext";
export type { ApiConfig } from "./config/ApiConfigContext";

// Generator selection context
export { GeneratorSelectionProvider, useGeneratorSelection } from "./config/GeneratorSelectionContext";
export type { GeneratorInfo, GeneratorSelectionContextValue, ArtifactSlotInfo, Artifact } from "./config/GeneratorSelectionContext";

// GraphQL exports
export { createGraphQLClient } from "./graphql/client";
export * from "./graphql/operations";

// Core hooks
export { useBoards } from "./hooks/useBoards";
export { useBoard } from "./hooks/useBoard";
export { useGeneration } from "./hooks/useGeneration";
export { useGenerators } from "./hooks/useGenerators";
export type { Generator, JSONSchema7 } from "./hooks/useGenerators";
export {
  useAncestry,
  useDescendants,
  useInputArtifacts,
  useLineage,
} from "./hooks/useLineage";
export type {
  ArtifactLineage,
  AncestryNode,
  DescendantNode,
} from "./hooks/useLineage";

// Generator schema utilities
export * from "./types/generatorSchema";
export * from "./utils/schemaParser";

// Provider components
export { BoardsProvider } from "./providers/BoardsProvider";

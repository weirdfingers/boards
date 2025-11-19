/**
 * Generator selection context for sharing selected generator state
 * and artifact compatibility logic across components.
 */

import { createContext, useContext, ReactNode, useState, useCallback, useMemo } from "react";
import type { JSONSchema7 } from "json-schema";
import { parseGeneratorSchema } from "../utils/schemaParser";
import type { ParsedGeneratorSchema } from "../types/generatorSchema";

export interface GeneratorInfo {
  name: string;
  description: string;
  artifactType: string;
  inputSchema: JSONSchema7;
}

export interface ArtifactSlotInfo {
  fieldName: string;
  artifactType: string;
  required: boolean;
}

export interface Artifact {
  id: string;
  artifactType: string;
  storageUrl?: string | null;
  thumbnailUrl?: string | null;
}

export interface GeneratorSelectionContextValue {
  selectedGenerator: GeneratorInfo | null;
  setSelectedGenerator: (generator: GeneratorInfo | null) => void;
  parsedSchema: ParsedGeneratorSchema | null;
  artifactSlots: ArtifactSlotInfo[];
  canArtifactBeAdded: (artifactType: string) => boolean;
  selectedArtifacts: Map<string, Artifact>;
  setSelectedArtifacts: (artifacts: Map<string, Artifact>) => void;
  addArtifactToSlot: (artifact: Artifact) => boolean;
  removeArtifactFromSlot: (slotName: string) => void;
  clearAllArtifacts: () => void;
}

const GeneratorSelectionContext = createContext<GeneratorSelectionContextValue | null>(null);

interface GeneratorSelectionProviderProps {
  children: ReactNode;
}

export function GeneratorSelectionProvider({
  children,
}: GeneratorSelectionProviderProps) {
  const [selectedGenerator, setSelectedGenerator] = useState<GeneratorInfo | null>(null);
  const [selectedArtifacts, setSelectedArtifacts] = useState<Map<string, Artifact>>(new Map());

  // Parse the selected generator's input schema
  const parsedSchema = useMemo((): ParsedGeneratorSchema | null => {
    if (!selectedGenerator) {
      return null;
    }
    return parseGeneratorSchema(selectedGenerator.inputSchema);
  }, [selectedGenerator]);

  // Extract artifact slots from the parsed schema
  const artifactSlots = useMemo((): ArtifactSlotInfo[] => {
    if (!parsedSchema) {
      return [];
    }
    return parsedSchema.artifactSlots.map((slot) => ({
      fieldName: slot.fieldName,
      artifactType: slot.artifactType,
      required: slot.required,
    }));
  }, [parsedSchema]);

  // Helper function to check if an artifact type can be added to any available (empty) slot
  const canArtifactBeAdded = useCallback((artifactType: string): boolean => {
    if (!artifactSlots.length) {
      return false;
    }
    // Check if there's at least one compatible slot that's not already filled
    return artifactSlots.some(
      (slot) =>
        slot.artifactType.toLowerCase() === artifactType.toLowerCase() &&
        !selectedArtifacts.has(slot.fieldName)
    );
  }, [artifactSlots, selectedArtifacts]);

  // Add artifact to the first compatible empty slot
  const addArtifactToSlot = useCallback((artifact: Artifact): boolean => {
    if (!artifactSlots.length) {
      return false;
    }

    // Find first compatible empty slot
    const compatibleSlot = artifactSlots.find(
      (slot) =>
        slot.artifactType.toLowerCase() === artifact.artifactType.toLowerCase() &&
        !selectedArtifacts.has(slot.fieldName)
    );

    if (!compatibleSlot) {
      return false;
    }

    // Add artifact to the slot
    const newArtifacts = new Map(selectedArtifacts);
    newArtifacts.set(compatibleSlot.fieldName, artifact);
    setSelectedArtifacts(newArtifacts);
    return true;
  }, [artifactSlots, selectedArtifacts]);

  // Remove artifact from a specific slot
  const removeArtifactFromSlot = useCallback((slotName: string) => {
    const newArtifacts = new Map(selectedArtifacts);
    newArtifacts.delete(slotName);
    setSelectedArtifacts(newArtifacts);
  }, [selectedArtifacts]);

  // Clear all selected artifacts
  const clearAllArtifacts = useCallback(() => {
    setSelectedArtifacts(new Map());
  }, []);

  // Clear artifacts when generator changes
  const handleSetSelectedGenerator = useCallback((generator: GeneratorInfo | null) => {
    setSelectedGenerator(generator);
    // Clear artifacts when switching generators
    setSelectedArtifacts(new Map());
  }, []);

  const value: GeneratorSelectionContextValue = {
    selectedGenerator,
    setSelectedGenerator: handleSetSelectedGenerator,
    parsedSchema,
    artifactSlots,
    canArtifactBeAdded,
    selectedArtifacts,
    setSelectedArtifacts,
    addArtifactToSlot,
    removeArtifactFromSlot,
    clearAllArtifacts,
  };

  return (
    <GeneratorSelectionContext.Provider value={value}>
      {children}
    </GeneratorSelectionContext.Provider>
  );
}

export function useGeneratorSelection(): GeneratorSelectionContextValue {
  const context = useContext(GeneratorSelectionContext);
  if (!context) {
    throw new Error("useGeneratorSelection must be used within GeneratorSelectionProvider");
  }
  return context;
}

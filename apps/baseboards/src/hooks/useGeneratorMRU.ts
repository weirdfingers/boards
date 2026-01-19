import { useState, useEffect, useCallback } from "react";

const MRU_STORAGE_KEY = "boards-generator-mru";
const MRU_MAX_SIZE = 3;

export function useGeneratorMRU() {
  const [mruGenerators, setMruGenerators] = useState<string[]>([]);

  // Load MRU from localStorage on mount
  useEffect(() => {
    try {
      if (typeof window === "undefined") return;

      const stored = localStorage.getItem(MRU_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Robustness check: Ensure it's an array of strings
        if (
          Array.isArray(parsed) &&
          parsed.every((item) => typeof item === "string")
        ) {
          setMruGenerators(parsed);
        }
      }
    } catch (error) {
      console.error("Failed to load MRU generators:", error);
      // Fallback to empty list is implicit via initial state
    }
  }, []);

  const addGeneratorToMRU = useCallback((generatorName: string) => {
    setMruGenerators((prev) => {
      // Create new list with generator at the front, removing duplicates
      const newMru = [
        generatorName,
        ...prev.filter((name) => name !== generatorName),
      ].slice(0, MRU_MAX_SIZE);

      // Persist to localStorage
      try {
        if (typeof window !== "undefined") {
          localStorage.setItem(MRU_STORAGE_KEY, JSON.stringify(newMru));
        }
      } catch (error) {
        console.error("Failed to save MRU generators:", error);
      }

      return newMru;
    });
  }, []);

  return {
    mruGenerators,
    lastUsedGenerator: mruGenerators.length > 0 ? mruGenerators[0] : undefined,
    addGeneratorToMRU,
  };
}

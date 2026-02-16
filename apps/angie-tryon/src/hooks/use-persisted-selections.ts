"use client";

import { useCallback } from "react";
import { useLocalStorage } from "./use-local-storage";
import type { SlotType, SlotValue } from "@/components/outfit/types";

type PersistedSelections = Partial<Record<SlotType, SlotValue | null>>;

const STORAGE_KEY = "angie-tryon:selections";

export function usePersistedSelections() {
  const [selections, setSelections, removeSelections] =
    useLocalStorage<PersistedSelections>(STORAGE_KEY, {});

  const setSelection = useCallback(
    (type: SlotType, value: SlotValue | null) => {
      setSelections((prev) => ({ ...prev, [type]: value }));
    },
    [setSelections]
  );

  const resetSelections = useCallback(() => {
    removeSelections();
  }, [removeSelections]);

  return { selections, setSelection, resetSelections };
}

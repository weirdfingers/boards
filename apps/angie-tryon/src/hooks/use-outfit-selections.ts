"use client";

import { useCallback, useMemo } from "react";
import { usePersistedSelections } from "./use-persisted-selections";
import type { SlotType, SlotValue } from "@/components/outfit/types";

const GARMENT_SLOTS: SlotType[] = [
  "insideTop",
  "outsideTop",
  "bottoms",
  "shoes",
  "socks",
  "hat",
];

export interface OutfitGeneratorInput {
  model_image: string | null;
  inside_top_image: string | null;
  outside_top_image: string | null;
  bottoms_image: string | null;
  shoes_image: string | null;
  socks_image: string | null;
  hat_image: string | null;
}

export function useOutfitSelections() {
  const { selections, setSelection, resetSelections } =
    usePersistedSelections();

  const setSlot = useCallback(
    (slot: SlotType, value: SlotValue) => {
      setSelection(slot, value);
    },
    [setSelection]
  );

  const clearSlot = useCallback(
    (slot: SlotType) => {
      setSelection(slot, null);
    },
    [setSelection]
  );

  const resetAll = useCallback(() => {
    resetSelections();
  }, [resetSelections]);

  const hasModel = !!selections.model;
  const filledGarmentCount = useMemo(
    () => GARMENT_SLOTS.filter((slot) => !!selections[slot]).length,
    [selections]
  );
  const isValid = hasModel && filledGarmentCount > 0;

  const toGeneratorInput = useCallback((): OutfitGeneratorInput => {
    return {
      model_image: selections.model?.id ?? null,
      inside_top_image: selections.insideTop?.id ?? null,
      outside_top_image: selections.outsideTop?.id ?? null,
      bottoms_image: selections.bottoms?.id ?? null,
      shoes_image: selections.shoes?.id ?? null,
      socks_image: selections.socks?.id ?? null,
      hat_image: selections.hat?.id ?? null,
    };
  }, [selections]);

  return {
    selections,
    setSlot,
    clearSlot,
    resetAll,
    isValid,
    hasModel,
    filledGarmentCount,
    toGeneratorInput,
  };
}

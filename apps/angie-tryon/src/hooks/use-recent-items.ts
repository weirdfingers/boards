"use client";

import { useCallback } from "react";
import { useLocalStorage } from "./use-local-storage";
import type { SlotType, SlotValue } from "@/components/outfit/types";

const MAX_RECENT_ITEMS = 20;

export function useRecentItems(slotType: SlotType | null) {
  const key = slotType
    ? `angie-tryon:recent:${slotType}`
    : "angie-tryon:recent:__noop__";

  const [recentItems, setRecentItems, clearStorage] = useLocalStorage<
    SlotValue[]
  >(key, []);

  const addRecentItem = useCallback(
    (item: SlotValue) => {
      if (!slotType) return;
      setRecentItems((prev) => {
        const filtered = prev.filter((existing) => existing.id !== item.id);
        return [item, ...filtered].slice(0, MAX_RECENT_ITEMS);
      });
    },
    [slotType, setRecentItems]
  );

  const clearRecentItems = useCallback(() => {
    if (!slotType) return;
    clearStorage();
  }, [slotType, clearStorage]);

  if (!slotType) {
    return {
      recentItems: [] as SlotValue[],
      addRecentItem: () => {},
      clearRecentItems: () => {},
    };
  }

  return { recentItems, addRecentItem, clearRecentItems };
}

"use client";

import { useCallback } from "react";
import { useLocalStorage } from "./use-local-storage";

export interface UserPreferences {
  autoBackgroundRemoval: boolean;
}

const DEFAULT_PREFERENCES: UserPreferences = {
  autoBackgroundRemoval: true,
};

const STORAGE_KEY = "angie-tryon:preferences";

export function usePersistedPreferences() {
  const [preferences, setPreferences, removePreferences] =
    useLocalStorage<UserPreferences>(STORAGE_KEY, DEFAULT_PREFERENCES);

  const setPreference = useCallback(
    <K extends keyof UserPreferences>(key: K, value: UserPreferences[K]) => {
      setPreferences((prev) => ({ ...prev, [key]: value }));
    },
    [setPreferences]
  );

  const resetPreferences = useCallback(() => {
    removePreferences();
  }, [removePreferences]);

  return { preferences, setPreference, resetPreferences };
}

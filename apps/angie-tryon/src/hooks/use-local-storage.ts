"use client";

import { useState, useEffect, useCallback, useRef } from "react";

export function useLocalStorage<T>(
  key: string,
  initialValue: T
): [T, (value: T | ((prev: T) => T)) => void, () => void] {
  // Always initialize with initialValue (SSR-safe, no hydration mismatch)
  const [storedValue, setStoredValue] = useState<T>(initialValue);
  const initialValueRef = useRef(initialValue);

  // On mount (client only), read from localStorage and reconcile
  useEffect(() => {
    try {
      const item = window.localStorage.getItem(key);
      if (item !== null) {
        setStoredValue(JSON.parse(item));
      }
    } catch (error) {
      console.warn(`Error reading localStorage key "${key}":`, error);
    }
  }, [key]);

  // Setter: writes to both state and localStorage
  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      setStoredValue((prev) => {
        const nextValue = value instanceof Function ? value(prev) : value;
        try {
          window.localStorage.setItem(key, JSON.stringify(nextValue));
        } catch (error) {
          console.warn(`Error writing localStorage key "${key}":`, error);
        }
        return nextValue;
      });
    },
    [key]
  );

  // Remove: clears key from localStorage, resets to initialValue
  const removeValue = useCallback(() => {
    try {
      window.localStorage.removeItem(key);
    } catch (error) {
      console.warn(`Error removing localStorage key "${key}":`, error);
    }
    setStoredValue(initialValueRef.current);
  }, [key]);

  // Cross-tab sync via storage event
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === key) {
        try {
          setStoredValue(
            e.newValue !== null
              ? JSON.parse(e.newValue)
              : initialValueRef.current
          );
        } catch {
          setStoredValue(initialValueRef.current);
        }
      }
    };
    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, [key]);

  return [storedValue, setValue, removeValue];
}

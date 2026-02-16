"use client";

import { useMemo } from "react";
import { Sparkles, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SlotType, SlotValue } from "./types";

const GARMENT_SLOTS: SlotType[] = [
  "insideTop",
  "outsideTop",
  "bottoms",
  "shoes",
  "socks",
  "hat",
];

export interface GenerationProgress {
  status: "queued" | "processing" | "completed" | "failed" | "cancelled";
  progress: number;
  message?: string | null;
}

interface GenerateButtonProps {
  selections: Partial<Record<SlotType, SlotValue | null>>;
  progress?: GenerationProgress | null;
  error?: Error | null;
  onGenerate: () => void;
  onRetry?: () => void;
}

export function GenerateButton({
  selections,
  progress,
  error,
  onGenerate,
  onRetry,
}: GenerateButtonProps) {
  const hasModel = !!selections.model;
  const filledGarmentCount = useMemo(
    () => GARMENT_SLOTS.filter((slot) => !!selections[slot]).length,
    [selections]
  );
  const isEnabled = hasModel && filledGarmentCount > 0;
  const isGenerating =
    progress?.status === "queued" || progress?.status === "processing";
  const hasError = !!error;

  // Determine visual state
  if (hasError) {
    return (
      <div className="flex flex-col items-center gap-2">
        <button
          type="button"
          onClick={onRetry ?? onGenerate}
          className={cn(
            "flex h-14 w-full items-center justify-center gap-2 rounded-2xl bg-destructive text-white font-semibold text-base",
            "transition-all active:scale-[0.99]"
          )}
        >
          <Sparkles className="size-5" />
          <span>Generation Failed — Tap to Retry</span>
        </button>
        {error.message && (
          <p className="text-xs text-destructive">{error.message}</p>
        )}
      </div>
    );
  }

  if (isGenerating) {
    return (
      <div className="flex flex-col items-center gap-2">
        <div
          className={cn(
            "flex h-14 w-full items-center justify-center gap-2 rounded-2xl bg-primary text-primary-foreground font-semibold text-base",
            "pointer-events-none"
          )}
          aria-busy="true"
          role="status"
        >
          <Loader2 className="size-5 animate-spin" />
          <span>{progress?.message ?? "Generating..."}</span>
        </div>
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          {progress?.progress != null && progress.progress > 0
            ? `${Math.round(progress.progress)}% complete`
            : "Starting generation..."}
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        type="button"
        disabled={!isEnabled}
        onClick={onGenerate}
        className={cn(
          "flex h-14 w-full items-center justify-center gap-2 rounded-2xl font-semibold text-base",
          "transition-all",
          isEnabled
            ? "bg-primary text-primary-foreground hover:bg-primary/90 active:scale-[0.99]"
            : "bg-muted text-muted-foreground"
        )}
      >
        <Sparkles className="size-5" />
        <span>Generate Outfit</span>
      </button>
      <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
        {isEnabled
          ? `AI results take ~${filledGarmentCount * 15}–${filledGarmentCount * 30}s`
          : "Select model + at least one item"}
      </p>
    </div>
  );
}

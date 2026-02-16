"use client";

import Image from "next/image";
import {
  User,
  Shirt,
  Footprints,
  Crown,
  Plus,
  Pencil,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { SlotType, SlotValue } from "./types";
import type { ComponentType } from "react";

const SLOT_ICONS: Record<SlotType, ComponentType<{ className?: string }>> = {
  model: User,
  insideTop: Shirt,
  outsideTop: Shirt,
  bottoms: Shirt,
  shoes: Footprints,
  socks: Footprints,
  hat: Crown,
};

interface OutfitSlotProps {
  type: SlotType;
  label: string;
  value?: SlotValue | null;
  onSelect: () => void;
  onEdit?: () => void;
  onClear?: () => void;
}

export function OutfitSlot({
  type,
  label,
  value,
  onSelect,
  onEdit,
}: OutfitSlotProps) {
  const isFilled = !!value;
  const Icon = SLOT_ICONS[type];

  return (
    <button
      type="button"
      onClick={isFilled ? onEdit : onSelect}
      className={cn(
        "flex h-20 w-full items-center gap-4 rounded-xl bg-card px-4 shadow-sm transition-all",
        "hover:shadow-md active:scale-[0.99]",
        isFilled ? "border border-border" : "border border-dashed border-border"
      )}
      aria-label={isFilled ? `Edit ${label}: ${value.name}` : `Add ${label}`}
    >
      {/* Thumbnail / Icon */}
      {isFilled ? (
        <div className="relative size-12 shrink-0 overflow-hidden rounded-full">
          <Image
            src={value.thumbnailUrl}
            alt={value.name}
            fill
            className="object-cover"
          />
        </div>
      ) : (
        <div className="flex size-12 shrink-0 items-center justify-center rounded-full border-2 border-dashed border-muted-foreground/30">
          <Icon className="size-5 text-muted-foreground/50" />
        </div>
      )}

      {/* Label & Item Name */}
      <div className="flex min-w-0 flex-1 flex-col items-start">
        <span className="text-sm font-medium text-foreground">{label}</span>
        {isFilled ? (
          <span className="truncate text-sm font-semibold text-foreground">
            {value.name}
          </span>
        ) : (
          <span className="text-sm text-primary/70">Add an item</span>
        )}
      </div>

      {/* Action Icon */}
      {isFilled ? (
        <div className="flex size-8 shrink-0 items-center justify-center">
          <Pencil className="size-4 text-muted-foreground" />
        </div>
      ) : (
        <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
          <Plus className="size-4" />
        </div>
      )}
    </button>
  );
}

"use client";

import { Button } from "@/components/ui/button";
import { OutfitSlot } from "./outfit-slot";
import { SLOT_CONFIGS } from "./types";
import type { SlotType, SlotValue } from "./types";

interface OutfitSlotListProps {
  selections: Partial<Record<SlotType, SlotValue | null>>;
  onSelectSlot: (type: SlotType) => void;
  onEditSlot: (type: SlotType) => void;
  onClearSlot: (type: SlotType) => void;
  onResetAll: () => void;
}

export function OutfitSlotList({
  selections,
  onSelectSlot,
  onEditSlot,
  onClearSlot,
  onResetAll,
}: OutfitSlotListProps) {
  const hasAnySelection = Object.values(selections).some(Boolean);

  return (
    <section className="space-y-4">
      {/* Section Header */}
      <div className="flex items-end justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Outfit Slots</h2>
          <p className="text-sm text-muted-foreground">
            Select items to visualize
          </p>
        </div>
        {hasAnySelection && (
          <Button
            variant="outline"
            size="sm"
            onClick={onResetAll}
            className="text-xs font-semibold uppercase tracking-wide text-secondary"
          >
            Reset All
          </Button>
        )}
      </div>

      {/* Slot Cards */}
      <div className="space-y-3">
        {SLOT_CONFIGS.map(({ type, label }) => (
          <OutfitSlot
            key={type}
            type={type}
            label={label}
            value={selections[type]}
            onSelect={() => onSelectSlot(type)}
            onEdit={() => onEditSlot(type)}
            onClear={() => onClearSlot(type)}
          />
        ))}
      </div>
    </section>
  );
}

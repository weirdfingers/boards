"use client";

import Image from "next/image";
import { Camera, ImageIcon, ClipboardPaste } from "lucide-react";
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerDescription,
} from "@/components/ui/drawer";
import { SLOT_CONFIGS } from "./types";
import type { SlotType, SlotValue, InputMethod } from "./types";

const INPUT_METHODS: {
  method: InputMethod;
  label: string;
  icon: typeof Camera;
}[] = [
  { method: "camera", label: "Camera", icon: Camera },
  { method: "photos", label: "Photos", icon: ImageIcon },
  { method: "paste", label: "Link/Paste", icon: ClipboardPaste },
];

interface SelectionDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  slotType: SlotType | null;
  items: SlotValue[];
  onSelectItem: (item: SlotValue) => void;
  onInputMethod: (method: InputMethod) => void;
}

export function SelectionDrawer({
  open,
  onOpenChange,
  slotType,
  items,
  onSelectItem,
  onInputMethod,
}: SelectionDrawerProps) {
  const slotLabel =
    SLOT_CONFIGS.find((c) => c.type === slotType)?.label ?? "";

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent>
        <div className="mx-auto w-full max-w-lg">
          <DrawerHeader className="text-left">
            <DrawerTitle className="text-2xl">Add {slotLabel}</DrawerTitle>
            <DrawerDescription>
              Upload a source or choose from saved
            </DrawerDescription>
          </DrawerHeader>

          <div className="space-y-6 px-4 pb-6">
            {/* Quick Actions */}
            <div>
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Quick Actions
              </h3>
              <div className="flex gap-4">
                {INPUT_METHODS.map(({ method, label, icon: Icon }) => (
                  <button
                    key={method}
                    type="button"
                    onClick={() => onInputMethod(method)}
                    className="flex flex-col items-center gap-2"
                  >
                    <div className="flex size-14 items-center justify-center rounded-full border-2 border-border bg-card transition-colors hover:bg-accent">
                      <Icon className="size-6 text-foreground" />
                    </div>
                    <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      {label}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Saved Collection */}
            <div>
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Saved Collection
                </h3>
                {items.length > 0 && (
                  <span className="text-xs font-semibold uppercase tracking-wide text-primary">
                    See All
                  </span>
                )}
              </div>

              {items.length === 0 ? (
                <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border px-4 py-10">
                  <p className="text-center text-sm text-muted-foreground">
                    No items yet. Use the options above to add your first item.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  {items.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => onSelectItem(item)}
                      className="flex flex-col gap-2 text-left"
                    >
                      <div className="relative aspect-square w-full overflow-hidden rounded-xl bg-muted">
                        <Image
                          src={item.thumbnailUrl}
                          alt={item.name}
                          fill
                          className="object-cover"
                        />
                      </div>
                      <span className="truncate text-sm font-medium">
                        {item.name}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </DrawerContent>
    </Drawer>
  );
}

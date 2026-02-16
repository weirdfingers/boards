"use client";

import Image from "next/image";
import { Camera, ImageIcon, ClipboardPaste, Loader2 } from "lucide-react";
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerDescription,
} from "@/components/ui/drawer";
import { SLOT_CONFIGS } from "./types";
import type { SlotType, SlotValue, InputMethod } from "./types";
import type { PhotoUploadState } from "@/hooks/use-photo-upload";

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
  uploadState: PhotoUploadState | null;
}

export function SelectionDrawer({
  open,
  onOpenChange,
  slotType,
  items,
  onSelectItem,
  onInputMethod,
  uploadState,
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

            {/* Upload Progress */}
            {uploadState && uploadState.phase !== "idle" && (
              <UploadProgress state={uploadState} />
            )}

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

function UploadProgress({ state }: { state: PhotoUploadState }) {
  const phaseLabel =
    state.phase === "uploading"
      ? "Uploading..."
      : state.phase === "removing-background"
        ? "Removing background..."
        : state.phase === "completed"
          ? "Done!"
          : state.phase === "failed"
            ? "Upload failed"
            : "";

  const progressText =
    state.totalFiles > 1
      ? `${state.completedFiles} of ${state.totalFiles} files`
      : phaseLabel;

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-3">
        {state.phase !== "completed" && state.phase !== "failed" && (
          <Loader2 className="size-5 shrink-0 animate-spin text-primary" />
        )}
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium">
            {state.totalFiles > 1 ? phaseLabel : progressText}
          </p>
          {state.totalFiles > 1 && (
            <p className="text-xs text-muted-foreground">{progressText}</p>
          )}
          {state.error && (
            <p className="mt-1 text-xs text-destructive">{state.error}</p>
          )}
        </div>
      </div>
      {(state.phase === "uploading" || state.phase === "removing-background") && (
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-all duration-300"
            style={{
              width: `${state.phase === "removing-background" ? 100 : state.uploadProgress}%`,
            }}
          />
        </div>
      )}
    </div>
  );
}

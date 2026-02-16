"use client";

import { useCallback, useState } from "react";
import { useSupabase } from "@/hooks/use-supabase";
import { Header } from "@/components/header";
import { OutfitSlotList } from "@/components/outfit/outfit-slot-list";
import { SelectionDrawer } from "@/components/outfit/selection-drawer";
import { GenerateButton } from "@/components/outfit/generate-button";
import type { SlotType, SlotValue, InputMethod } from "@/components/outfit/types";

export default function Home() {
  const { user } = useSupabase();
  const [selections, setSelections] = useState<
    Partial<Record<SlotType, SlotValue | null>>
  >({});
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [activeSlotType, setActiveSlotType] = useState<SlotType | null>(null);

  const handleSelectSlot = useCallback((type: SlotType) => {
    setActiveSlotType(type);
    setDrawerOpen(true);
  }, []);

  const handleEditSlot = useCallback((type: SlotType) => {
    setActiveSlotType(type);
    setDrawerOpen(true);
  }, []);

  const handleSelectItem = useCallback(
    (item: SlotValue) => {
      if (activeSlotType) {
        setSelections((prev) => ({ ...prev, [activeSlotType]: item }));
      }
      setDrawerOpen(false);
    },
    [activeSlotType]
  );

  const handleInputMethod = useCallback(
    (method: InputMethod) => {
      // Downstream tickets: at-a2er (camera), at-0pyp (photos), at-vgk6 (paste)
      console.log("input method", method, "for slot", activeSlotType);
    },
    [activeSlotType]
  );

  const handleClearSlot = useCallback((type: SlotType) => {
    setSelections((prev) => ({ ...prev, [type]: null }));
  }, []);

  const handleResetAll = useCallback(() => {
    setSelections({});
  }, []);

  if (!user) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center p-4">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-semibold">AI Stylist</h1>
          <p className="text-muted-foreground">This is a private application.</p>
          <p className="text-sm text-muted-foreground">
            Please check your messages for an invitation link.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <Header />
      <main className="flex-1 px-4 pb-6">
        <div className="mx-auto w-full max-w-lg space-y-6">
          <OutfitSlotList
            selections={selections}
            onSelectSlot={handleSelectSlot}
            onEditSlot={handleEditSlot}
            onClearSlot={handleClearSlot}
            onResetAll={handleResetAll}
          />
          <GenerateButton
            selections={selections}
            onGenerate={() => {
              // Wired up in at-ii1g (outfit generation flow)
              console.log("Generate outfit", selections);
            }}
          />
        </div>
      </main>
      <SelectionDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        slotType={activeSlotType}
        items={[]}
        onSelectItem={handleSelectItem}
        onInputMethod={handleInputMethod}
      />
    </div>
  );
}

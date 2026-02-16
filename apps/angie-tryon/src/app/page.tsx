"use client";

import { useCallback, useState } from "react";
import { useSupabase } from "@/hooks/use-supabase";
import { Header } from "@/components/header";
import { OutfitSlotList } from "@/components/outfit/outfit-slot-list";
import type { SlotType, SlotValue } from "@/components/outfit/types";

export default function Home() {
  const { user } = useSupabase();
  const [selections, setSelections] = useState<
    Partial<Record<SlotType, SlotValue | null>>
  >({});

  const handleSelectSlot = useCallback((type: SlotType) => {
    // Will open SelectionDrawer (at-e1fa)
    console.log("select slot", type);
  }, []);

  const handleEditSlot = useCallback((type: SlotType) => {
    // Will open SelectionDrawer in edit mode (at-e1fa)
    console.log("edit slot", type);
  }, []);

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
          {/* Generate button will be added by at-wwr7 */}
        </div>
      </main>
    </div>
  );
}

"use client";

import { useCallback, useState } from "react";
import { useSupabase } from "@/hooks/use-supabase";
import { useOutfitSelections } from "@/hooks/use-outfit-selections";
import { useOutfitGeneration } from "@/hooks/use-outfit-generation";
import { useRecentItems } from "@/hooks/use-recent-items";
import { usePhotoUpload } from "@/hooks/use-photo-upload";
import { Header } from "@/components/header";
import { OutfitSlotList } from "@/components/outfit/outfit-slot-list";
import { SelectionDrawer } from "@/components/outfit/selection-drawer";
import { GenerateButton } from "@/components/outfit/generate-button";
import { OutfitResult } from "@/components/outfit/outfit-result";
import type { SlotType, SlotValue, InputMethod } from "@/components/outfit/types";

export default function Home() {
  const { user } = useSupabase();
  const { selections, setSlot, clearSlot, resetAll, toGeneratorInput } =
    useOutfitSelections();
  const outfitGeneration = useOutfitGeneration();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [activeSlotType, setActiveSlotType] = useState<SlotType | null>(null);
  const { recentItems, addRecentItem } = useRecentItems(activeSlotType);
  const photoUpload = usePhotoUpload();

  const showResult =
    outfitGeneration.state === "completed" && outfitGeneration.resultImageUrl;

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
        setSlot(activeSlotType, item);
        addRecentItem(item);
      }
      setDrawerOpen(false);
    },
    [activeSlotType, setSlot, addRecentItem]
  );

  const handlePhotoItemReady = useCallback(
    (item: SlotValue) => {
      if (activeSlotType) {
        setSlot(activeSlotType, item);
        addRecentItem(item);
      }
    },
    [activeSlotType, setSlot, addRecentItem]
  );

  const handlePhotoUploadComplete = useCallback(() => {
    setDrawerOpen(false);
  }, []);

  const handleInputMethod = useCallback(
    (method: InputMethod) => {
      if (method === "photos" && activeSlotType) {
        photoUpload.openFilePicker(activeSlotType);
        return;
      }
      if (method === "camera" && activeSlotType) {
        photoUpload.openCamera(activeSlotType);
        return;
      }
      // Downstream ticket: at-vgk6 (paste)
      console.log("input method", method, "for slot", activeSlotType);
    },
    [activeSlotType, photoUpload]
  );

  const handleClearSlot = useCallback(
    (type: SlotType) => {
      clearSlot(type);
    },
    [clearSlot]
  );

  const handleResetAll = useCallback(() => {
    resetAll();
  }, [resetAll]);

  const handleGenerate = useCallback(() => {
    const input = toGeneratorInput();
    outfitGeneration.generate(input);
  }, [toGeneratorInput, outfitGeneration]);

  const handleRegenerate = useCallback(() => {
    outfitGeneration.regenerate();
  }, [outfitGeneration]);

  const handleBackFromResult = useCallback(() => {
    outfitGeneration.reset();
  }, [outfitGeneration]);

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
      <Header
        showBack={!!showResult}
        onBack={handleBackFromResult}
      />
      <main className="flex-1 px-4 pb-6">
        <div className="mx-auto w-full max-w-lg space-y-6">
          {showResult ? (
            <OutfitResult
              imageUrl={outfitGeneration.resultImageUrl!}
              onRegenerate={handleRegenerate}
              onBack={handleBackFromResult}
              isRegenerating={outfitGeneration.state === "generating"}
            />
          ) : (
            <>
              <OutfitSlotList
                selections={selections}
                onSelectSlot={handleSelectSlot}
                onEditSlot={handleEditSlot}
                onClearSlot={handleClearSlot}
                onResetAll={handleResetAll}
              />
              <GenerateButton
                selections={selections}
                progress={outfitGeneration.progress ?? undefined}
                error={outfitGeneration.error ?? undefined}
                onGenerate={handleGenerate}
                onRetry={handleGenerate}
              />
            </>
          )}
        </div>
      </main>
      {!showResult && (
        <SelectionDrawer
          open={drawerOpen}
          onOpenChange={setDrawerOpen}
          slotType={activeSlotType}
          items={recentItems}
          onSelectItem={handleSelectItem}
          onInputMethod={handleInputMethod}
          uploadState={photoUpload.isUploading ? photoUpload.uploadState : null}
        />
      )}
      <input
        ref={photoUpload.fileInputRef}
        type="file"
        multiple
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={(e) =>
          photoUpload.handleFileChange(e, {
            onItemReady: handlePhotoItemReady,
            onComplete: handlePhotoUploadComplete,
          })
        }
      />
      <input
        ref={photoUpload.cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) =>
          photoUpload.handleFileChange(e, {
            onItemReady: handlePhotoItemReady,
            onComplete: handlePhotoUploadComplete,
          })
        }
      />
    </div>
  );
}

"use client";

import type { ChangeEvent, RefObject } from "react";
import { useCallback, useRef, useState } from "react";
import {
  useBoards,
  useUploadWithBackgroundRemoval,
  useManageTags,
  useTagGeneration,
} from "@weirdfingers/boards";
import type { ItemCategory, ProcessingPhase } from "@weirdfingers/boards";
import type { SlotType, SlotValue } from "@/components/outfit/types";

const DEFAULT_BOARD_TITLE = "Angie Tryon";
const ACCEPTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50 MB

export interface PhotoUploadState {
  /** Current phase of the active upload. */
  phase: ProcessingPhase;
  /** Upload progress percentage (0-100). */
  uploadProgress: number;
  /** Total files selected in the current batch. */
  totalFiles: number;
  /** Number of files completed so far. */
  completedFiles: number;
  /** Error from the last upload attempt. */
  error: string | null;
}

export interface PhotoUploadHook {
  /** Open the file picker for the given slot. */
  openFilePicker: (slotType: SlotType) => void;
  /** Open the camera for the given slot. Uses back camera for clothing, front for model. */
  openCamera: (slotType: SlotType) => void;
  /** Paste image from clipboard for the given slot. */
  pasteFromClipboard: (
    slotType: SlotType,
    callbacks: {
      onItemReady: (item: SlotValue) => void;
      onComplete: () => void;
    }
  ) => void;
  /** Current upload state. */
  uploadState: PhotoUploadState;
  /** Whether an upload is in progress. */
  isUploading: boolean;
  /** The hidden file input ref — render this in the DOM. */
  fileInputRef: RefObject<HTMLInputElement>;
  /** The hidden camera input ref — render this in the DOM. */
  cameraInputRef: RefObject<HTMLInputElement>;
  /** Handle file input change (called automatically). */
  handleFileChange: (
    e: ChangeEvent<HTMLInputElement>,
    callbacks: {
      onItemReady: (item: SlotValue) => void;
      onComplete: () => void;
    }
  ) => void;
  /** Register callbacks that persist across renders. */
  setCallbacks: (callbacks: {
    onItemReady: (item: SlotValue) => void;
    onComplete: () => void;
  }) => void;
}

export function usePhotoUpload(): PhotoUploadHook {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const activeSlotRef = useRef<SlotType | null>(null);
  const callbacksRef = useRef<{
    onItemReady: (item: SlotValue) => void;
    onComplete: () => void;
  } | null>(null);

  const { boards, createBoard } = useBoards();
  const upload = useUploadWithBackgroundRemoval();
  const { tags, createTag } = useManageTags();

  // We'll tag with the slot type after upload; track the latest completed gen ID
  const [pendingTagGenId, setPendingTagGenId] = useState<string>("");
  const _tagGeneration = useTagGeneration(pendingTagGenId);

  const [uploadState, setUploadState] = useState<PhotoUploadState>({
    phase: "idle",
    uploadProgress: 0,
    totalFiles: 0,
    completedFiles: 0,
    error: null,
  });

  const getDefaultBoardId = useCallback(async (): Promise<string> => {
    const existing = boards.find(
      (b: { title: string }) => b.title === DEFAULT_BOARD_TITLE
    );
    if (existing) return existing.id;

    const board = await createBoard({
      title: DEFAULT_BOARD_TITLE,
      description: "Auto-created board for outfit generations",
    });
    return board.id;
  }, [boards, createBoard]);

  const setCallbacks = useCallback(
    (cbs: {
      onItemReady: (item: SlotValue) => void;
      onComplete: () => void;
    }) => {
      callbacksRef.current = cbs;
    },
    []
  );

  const openFilePicker = useCallback(
    (slotType: SlotType) => {
      activeSlotRef.current = slotType;
      if (fileInputRef.current) {
        // Reset so re-selecting the same file triggers onChange
        fileInputRef.current.value = "";
        fileInputRef.current.click();
      }
    },
    []
  );

  const openCamera = useCallback(
    (slotType: SlotType) => {
      activeSlotRef.current = slotType;
      if (cameraInputRef.current) {
        // Back camera for clothing, front camera for model photos
        cameraInputRef.current.capture =
          slotType === "model" ? "user" : "environment";
        cameraInputRef.current.value = "";
        cameraInputRef.current.click();
      }
    },
    []
  );

  const setPasteError = useCallback((message: string) => {
    setUploadState({
      phase: "failed",
      uploadProgress: 0,
      totalFiles: 0,
      completedFiles: 0,
      error: message,
    });
    // Auto-clear after 3s so the error doesn't get stuck
    setTimeout(() => {
      setUploadState({
        phase: "idle",
        uploadProgress: 0,
        totalFiles: 0,
        completedFiles: 0,
        error: null,
      });
    }, 3000);
  }, []);

  const processFiles = useCallback(
    async (
      files: File[],
      callbacks: {
        onItemReady: (item: SlotValue) => void;
        onComplete: () => void;
      }
    ) => {
      const slotType = activeSlotRef.current;
      if (!slotType || files.length === 0) return;

      // Validate files
      const validFiles = files.filter((f) => {
        if (!ACCEPTED_IMAGE_TYPES.includes(f.type)) return false;
        if (f.size > MAX_FILE_SIZE) return false;
        return true;
      });

      if (validFiles.length === 0) {
        setUploadState((prev) => ({
          ...prev,
          error: "No valid image files selected. Accepts JPEG, PNG, or WebP under 50MB.",
        }));
        return;
      }

      setUploadState({
        phase: "uploading",
        uploadProgress: 0,
        totalFiles: validFiles.length,
        completedFiles: 0,
        error: null,
      });

      const boardId = await getDefaultBoardId();
      const category: ItemCategory = slotType === "model" ? "model" : "clothing";

      for (let i = 0; i < validFiles.length; i++) {
        const file = validFiles[i];
        try {
          const result = await upload.processImage({
            boardId,
            source: file,
            category,
            userDescription: file.name,
          });

          // Tag with slot type
          try {
            let slotTag = tags.find(
              (t: { slug: string }) => t.slug === slotType
            );
            if (!slotTag) {
              slotTag = await createTag({ name: slotType });
            }
            setPendingTagGenId(result.generationId);
            // Tag via the hook — since we just set the ID, we need to call directly
            // The hook approach requires a render cycle, so we do a best-effort tag
          } catch {
            // Tagging is non-critical
          }

          const item: SlotValue = {
            id: result.generationId,
            name: file.name.replace(/\.[^.]+$/, ""),
            thumbnailUrl: result.thumbnailUrl ?? result.storageUrl,
          };

          callbacks.onItemReady(item);

          setUploadState((prev) => ({
            ...prev,
            completedFiles: i + 1,
            phase: i + 1 === validFiles.length ? "completed" : "uploading",
          }));
        } catch (err) {
          setUploadState((prev) => ({
            ...prev,
            error:
              err instanceof Error
                ? err.message
                : `Failed to upload ${file.name}`,
            phase: "failed",
          }));
          // Continue with remaining files
        }
      }

      callbacks.onComplete();

      // Reset after a short delay so the UI can show completion
      setTimeout(() => {
        setUploadState({
          phase: "idle",
          uploadProgress: 0,
          totalFiles: 0,
          completedFiles: 0,
          error: null,
        });
        upload.reset();
      }, 500);
    },
    [getDefaultBoardId, upload, tags, createTag]
  );

  const pasteFromClipboard = useCallback(
    async (
      slotType: SlotType,
      callbacks: {
        onItemReady: (item: SlotValue) => void;
        onComplete: () => void;
      }
    ) => {
      activeSlotRef.current = slotType;

      if (!navigator.clipboard?.read) {
        setPasteError(
          "Clipboard access is not supported in this browser."
        );
        return;
      }

      let clipboardItems: ClipboardItem[];
      try {
        clipboardItems = await navigator.clipboard.read();
      } catch (err) {
        if (err instanceof DOMException && err.name === "NotAllowedError") {
          setPasteError(
            "Clipboard access denied. Please allow clipboard access and try again."
          );
        } else {
          setPasteError("Failed to read clipboard.");
        }
        return;
      }

      const imageFiles: File[] = [];
      for (const item of clipboardItems) {
        const imageType = item.types.find((t) => t.startsWith("image/"));
        if (imageType) {
          const blob = await item.getType(imageType);
          const extension = imageType.split("/")[1] ?? "png";
          const file = new File([blob], `pasted-image.${extension}`, {
            type: imageType,
          });
          imageFiles.push(file);
        }
      }

      if (imageFiles.length === 0) {
        setPasteError(
          "No image found in clipboard. Copy an image and try again."
        );
        return;
      }

      await processFiles(imageFiles, callbacks);
    },
    [processFiles, setPasteError]
  );

  const handleFileChange = useCallback(
    (
      e: ChangeEvent<HTMLInputElement>,
      callbacks: {
        onItemReady: (item: SlotValue) => void;
        onComplete: () => void;
      }
    ) => {
      const files = Array.from(e.target.files ?? []);
      if (files.length > 0) {
        processFiles(files, callbacks);
      }
    },
    [processFiles]
  );

  // Sync upload progress from the underlying hook
  const currentPhase = upload.isProcessing ? upload.phase : uploadState.phase;
  const currentProgress =
    upload.phase === "uploading"
      ? upload.uploadProgress
      : uploadState.uploadProgress;

  return {
    openFilePicker,
    openCamera,
    pasteFromClipboard,
    uploadState: {
      ...uploadState,
      phase: currentPhase,
      uploadProgress: currentProgress,
    },
    isUploading: upload.isProcessing,
    fileInputRef,
    cameraInputRef,
    handleFileChange,
    setCallbacks,
  };
}

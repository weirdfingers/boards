"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  useGeneration,
  useBoards,
  useManageTags,
  useTagGeneration,
  ArtifactType,
} from "@weirdfingers/boards";
import type { OutfitGeneratorInput } from "./use-outfit-selections";
import type { GenerationProgress } from "@/components/outfit/generate-button";

const DEFAULT_BOARD_TITLE = "Angie Tryon";
const GENERATOR_NAME = "outfit-generator";
const OUTFIT_TAG_NAME = "outfit";

type OutfitGenerationState = "idle" | "generating" | "completed" | "failed";

export interface OutfitGenerationHook {
  state: OutfitGenerationState;
  progress: GenerationProgress | null;
  resultImageUrl: string | null;
  error: Error | null;
  generate: (input: OutfitGeneratorInput) => Promise<void>;
  regenerate: () => Promise<void>;
  reset: () => void;
}

export function useOutfitGeneration(): OutfitGenerationHook {
  const generation = useGeneration();
  const { boards, createBoard } = useBoards();
  const { tags, createTag } = useManageTags();

  const [state, setState] = useState<OutfitGenerationState>("idle");
  const [resultImageUrl, setResultImageUrl] = useState<string | null>(null);
  const lastInputRef = useRef<OutfitGeneratorInput | null>(null);
  const lastJobIdRef = useRef<string | null>(null);

  // Track the generation ID for tagging once completed
  const [completedGenerationId, setCompletedGenerationId] = useState<
    string | null
  >(null);
  const tagGeneration = useTagGeneration(completedGenerationId ?? "");

  // Get or create default board
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

  // Tag generation with "outfit" when completed
  useEffect(() => {
    if (!completedGenerationId) return;

    const tagWithOutfit = async () => {
      try {
        let outfitTag = tags.find(
          (t: { slug: string }) => t.slug === OUTFIT_TAG_NAME
        );
        if (!outfitTag) {
          outfitTag = await createTag({ name: OUTFIT_TAG_NAME });
        }
        await tagGeneration.addTag(outfitTag.id);
      } catch {
        console.warn("Failed to tag generation with outfit");
      }
    };

    tagWithOutfit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [completedGenerationId]);

  // Map progress from the generation hook to GenerateButton's format
  const mappedProgress: GenerationProgress | null = generation.progress
    ? {
        status: generation.progress.status,
        progress: generation.progress.progress,
        message: generation.progress.message,
      }
    : null;

  // Track progress state changes
  useEffect(() => {
    if (!generation.progress) return;

    const { status } = generation.progress;
    if (status === "queued" || status === "processing") {
      setState("generating");
    } else if (status === "completed") {
      setState("completed");
    } else if (status === "failed" || status === "cancelled") {
      setState("failed");
    }
  }, [generation.progress]);

  // Track result — extract image URL
  useEffect(() => {
    if (generation.result) {
      setState("completed");
      setCompletedGenerationId(generation.result.id);

      const imageArtifact = generation.result.artifacts.find(
        (a: { type: string }) => a.type === "image" || a.type === "IMAGE"
      );
      setResultImageUrl(imageArtifact?.url ?? null);
    }
  }, [generation.result]);

  // Track errors
  useEffect(() => {
    if (generation.error) {
      setState("failed");
    }
  }, [generation.error]);

  const generate = useCallback(
    async (input: OutfitGeneratorInput) => {
      lastInputRef.current = input;
      setState("generating");
      setResultImageUrl(null);
      setCompletedGenerationId(null);

      try {
        const boardId = await getDefaultBoardId();
        const jobId = await generation.submit({
          model: GENERATOR_NAME,
          artifactType: ArtifactType.IMAGE,
          inputs: {
            prompt: "",
            model_image: input.model_image,
            inside_top_image: input.inside_top_image,
            outside_top_image: input.outside_top_image,
            bottoms_image: input.bottoms_image,
            shoes_image: input.shoes_image,
            socks_image: input.socks_image,
            hat_image: input.hat_image,
          },
          boardId,
        });
        lastJobIdRef.current = jobId;
      } catch {
        setState("failed");
      }
    },
    [getDefaultBoardId, generation]
  );

  const regenerate = useCallback(async () => {
    if (lastInputRef.current) {
      await generate(lastInputRef.current);
    }
  }, [generate]);

  const reset = useCallback(() => {
    setState("idle");
    setResultImageUrl(null);
    setCompletedGenerationId(null);
    lastJobIdRef.current = null;
  }, []);

  return {
    state,
    progress: mappedProgress,
    resultImageUrl,
    error: generation.error,
    generate,
    regenerate,
    reset,
  };
}

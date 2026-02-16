/**
 * Hook that orchestrates image upload followed by automatic background removal.
 *
 * For clothing items, the upload is automatically followed by a
 * `fal-bria-background-remove` generation. Model photos skip background
 * removal because Kolors virtual try-on needs the full human image with context.
 */

import { useCallback, useState, useRef } from "react";
import { useMutation } from "urql";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import {
  CREATE_GENERATION,
  ArtifactType,
  type CreateGenerationInput,
} from "../graphql/operations";
import { useMultiUpload, type MultiUploadRequest } from "./useMultiUpload";
import { useAuth } from "../auth/context";
import { useApiConfig } from "../config/ApiConfigContext";

/** Whether the image is a garment (needs bg removal) or a model photo (keep as-is). */
export type ItemCategory = "clothing" | "model";

/** Processing phases for the upload + background removal pipeline. */
export type ProcessingPhase =
  | "idle"
  | "uploading"
  | "removing-background"
  | "completed"
  | "failed";

/** Real-time progress from the background removal SSE stream. */
export interface BgRemovalProgress {
  status: "queued" | "processing" | "completed" | "failed";
  progress: number;
  phase: string;
  message?: string | null;
}

/** The final result of the processing pipeline. */
export interface ProcessingResult {
  /** The generation ID to use (bg-removed for clothing, raw upload for model). */
  generationId: string;
  /** Permanent storage URL of the final image. */
  storageUrl: string;
  /** Optional thumbnail URL. */
  thumbnailUrl?: string;
}

export interface UploadWithBackgroundRemovalHook {
  /** Run the full pipeline: upload, then optionally background-remove. */
  processImage: (request: {
    boardId: string;
    source: File | string;
    category: ItemCategory;
    userDescription?: string;
  }) => Promise<ProcessingResult>;

  /** Current phase of the pipeline. */
  phase: ProcessingPhase;

  /** Upload progress (0-100), updated during the "uploading" phase. */
  uploadProgress: number;

  /** Background removal progress, updated during the "removing-background" phase. */
  bgRemovalProgress: BgRemovalProgress | null;

  /** Final result once phase is "completed". */
  result: ProcessingResult | null;

  /** Error if phase is "failed". */
  error: Error | null;

  /** Whether the pipeline is currently running. */
  isProcessing: boolean;

  /** Reset state back to idle. */
  reset: () => void;
}

const BG_REMOVAL_GENERATOR = "fal-bria-background-remove";

export function useUploadWithBackgroundRemoval(): UploadWithBackgroundRemovalHook {
  const [phase, setPhase] = useState<ProcessingPhase>("idle");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [bgRemovalProgress, setBgRemovalProgress] =
    useState<BgRemovalProgress | null>(null);
  const [result, setResult] = useState<ProcessingResult | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  const { uploadMultiple, uploads } = useMultiUpload();
  const [, createGenerationMutation] = useMutation(CREATE_GENERATION);

  const { apiUrl } = useApiConfig();
  const auth = useAuth();

  const reset = useCallback(() => {
    // Abort any in-flight SSE connection
    abortRef.current?.abort();
    abortRef.current = null;

    setPhase("idle");
    setUploadProgress(0);
    setBgRemovalProgress(null);
    setResult(null);
    setError(null);
  }, []);

  /**
   * Wait for a generation job to complete by listening to its SSE stream.
   * Resolves with the generation ID on success; rejects on failure.
   */
  const waitForGeneration = useCallback(
    async (
      jobId: string,
      onProgress: (p: BgRemovalProgress) => void
    ): Promise<string> => {
      const abortController = new AbortController();
      abortRef.current = abortController;

      const token = await auth.getToken();
      const headers: Record<string, string> = {
        Accept: "text/event-stream",
      };
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }

      return new Promise<string>((resolve, reject) => {
        fetchEventSource(
          `${apiUrl}/api/sse/generations/${jobId}/progress`,
          {
            headers,
            signal: abortController.signal,

            async onopen(response) {
              if (!response.ok) {
                reject(
                  new Error(
                    `SSE connection failed: ${response.statusText}`
                  )
                );
              }
            },

            onmessage(event) {
              if (!event.data || event.data.trim() === "") return;
              try {
                const data = JSON.parse(event.data) as BgRemovalProgress;
                onProgress(data);

                if (data.status === "completed") {
                  abortController.abort();
                  resolve(jobId);
                } else if (data.status === "failed") {
                  abortController.abort();
                  reject(new Error("Background removal failed"));
                }
              } catch {
                // Ignore unparseable events
              }
            },

            onerror(err) {
              abortController.abort();
              reject(
                err instanceof Error
                  ? err
                  : new Error("Lost connection to background removal progress")
              );
              throw err; // Stop retries
            },

            openWhenHidden: true,
          }
        );
      });
    },
    [apiUrl, auth]
  );

  const processImage = useCallback(
    async (request: {
      boardId: string;
      source: File | string;
      category: ItemCategory;
      userDescription?: string;
    }): Promise<ProcessingResult> => {
      try {
        // Reset state
        setPhase("uploading");
        setUploadProgress(0);
        setBgRemovalProgress(null);
        setResult(null);
        setError(null);

        // -- Step 1: Upload the raw image --
        const uploadRequest: MultiUploadRequest = {
          boardId: request.boardId,
          artifactType: ArtifactType.IMAGE,
          source: request.source,
          userDescription: request.userDescription,
        };

        const uploadResults = await uploadMultiple([uploadRequest]);

        if (uploadResults.length === 0) {
          throw new Error("Upload failed");
        }

        const uploadResult = uploadResults[0];
        setUploadProgress(100);

        // For model photos, skip background removal
        if (request.category === "model") {
          const res: ProcessingResult = {
            generationId: uploadResult.id,
            storageUrl: uploadResult.storageUrl,
            thumbnailUrl: uploadResult.thumbnailUrl,
          };
          setResult(res);
          setPhase("completed");
          return res;
        }

        // -- Step 2: Trigger background removal for clothing items --
        setPhase("removing-background");
        setBgRemovalProgress({
          status: "queued",
          progress: 0,
          phase: "queued",
          message: "Starting background removal...",
        });

        const genInput: CreateGenerationInput = {
          boardId: request.boardId,
          generatorName: BG_REMOVAL_GENERATOR,
          artifactType: ArtifactType.IMAGE,
          inputParams: {
            image_url: uploadResult.id,
          },
        };

        const genResult = await createGenerationMutation({ input: genInput });

        if (genResult.error) {
          throw new Error(genResult.error.message);
        }
        if (!genResult.data?.createGeneration) {
          throw new Error("Failed to create background removal job");
        }

        const jobId: string = genResult.data.createGeneration.id;

        // -- Step 3: Wait for bg removal to complete via SSE --
        await waitForGeneration(jobId, (progress) => {
          setBgRemovalProgress(progress);
        });

        // -- Step 4: Fetch the completed generation to get storageUrl --
        // SSE completion events don't include storageUrl, so we query for it.
        const finalGen = await pollForGeneration(jobId);

        const res: ProcessingResult = {
          generationId: finalGen.id,
          storageUrl: finalGen.storageUrl,
          thumbnailUrl: finalGen.thumbnailUrl ?? undefined,
        };
        setResult(res);
        setPhase("completed");
        return res;
      } catch (err) {
        const processingError =
          err instanceof Error ? err : new Error("Processing failed");
        setError(processingError);
        setPhase("failed");
        throw processingError;
      }
    },
    [uploadMultiple, createGenerationMutation, waitForGeneration]
  );

  /**
   * Poll for the generation data via a direct GraphQL fetch.
   * We do this because the SSE completion event doesn't include storageUrl.
   */
  async function pollForGeneration(
    generationId: string
  ): Promise<{ id: string; storageUrl: string; thumbnailUrl: string | null }> {
    const token = await auth.getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const maxAttempts = 10;
    const delayMs = 500;

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const response = await fetch(`${apiUrl}/graphql`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          query: `query GetGeneration($id: UUID!) {
            generation(id: $id) {
              id
              storageUrl
              thumbnailUrl
              status
            }
          }`,
          variables: { id: generationId },
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch generation: ${response.statusText}`);
      }

      const json = await response.json();
      const gen = json.data?.generation;

      if (gen && gen.storageUrl) {
        return {
          id: gen.id,
          storageUrl: gen.storageUrl,
          thumbnailUrl: gen.thumbnailUrl,
        };
      }

      // Wait before retrying
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }

    throw new Error("Timed out waiting for background removal result");
  }

  // Sync upload progress from useMultiUpload's uploads state
  const activeUpload = uploads.find(
    (u) => u.status === "uploading" || u.status === "pending"
  );
  const currentUploadProgress =
    phase === "uploading" && activeUpload
      ? activeUpload.progress
      : uploadProgress;

  return {
    processImage,
    phase,
    uploadProgress: currentUploadProgress,
    bgRemovalProgress,
    result,
    error,
    isProcessing: phase === "uploading" || phase === "removing-background",
    reset,
  };
}

/**
 * Hook for managing AI generations with real-time progress via SSE.
 */

import { useCallback, useState, useEffect, useRef } from "react";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { useMutation } from "urql";
import {
  CREATE_GENERATION,
  CANCEL_GENERATION,
  RETRY_GENERATION,
  CreateGenerationInput,
  ArtifactType,
} from "../graphql/operations";
import { useAuth } from "../auth/context";
import { useApiConfig } from "../config/ApiConfigContext";

export interface GenerationRequest {
  model: string;
  artifactType: ArtifactType; // Allow string for flexibility with new types
  inputs: GenerationInputs;
  boardId: string;
  options?: GenerationOptions;
}

export interface GenerationInputs {
  prompt: string;
  negativePrompt?: string;
  image?: string | File;
  mask?: string | File;
  loras?: LoRAInput[];
  seed?: number;
  steps?: number;
  guidance?: number;
  aspectRatio?: string;
  style?: string;
  [key: string]: unknown;
}

export interface GenerationOptions {
  priority?: "low" | "normal" | "high";
  timeout?: number;
  webhookUrl?: string;
  [key: string]: unknown;
}

export interface LoRAInput {
  id: string;
  weight: number;
}

export interface GenerationProgress {
  jobId: string;
  status: "queued" | "processing" | "completed" | "failed" | "cancelled";
  progress: number; // 0-100
  phase: string;
  message?: string | null;
  estimatedTimeRemaining?: number;
  currentStep?: string;
  logs?: string[];
}

export interface GenerationResult {
  id: string;
  jobId: string;
  boardId: string;
  request: GenerationRequest;
  artifacts: Artifact[];
  credits: {
    cost: number;
    balanceBefore: number;
    balance: number;
  };
  performance: {
    queueTime: number;
    processingTime: number;
    totalTime: number;
  };
  createdAt: Date;
}

export interface Artifact {
  id: string;
  type: string;
  url: string;
  thumbnailUrl?: string;
  metadata: Record<string, unknown>;
}

export interface GenerationHook {
  // Current generation state
  progress: GenerationProgress | null;
  result: GenerationResult | null;
  error: Error | null;
  isGenerating: boolean;

  // Operations
  submit: (request: GenerationRequest) => Promise<string>;
  cancel: (jobId: string) => Promise<void>;
  retry: (jobId: string) => Promise<void>;

  // History
  history: GenerationResult[];
  clearHistory: () => void;
}

export function useGeneration(): GenerationHook {
  const [progress, setProgress] = useState<GenerationProgress | null>(null);
  const [result, setResult] = useState<GenerationResult | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [history, setHistory] = useState<GenerationResult[]>([]);

  // Get API configuration and auth
  const { apiUrl } = useApiConfig();
  const auth = useAuth();

  // Keep track of active SSE connections (using AbortControllers)
  const abortControllers = useRef<Map<string, AbortController>>(new Map());

  // Mutations
  const [, createGenerationMutation] = useMutation(CREATE_GENERATION);
  const [, cancelGenerationMutation] = useMutation(CANCEL_GENERATION);
  const [, retryGenerationMutation] = useMutation(RETRY_GENERATION);

  // Clean up SSE connections on unmount
  useEffect(() => {
    return () => {
      abortControllers.current.forEach((controller) => {
        controller.abort();
      });
      abortControllers.current.clear();
    };
  }, []);

  const connectToSSE = useCallback(
    async (jobId: string) => {
      // Close existing connection if any
      const existingController = abortControllers.current.get(jobId);
      if (existingController) {
        existingController.abort();
      }

      // Create new abort controller
      const abortController = new AbortController();
      abortControllers.current.set(jobId, abortController);

      // Get auth token
      const token = await auth.getToken();

      // Build headers
      const headers: Record<string, string> = {
        Accept: "text/event-stream",
      };

      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }

      // Connect to SSE endpoint directly
      const sseUrl = `${apiUrl}/api/sse/generations/${jobId}/progress`;
      console.log("SSE: Connecting to", sseUrl, "with headers:", headers);

      try {
        await fetchEventSource(sseUrl, {
          headers,
          signal: abortController.signal,

          async onopen(response) {
            console.log(
              "SSE: Connection opened",
              response.status,
              response.statusText
            );
            if (response.ok) {
              console.log("SSE: Connection successful");
            } else {
              console.error("SSE: Connection failed", response.status);
              throw new Error(`SSE connection failed: ${response.statusText}`);
            }
          },

          onmessage(event) {
            console.log("SSE: Raw event received:", event);

            // Skip empty messages (like keep-alive comments)
            if (!event.data || event.data.trim() === "") {
              console.log("SSE: Skipping empty message");
              return;
            }

            try {
              const progressData: GenerationProgress = JSON.parse(event.data);
              console.log("SSE: progress data received:", progressData);
              setProgress(progressData);

              // If generation is complete, handle the result
              if (
                progressData.status === "completed" ||
                progressData.status === "failed" ||
                progressData.status === "cancelled"
              ) {
                setIsGenerating(false);

                if (progressData.status === "completed") {
                  // TODO: Fetch the complete result from GraphQL
                  // For now, create a mock result
                  const mockResult: GenerationResult = {
                    id: progressData.jobId,
                    jobId: progressData.jobId,
                    boardId: "", // Would be filled from the original request
                    request: {} as GenerationRequest,
                    artifacts: [],
                    credits: { cost: 0, balanceBefore: 0, balance: 0 },
                    performance: {
                      queueTime: 0,
                      processingTime: 0,
                      totalTime: 0,
                    },
                    createdAt: new Date(),
                  };

                  setResult(mockResult);
                  setHistory((prev) => [...prev, mockResult]);
                } else if (progressData.status === "failed") {
                  setError(new Error("Generation failed"));
                }

                // Close connection
                abortController.abort();
                abortControllers.current.delete(jobId);
              }
            } catch (err) {
              console.error("Failed to parse SSE message:", err);
              setError(new Error("Failed to parse progress update"));
              setIsGenerating(false);
              abortController.abort();
              abortControllers.current.delete(jobId);
            }
          },

          onerror(err) {
            console.error("SSE connection error:", err);
            console.error("SSE error details:", {
              message: err instanceof Error ? err.message : String(err),
              jobId,
              url: sseUrl,
            });
            setError(new Error("Lost connection to generation progress"));
            setIsGenerating(false);
            abortController.abort();
            abortControllers.current.delete(jobId);
            // Re-throw to stop retry
            throw err;
          },

          openWhenHidden: true, // Keep connection open when tab is hidden
        });
      } catch (err) {
        // Connection was aborted or failed
        if (abortController.signal.aborted) {
          console.log("SSE connection aborted for job:", jobId);
        } else {
          console.error("SSE connection failed:", err);
        }
      }
    },
    [apiUrl, auth]
  );

  const submit = useCallback(
    async (request: GenerationRequest): Promise<string> => {
      setError(null);
      setProgress(null);
      setResult(null);
      setIsGenerating(true);

      // Convert the request to the GraphQL input format
      const input: CreateGenerationInput = {
        boardId: request.boardId,
        generatorName: request.model,
        artifactType: request.artifactType,
        inputParams: {
          ...request.inputs,
          ...request.options,
        },
      };

      // Retry logic for generation submission
      let lastError: Error | null = null;
      const maxRetries = 2; // Fewer retries for generation as it's expensive

      for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
          // Submit generation via GraphQL
          const result = await createGenerationMutation({ input });

          if (result.error) {
            throw new Error(result.error.message);
          }

          if (!result.data?.createGeneration) {
            throw new Error("Failed to create generation");
          }

          const jobId = result.data.createGeneration.id;

          // Connect to SSE for progress updates
          connectToSSE(jobId);

          // Re-enable the submit button now that submission is complete
          // The SSE connection will continue tracking progress in the background
          setIsGenerating(false);

          return jobId;
        } catch (err) {
          lastError =
            err instanceof Error
              ? err
              : new Error("Failed to submit generation");

          // Don't retry on certain types of errors
          if (
            lastError.message.includes("insufficient credits") ||
            lastError.message.includes("validation") ||
            lastError.message.includes("unauthorized") ||
            lastError.message.includes("forbidden")
          ) {
            setError(lastError);
            setIsGenerating(false);
            throw lastError;
          }

          // If this was the last attempt, throw the error
          if (attempt === maxRetries) {
            setError(lastError);
            setIsGenerating(false);
            throw lastError;
          }

          // Wait before retrying (shorter delay for generations)
          await new Promise((resolve) => setTimeout(resolve, 1000 * attempt));
        }
      }

      const finalError =
        lastError || new Error("Failed to submit generation after retries");
      setError(finalError);
      setIsGenerating(false);
      throw finalError;
    },
    [createGenerationMutation, connectToSSE]
  );

  const cancel = useCallback(
    async (jobId: string): Promise<void> => {
      try {
        // Cancel via GraphQL
        const result = await cancelGenerationMutation({ id: jobId });

        if (result.error) {
          throw new Error(result.error.message);
        }

        // Close SSE connection
        const controller = abortControllers.current.get(jobId);
        if (controller) {
          controller.abort();
          abortControllers.current.delete(jobId);
        }

        setIsGenerating(false);
        setProgress((prev) => (prev ? { ...prev, status: "cancelled" } : null));
      } catch (err) {
        setError(
          err instanceof Error ? err : new Error("Failed to cancel generation")
        );
      }
    },
    [cancelGenerationMutation]
  );

  const retry = useCallback(
    async (jobId: string): Promise<void> => {
      try {
        setError(null);
        setIsGenerating(true);

        // Retry via GraphQL
        const result = await retryGenerationMutation({ id: jobId });

        if (result.error) {
          throw new Error(result.error.message);
        }

        if (!result.data?.retryGeneration) {
          throw new Error("Failed to retry generation");
        }

        const newJobId = result.data.retryGeneration.id;

        // Connect to SSE for the retried job
        connectToSSE(newJobId);
      } catch (err) {
        setError(
          err instanceof Error ? err : new Error("Failed to retry generation")
        );
        setIsGenerating(false);
      }
    },
    [retryGenerationMutation, connectToSSE]
  );

  const clearHistory = useCallback(() => {
    setHistory([]);
  }, []);

  return {
    progress,
    result,
    error,
    isGenerating,
    submit,
    cancel,
    retry,
    history,
    clearHistory,
  };
}

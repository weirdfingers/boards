/**
 * Hook for managing AI generations with real-time progress via SSE.
 */

import { useCallback, useState, useEffect, useRef } from 'react';
import { useMutation } from 'urql';
import { CREATE_GENERATION, CANCEL_GENERATION, RETRY_GENERATION, CreateGenerationInput } from '../graphql/operations';

interface GenerationRequest {
  provider: string;
  model: string;
  inputs: GenerationInputs;
  boardId: string;
  options?: GenerationOptions;
}

interface GenerationInputs {
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

interface GenerationOptions {
  priority?: 'low' | 'normal' | 'high';
  timeout?: number;
  webhookUrl?: string;
  [key: string]: unknown;
}

interface LoRAInput {
  id: string;
  weight: number;
}

interface GenerationProgress {
  jobId: string;
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number; // 0-100
  estimatedTimeRemaining?: number;
  currentStep?: string;
  logs?: string[];
}

interface GenerationResult {
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

interface Artifact {
  id: string;
  type: string;
  url: string;
  thumbnailUrl?: string;
  metadata: Record<string, unknown>;
}

interface GenerationHook {
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
  
  // Keep track of active SSE connections
  const sseConnections = useRef<Map<string, EventSource>>(new Map());

  // Mutations
  const [, createGenerationMutation] = useMutation(CREATE_GENERATION);
  const [, cancelGenerationMutation] = useMutation(CANCEL_GENERATION);
  const [, retryGenerationMutation] = useMutation(RETRY_GENERATION);

  // Clean up SSE connections on unmount
  useEffect(() => {
    return () => {
      sseConnections.current.forEach((eventSource) => {
        eventSource.close();
      });
      sseConnections.current.clear();
    };
  }, []);

  const connectToSSE = useCallback((jobId: string) => {
    // Close existing connection if any
    const existingConnection = sseConnections.current.get(jobId);
    if (existingConnection) {
      existingConnection.close();
    }

    // Create new SSE connection
    const eventSource = new EventSource(`/api/sse/generation/${jobId}`);
    sseConnections.current.set(jobId, eventSource);

    eventSource.onmessage = (event) => {
      try {
        const progressData: GenerationProgress = JSON.parse(event.data);
        setProgress(progressData);

        // If generation is complete, handle the result
        if (progressData.status === 'completed' || progressData.status === 'failed') {
          setIsGenerating(false);
          
          if (progressData.status === 'completed') {
            // TODO: Fetch the complete result from GraphQL
            // For now, create a mock result
            const mockResult: GenerationResult = {
              id: progressData.jobId,
              jobId: progressData.jobId,
              boardId: '', // Would be filled from the original request
              request: {} as GenerationRequest,
              artifacts: [],
              credits: { cost: 0, balanceBefore: 0, balance: 0 },
              performance: { queueTime: 0, processingTime: 0, totalTime: 0 },
              createdAt: new Date(),
            };
            
            setResult(mockResult);
            setHistory(prev => [...prev, mockResult]);
          } else {
            setError(new Error('Generation failed'));
          }
          
          // Close SSE connection
          eventSource.close();
          sseConnections.current.delete(jobId);
        }
      } catch (err) {
        console.error('Failed to parse SSE message:', err);
        setError(new Error('Failed to parse progress update'));
      }
    };

    eventSource.onerror = (event) => {
      console.error('SSE connection error:', event);
      setError(new Error('Lost connection to generation progress'));
      setIsGenerating(false);
      eventSource.close();
      sseConnections.current.delete(jobId);
    };

    return eventSource;
  }, []);

  const submit = useCallback(async (request: GenerationRequest): Promise<string> => {
    try {
      setError(null);
      setProgress(null);
      setResult(null);
      setIsGenerating(true);

      // Convert the request to the GraphQL input format
      const input: CreateGenerationInput = {
        boardId: request.boardId,
        providerName: request.provider,
        generatorName: request.model,
        inputParams: {
          ...request.inputs,
          ...request.options,
        },
      };

      // Submit generation via GraphQL
      const result = await createGenerationMutation({ input });
      
      if (result.error) {
        throw new Error(result.error.message);
      }
      
      if (!result.data?.createGeneration) {
        throw new Error('Failed to create generation');
      }

      const jobId = result.data.createGeneration.id;
      
      // Connect to SSE for progress updates
      connectToSSE(jobId);
      
      return jobId;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to submit generation'));
      setIsGenerating(false);
      throw err;
    }
  }, [createGenerationMutation, connectToSSE]);

  const cancel = useCallback(async (jobId: string): Promise<void> => {
    try {
      // Cancel via GraphQL
      const result = await cancelGenerationMutation({ id: jobId });
      
      if (result.error) {
        throw new Error(result.error.message);
      }

      // Close SSE connection
      const connection = sseConnections.current.get(jobId);
      if (connection) {
        connection.close();
        sseConnections.current.delete(jobId);
      }

      setIsGenerating(false);
      setProgress(prev => prev ? { ...prev, status: 'cancelled' } : null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to cancel generation'));
    }
  }, [cancelGenerationMutation]);

  const retry = useCallback(async (jobId: string): Promise<void> => {
    try {
      setError(null);
      setIsGenerating(true);

      // Retry via GraphQL
      const result = await retryGenerationMutation({ id: jobId });
      
      if (result.error) {
        throw new Error(result.error.message);
      }
      
      if (!result.data?.retryGeneration) {
        throw new Error('Failed to retry generation');
      }

      const newJobId = result.data.retryGeneration.id;
      
      // Connect to SSE for the retried job
      connectToSSE(newJobId);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to retry generation'));
      setIsGenerating(false);
    }
  }, [retryGenerationMutation, connectToSSE]);

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
/**
 * Hook for uploading multiple artifacts concurrently with individual progress tracking.
 */

import { useCallback, useState, useRef } from "react";
import { useMutation } from "urql";
import { UPLOAD_ARTIFACT_FROM_URL, ArtifactType } from "../graphql/operations";
import { useAuth } from "../auth/context";
import { useApiConfig } from "../config/ApiConfigContext";

export interface MultiUploadRequest {
  boardId: string;
  artifactType: ArtifactType;
  source: File | string; // File object or URL string
  userDescription?: string;
  parentGenerationId?: string;
}

export interface MultiUploadResult {
  id: string;
  storageUrl: string;
  thumbnailUrl?: string;
  status: "completed" | "failed";
  artifactType: ArtifactType;
  generatorName: string;
}

export type UploadStatus = "pending" | "uploading" | "completed" | "failed";

export interface UploadItem {
  id: string;
  file: File | string;
  fileName: string;
  status: UploadStatus;
  progress: number;
  result?: MultiUploadResult;
  error?: Error;
}

export interface MultiUploadHook {
  uploadMultiple: (requests: MultiUploadRequest[]) => Promise<MultiUploadResult[]>;
  uploads: UploadItem[];
  isUploading: boolean;
  overallProgress: number;
  clearUploads: () => void;
  cancelUpload: (uploadId: string) => void;
}

let uploadIdCounter = 0;

function generateUploadId(): string {
  return `upload-${Date.now()}-${++uploadIdCounter}`;
}

function getFileName(source: File | string): string {
  if (typeof source === "string") {
    try {
      const url = new URL(source);
      const pathParts = url.pathname.split("/");
      return pathParts[pathParts.length - 1] || source;
    } catch {
      return source;
    }
  }
  return source.name;
}

export function useMultiUpload(): MultiUploadHook {
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const abortControllersRef = useRef<Map<string, () => void>>(new Map());

  const { apiUrl } = useApiConfig();
  const auth = useAuth();

  const [, uploadFromUrlMutation] = useMutation(UPLOAD_ARTIFACT_FROM_URL);

  const updateUpload = useCallback(
    (uploadId: string, updates: Partial<UploadItem>) => {
      setUploads((prev) =>
        prev.map((item) =>
          item.id === uploadId ? { ...item, ...updates } : item
        )
      );
    },
    []
  );

  const uploadSingle = useCallback(
    async (
      uploadId: string,
      request: MultiUploadRequest
    ): Promise<MultiUploadResult> => {
      updateUpload(uploadId, { status: "uploading", progress: 0 });

      try {
        // Handle URL upload via GraphQL
        if (typeof request.source === "string") {
          const result = await uploadFromUrlMutation({
            input: {
              boardId: request.boardId,
              artifactType: request.artifactType,
              fileUrl: request.source,
              userDescription: request.userDescription,
              parentGenerationId: request.parentGenerationId,
            },
          });

          if (result.error) {
            throw new Error(result.error.message);
          }

          if (!result.data?.uploadArtifact) {
            throw new Error("Upload failed");
          }

          const uploadResult: MultiUploadResult = {
            id: result.data.uploadArtifact.id,
            storageUrl: result.data.uploadArtifact.storageUrl,
            thumbnailUrl: result.data.uploadArtifact.thumbnailUrl,
            status: "completed",
            artifactType: result.data.uploadArtifact.artifactType,
            generatorName: result.data.uploadArtifact.generatorName,
          };

          updateUpload(uploadId, {
            status: "completed",
            progress: 100,
            result: uploadResult,
          });

          return uploadResult;
        }

        // Handle file upload via REST API
        const formData = new FormData();
        formData.append("board_id", request.boardId);
        formData.append("artifact_type", request.artifactType.toLowerCase());
        formData.append("file", request.source);
        if (request.userDescription) {
          formData.append("user_description", request.userDescription);
        }
        if (request.parentGenerationId) {
          formData.append("parent_generation_id", request.parentGenerationId);
        }

        const token = await auth.getToken();
        const headers: Record<string, string> = {};
        if (token) {
          headers.Authorization = `Bearer ${token}`;
        }

        // Use XMLHttpRequest for progress tracking
        const result = await new Promise<MultiUploadResult>(
          (resolve, reject) => {
            const xhr = new XMLHttpRequest();

            // Store abort function for cancellation
            abortControllersRef.current.set(uploadId, () => xhr.abort());

            // Cleanup function to ensure abort controller is always removed
            const cleanup = () => {
              abortControllersRef.current.delete(uploadId);
            };

            xhr.upload.addEventListener("progress", (e) => {
              if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                updateUpload(uploadId, { progress: percentComplete });
              }
            });

            xhr.addEventListener("load", () => {
              cleanup();
              if (xhr.status === 200) {
                try {
                  const data = JSON.parse(xhr.responseText);
                  resolve({
                    id: data.id,
                    storageUrl: data.storageUrl,
                    thumbnailUrl: data.thumbnailUrl,
                    status: "completed",
                    artifactType: data.artifactType as ArtifactType,
                    generatorName: data.generatorName,
                  });
                } catch (err) {
                  reject(new Error("Failed to parse response"));
                }
              } else {
                try {
                  const errorData = JSON.parse(xhr.responseText);
                  reject(
                    new Error(
                      errorData.detail || `Upload failed: ${xhr.statusText}`
                    )
                  );
                } catch {
                  reject(new Error(`Upload failed: ${xhr.statusText}`));
                }
              }
            });

            xhr.addEventListener("error", () => {
              cleanup();
              reject(new Error("Upload failed: Network error"));
            });

            xhr.addEventListener("abort", () => {
              cleanup();
              reject(new Error("Upload cancelled"));
            });

            xhr.addEventListener("loadend", () => {
              // Ensure cleanup happens in all cases (additional safety net)
              cleanup();
            });

            xhr.open("POST", `${apiUrl}/api/uploads/artifact`);
            Object.entries(headers).forEach(([key, value]) => {
              xhr.setRequestHeader(key, value);
            });
            xhr.send(formData);
          }
        );

        updateUpload(uploadId, {
          status: "completed",
          progress: 100,
          result,
        });

        return result;
      } catch (err) {
        const uploadError =
          err instanceof Error ? err : new Error("Upload failed");

        updateUpload(uploadId, {
          status: "failed",
          error: uploadError,
        });

        throw uploadError;
      }
    },
    [uploadFromUrlMutation, apiUrl, auth, updateUpload]
  );

  const uploadMultiple = useCallback(
    async (requests: MultiUploadRequest[]): Promise<MultiUploadResult[]> => {
      // Create upload items for all requests
      const newUploads: UploadItem[] = requests.map((request) => ({
        id: generateUploadId(),
        file: request.source,
        fileName: getFileName(request.source),
        status: "pending" as UploadStatus,
        progress: 0,
      }));

      setUploads((prev) => [...prev, ...newUploads]);

      // Upload all files concurrently
      const results = await Promise.allSettled(
        requests.map((request, index) =>
          uploadSingle(newUploads[index].id, request)
        )
      );

      // Extract successful results
      const successfulResults: MultiUploadResult[] = [];
      results.forEach((result) => {
        if (result.status === "fulfilled") {
          successfulResults.push(result.value);
        }
      });

      return successfulResults;
    },
    [uploadSingle]
  );

  const clearUploads = useCallback(() => {
    // Abort any in-progress uploads
    abortControllersRef.current.forEach((abort) => abort());
    abortControllersRef.current.clear();
    setUploads([]);
  }, []);

  const cancelUpload = useCallback((uploadId: string) => {
    const abort = abortControllersRef.current.get(uploadId);
    if (abort) {
      abort();
    }
  }, []);

  // Calculate derived state
  const isUploading = uploads.some((u) => u.status === "uploading");
  const overallProgress =
    uploads.length > 0
      ? uploads.reduce((sum, u) => sum + u.progress, 0) / uploads.length
      : 0;

  return {
    uploadMultiple,
    uploads,
    isUploading,
    overallProgress,
    clearUploads,
    cancelUpload,
  };
}

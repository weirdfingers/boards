/**
 * Hook for uploading artifacts (images, videos, audio, text).
 */

import { useCallback, useState } from "react";
import { useMutation } from "urql";
import { UPLOAD_ARTIFACT_FROM_URL, ArtifactType } from "../graphql/operations";
import { useAuth } from "../auth/context";
import { useApiConfig } from "../config/ApiConfigContext";

export interface UploadRequest {
  boardId: string;
  artifactType: ArtifactType;
  source: File | string; // File object or URL string
  userDescription?: string;
  parentGenerationId?: string;
}

export interface UploadResult {
  id: string;
  storageUrl: string;
  thumbnailUrl?: string;
  status: "completed" | "failed";
  artifactType: ArtifactType;
  generatorName: string;
}

export interface UploadHook {
  upload: (request: UploadRequest) => Promise<UploadResult>;
  isUploading: boolean;
  progress: number; // 0-100
  error: Error | null;
}

export function useUpload(): UploadHook {
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<Error | null>(null);

  const { apiUrl } = useApiConfig();
  const auth = useAuth();

  const [, uploadFromUrlMutation] = useMutation(UPLOAD_ARTIFACT_FROM_URL);

  const upload = useCallback(
    async (request: UploadRequest): Promise<UploadResult> => {
      setError(null);
      setProgress(0);
      setIsUploading(true);

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

          setProgress(100);
          setIsUploading(false);

          return {
            id: result.data.uploadArtifact.id,
            storageUrl: result.data.uploadArtifact.storageUrl,
            thumbnailUrl: result.data.uploadArtifact.thumbnailUrl,
            status: "completed",
            artifactType: result.data.uploadArtifact.artifactType,
            generatorName: result.data.uploadArtifact.generatorName,
          };
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
        const result = await new Promise<UploadResult>((resolve, reject) => {
          const xhr = new XMLHttpRequest();

          xhr.upload.addEventListener("progress", (e) => {
            if (e.lengthComputable) {
              const percentComplete = (e.loaded / e.total) * 100;
              setProgress(percentComplete);
            }
          });

          xhr.addEventListener("load", () => {
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
                reject(new Error(errorData.detail || `Upload failed: ${xhr.statusText}`));
              } catch {
                reject(new Error(`Upload failed: ${xhr.statusText}`));
              }
            }
          });

          xhr.addEventListener("error", () => {
            reject(new Error("Upload failed: Network error"));
          });

          xhr.addEventListener("abort", () => {
            reject(new Error("Upload cancelled"));
          });

          xhr.open("POST", `${apiUrl}/api/uploads/artifact`);
          Object.entries(headers).forEach(([key, value]) => {
            xhr.setRequestHeader(key, value);
          });
          xhr.send(formData);
        });

        setProgress(100);
        setIsUploading(false);
        return result;
      } catch (err) {
        const uploadError =
          err instanceof Error ? err : new Error("Upload failed");
        setError(uploadError);
        setIsUploading(false);
        setProgress(0);
        throw uploadError;
      }
    },
    [uploadFromUrlMutation, apiUrl, auth]
  );

  return {
    upload,
    isUploading,
    progress,
    error,
  };
}

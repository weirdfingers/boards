"use client";

import React, { useCallback, useState, useRef } from "react";
import {
  useMultiUpload,
  ArtifactType,
  UploadItem,
  MultiUploadRequest,
} from "@weirdfingers/boards";
import { toast } from "@/components/ui/use-toast";

interface UploadArtifactProps {
  boardId: string;
  onUploadComplete?: (generationId: string) => void;
}

// Maximum file size: 100MB
const MAX_FILE_SIZE = 100 * 1024 * 1024;

// Allowed MIME types for each artifact type
const ALLOWED_MIME_TYPES = {
  image: [
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
    "image/svg+xml",
  ],
  video: [
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/webm",
    "video/mpeg",
    "video/x-matroska",
  ],
  audio: [
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
    "audio/webm",
    "audio/mp4",
    "audio/x-m4a",
  ],
  text: [
    "text/plain",
    "text/markdown",
    "application/json",
    "text/html",
    "text/csv",
  ],
};

function detectArtifactType(mimeType: string): ArtifactType {
  if (mimeType.startsWith("image/")) {
    return ArtifactType.IMAGE;
  } else if (mimeType.startsWith("video/")) {
    return ArtifactType.VIDEO;
  } else if (mimeType.startsWith("audio/")) {
    return ArtifactType.AUDIO;
  } else if (mimeType.startsWith("text/")) {
    return ArtifactType.TEXT;
  }
  return ArtifactType.IMAGE;
}

function validateFile(file: File): { valid: boolean; error?: string } {
  // Check file size
  if (file.size > MAX_FILE_SIZE) {
    return {
      valid: false,
      error: `File size exceeds maximum of 100MB (${Math.round(file.size / 1024 / 1024)}MB)`,
    };
  }

  // Check MIME type
  const mimeType = file.type.toLowerCase();
  const isValidMimeType = Object.values(ALLOWED_MIME_TYPES)
    .flat()
    .some((allowed) => mimeType === allowed.toLowerCase());

  if (!isValidMimeType) {
    return {
      valid: false,
      error: `Unsupported file type: ${file.type || "unknown"}. Please upload an image, video, audio, or text file.`,
    };
  }

  return { valid: true };
}

function validateUrl(url: string): { valid: boolean; error?: string } {
  try {
    const parsedUrl = new URL(url);
    if (parsedUrl.protocol !== "http:" && parsedUrl.protocol !== "https:") {
      return {
        valid: false,
        error: "URL must use HTTP or HTTPS protocol",
      };
    }
    return { valid: true };
  } catch {
    return {
      valid: false,
      error: "Invalid URL format",
    };
  }
}

function UploadItemRow({
  item,
  onCancel,
}: {
  item: UploadItem;
  onCancel: () => void;
}) {
  return (
    <div className="flex items-center gap-3 p-2 bg-gray-50 rounded-lg">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">
          {item.fileName}
        </p>
        {item.status === "uploading" && (
          <div className="mt-1 w-full bg-gray-200 rounded-full h-1.5">
            <div
              className="bg-orange-500 h-1.5 rounded-full transition-all duration-300"
              style={{ width: `${item.progress}%` }}
            />
          </div>
        )}
        {item.status === "failed" && item.error && (
          <p className="text-xs text-red-600 mt-1">{item.error.message}</p>
        )}
      </div>
      <div className="flex-shrink-0">
        {item.status === "pending" && (
          <span className="text-xs text-gray-500">Waiting...</span>
        )}
        {item.status === "uploading" && (
          <button
            onClick={onCancel}
            className="text-xs text-gray-500 hover:text-red-600"
          >
            Cancel
          </button>
        )}
        {item.status === "completed" && (
          <svg
            className="w-5 h-5 text-green-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        )}
        {item.status === "failed" && (
          <svg
            className="w-5 h-5 text-red-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        )}
      </div>
    </div>
  );
}

export function UploadArtifact({
  boardId,
  onUploadComplete,
}: UploadArtifactProps) {
  const {
    uploadMultiple,
    uploads,
    isUploading,
    overallProgress,
    clearUploads,
    cancelUpload,
  } = useMultiUpload();
  const [isOpen, setIsOpen] = useState(false);
  const [urlInput, setUrlInput] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFilesUpload = useCallback(
    async (files: File[]) => {
      if (files.length === 0) return;

      // Validate all files first
      const invalidFiles: string[] = [];
      const validFiles: File[] = [];

      files.forEach((file) => {
        const validation = validateFile(file);
        if (!validation.valid) {
          invalidFiles.push(`${file.name}: ${validation.error}`);
        } else {
          validFiles.push(file);
        }
      });

      // Show errors for invalid files
      if (invalidFiles.length > 0) {
        toast({
          variant: "destructive",
          title: "Some files were rejected",
          description: invalidFiles.join("; "),
        });
      }

      // Upload valid files only
      if (validFiles.length === 0) return;

      const requests: MultiUploadRequest[] = validFiles.map((file) => ({
        boardId,
        artifactType: detectArtifactType(file.type),
        source: file,
      }));

      try {
        const results = await uploadMultiple(requests);
        results.forEach((result) => {
          onUploadComplete?.(result.id);
        });
      } catch (err) {
        toast({
          variant: "destructive",
          title: "Upload failed",
          description: err instanceof Error ? err.message : "An unknown error occurred",
        });
      }
    },
    [uploadMultiple, boardId, onUploadComplete]
  );

  const handleUrlUpload = useCallback(async () => {
    if (!urlInput.trim()) return;

    // Validate URL
    const validation = validateUrl(urlInput.trim());
    if (!validation.valid) {
      toast({
        variant: "destructive",
        title: "Invalid URL",
        description: validation.error,
      });
      return;
    }

    try {
      const results = await uploadMultiple([
        {
          boardId,
          artifactType: ArtifactType.IMAGE,
          source: urlInput.trim(),
        },
      ]);
      if (results.length > 0) {
        onUploadComplete?.(results[0].id);
      }
      setUrlInput("");
    } catch (err) {
      toast({
        variant: "destructive",
        title: "URL upload failed",
        description: err instanceof Error ? err.message : "An unknown error occurred",
      });
    }
  }, [uploadMultiple, boardId, urlInput, onUploadComplete]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragActive(false);

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        handleFilesUpload(files);
      }
    },
    [handleFilesUpload]
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = () => {
    setDragActive(false);
  };

  const handlePaste = useCallback(
    async (e: React.ClipboardEvent) => {
      const items = Array.from(e.clipboardData.items);
      const imageFiles: File[] = [];

      for (const item of items) {
        if (item.type.startsWith("image/")) {
          const file = item.getAsFile();
          if (file) {
            imageFiles.push(file);
          }
        }
      }

      if (imageFiles.length > 0) {
        e.preventDefault();
        await handleFilesUpload(imageFiles);
      }
    },
    [handleFilesUpload]
  );

  const handleClose = useCallback(() => {
    setIsOpen(false);
    // Clear completed/failed uploads when closing
    if (!isUploading) {
      clearUploads();
    }
  }, [isUploading, clearUploads]);

  // Filter to show only active uploads (not completed ones unless recent)
  const activeUploads = uploads.filter(
    (u) => u.status === "pending" || u.status === "uploading"
  );
  const completedCount = uploads.filter((u) => u.status === "completed").length;
  const failedCount = uploads.filter((u) => u.status === "failed").length;

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(true)}
        className="inline-flex items-center gap-2 px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors"
      >
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
          />
        </svg>
        Upload
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-96 bg-white rounded-lg shadow-xl p-6 z-50 border border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Upload Artifacts
            </h3>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-600"
              aria-label="Close upload dialog"
            >
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* Drag and drop zone */}
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragActive
                ? "border-orange-500 bg-orange-50"
                : "border-gray-300 hover:border-gray-400"
            }`}
            role="button"
            tabIndex={0}
            aria-label="Upload files by drag and drop or click to select"
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                fileInputRef.current?.click();
              }
            }}
          >
            <input
              id="file-upload"
              ref={fileInputRef}
              type="file"
              multiple
              onChange={(e) => {
                const files = Array.from(e.target.files || []);
                if (files.length > 0) {
                  handleFilesUpload(files);
                }
                // Reset input so same files can be selected again
                e.target.value = "";
              }}
              className="hidden"
              accept="image/*,video/*,audio/*,text/*"
              aria-label="Select files to upload"
              aria-describedby="file-upload-description"
            />

            <div className="flex flex-col items-center gap-2">
              <svg
                className="w-12 h-12 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>

              <div>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="text-orange-600 hover:text-orange-700 font-medium"
                  aria-label="Choose files to upload"
                >
                  Choose files
                </button>
                <span className="text-gray-500"> or drag and drop here</span>
              </div>

              <p id="file-upload-description" className="text-sm text-gray-500">
                Images, videos, audio, and text files (max 100MB each)
              </p>
              <p className="text-xs text-gray-400">
                You can select multiple files at once
              </p>
            </div>
          </div>

          {/* URL input */}
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Or paste a URL or image
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                onPaste={handlePaste}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleUrlUpload();
                  }
                }}
                placeholder="https://example.com/image.jpg or paste an image"
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                disabled={isUploading}
              />
              <button
                onClick={handleUrlUpload}
                disabled={!urlInput.trim() || isUploading}
                className="px-6 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                Upload
              </button>
            </div>
          </div>

          {/* Upload progress list */}
          {activeUploads.length > 0 && (
            <div className="mt-4 space-y-2 max-h-48 overflow-y-auto" role="status" aria-live="polite">
              {activeUploads.map((item) => (
                <UploadItemRow
                  key={item.id}
                  item={item}
                  onCancel={() => cancelUpload(item.id)}
                />
              ))}
            </div>
          )}

          {/* Overall progress bar */}
          {isUploading && (
            <div className="mt-4" role="status" aria-live="polite" aria-atomic="true">
              <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
                <span>
                  Uploading {activeUploads.length} file
                  {activeUploads.length !== 1 ? "s" : ""}...
                </span>
                <span>{Math.round(overallProgress)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2" role="progressbar" aria-valuenow={Math.round(overallProgress)} aria-valuemin={0} aria-valuemax={100}>
                <div
                  className="bg-orange-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${overallProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Summary when uploads finish */}
          {!isUploading && uploads.length > 0 && (
            <div className="mt-4 p-3 bg-gray-50 rounded-lg" role="status" aria-live="polite">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">
                  {completedCount > 0 && (
                    <span className="text-green-600">
                      {completedCount} completed
                    </span>
                  )}
                  {completedCount > 0 && failedCount > 0 && ", "}
                  {failedCount > 0 && (
                    <span className="text-red-600">{failedCount} failed</span>
                  )}
                </span>
                <button
                  type="button"
                  onClick={clearUploads}
                  className="text-gray-500 hover:text-gray-700 text-xs"
                  aria-label="Clear upload history"
                >
                  Clear
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

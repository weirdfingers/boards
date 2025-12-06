"use client";

import React, { useCallback, useState, useRef } from "react";
import { useUpload, ArtifactType } from "@weirdfingers/boards";

interface UploadArtifactProps {
  boardId: string;
  onUploadComplete?: (generationId: string) => void;
}

export function UploadArtifact({ boardId, onUploadComplete }: UploadArtifactProps) {
  const { upload, isUploading, progress, error } = useUpload();
  const [isOpen, setIsOpen] = useState(false);
  const [urlInput, setUrlInput] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = useCallback(
    async (file: File) => {
      // Detect artifact type from file
      const type = file.type;
      let artifactType: ArtifactType = ArtifactType.IMAGE;

      if (type.startsWith("image/")) {
        artifactType = ArtifactType.IMAGE;
      } else if (type.startsWith("video/")) {
        artifactType = ArtifactType.VIDEO;
      } else if (type.startsWith("audio/")) {
        artifactType = ArtifactType.AUDIO;
      } else if (type.startsWith("text/")) {
        artifactType = ArtifactType.TEXT;
      }

      try {
        const result = await upload({
          boardId,
          artifactType,
          source: file,
        });
        onUploadComplete?.(result.id);
        setIsOpen(false);
      } catch (err) {
        console.error("Upload failed:", err);
      }
    },
    [upload, boardId, onUploadComplete]
  );

  const handleUrlUpload = useCallback(async () => {
    if (!urlInput.trim()) return;

    try {
      // Default to image for URL uploads
      const result = await upload({
        boardId,
        artifactType: ArtifactType.IMAGE,
        source: urlInput.trim(),
      });
      onUploadComplete?.(result.id);
      setUrlInput("");
      setIsOpen(false);
    } catch (err) {
      console.error("URL upload failed:", err);
    }
  }, [upload, boardId, urlInput, onUploadComplete]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragActive(false);

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        handleFileUpload(files[0]);
      }
    },
    [handleFileUpload]
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

      // Check for image in clipboard
      for (const item of items) {
        if (item.type.startsWith("image/")) {
          const file = item.getAsFile();
          if (file) {
            e.preventDefault();
            await handleFileUpload(file);
            return;
          }
        }
      }
    },
    [handleFileUpload]
  );

  if (!isOpen) {
    return (
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
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Upload Artifact</h3>
        <button
          onClick={() => setIsOpen(false)}
          className="text-gray-400 hover:text-gray-600"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
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
      >
        <input
          ref={fileInputRef}
          type="file"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFileUpload(file);
          }}
          className="hidden"
          accept="image/*,video/*,audio/*,text/*"
        />

        <div className="flex flex-col items-center gap-2">
          <svg
            className="w-12 h-12 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
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
              onClick={() => fileInputRef.current?.click()}
              className="text-orange-600 hover:text-orange-700 font-medium"
            >
              Choose a file
            </button>
            <span className="text-gray-500"> or drag and drop here</span>
          </div>

          <p className="text-sm text-gray-500">
            Images, videos, audio, and text files (max 100MB)
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

      {/* Progress bar */}
      {isUploading && (
        <div className="mt-4">
          <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
            <span>Uploading...</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-orange-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800 text-sm">{error.message}</p>
        </div>
      )}
    </div>
  );
}

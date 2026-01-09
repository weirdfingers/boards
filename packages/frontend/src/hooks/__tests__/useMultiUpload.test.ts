/**
 * Tests for useMultiUpload hook.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useMultiUpload } from "../useMultiUpload";
import { ArtifactType } from "../../graphql/operations";

// Mock dependencies
vi.mock("urql", async (importOriginal) => {
  const actual = await importOriginal<typeof import("urql")>();
  return {
    ...actual,
    useMutation: vi.fn(() => [
      {},
      vi.fn().mockResolvedValue({
        data: {
          uploadArtifact: {
            id: "test-artifact-id",
            storageUrl: "https://example.com/artifact.jpg",
            thumbnailUrl: "https://example.com/thumb.jpg",
            artifactType: "IMAGE",
            generatorName: "user-upload-image",
          },
        },
      }),
    ]),
  };
});

vi.mock("../../auth/context", () => ({
  useAuth: vi.fn(() => ({
    getToken: vi.fn().mockResolvedValue("test-token"),
  })),
}));

vi.mock("../../config/ApiConfigContext", () => ({
  useApiConfig: vi.fn(() => ({
    apiUrl: "http://localhost:8088",
  })),
}));

describe("useMultiUpload", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should initialize with empty uploads", () => {
    const { result } = renderHook(() => useMultiUpload());

    expect(result.current.uploads).toEqual([]);
    expect(result.current.isUploading).toBe(false);
    expect(result.current.overallProgress).toBe(0);
  });

  it("should handle URL upload via GraphQL", async () => {
    const { result } = renderHook(() => useMultiUpload());

    const uploadPromise = result.current.uploadMultiple([
      {
        boardId: "test-board-id",
        artifactType: ArtifactType.IMAGE,
        source: "https://example.com/image.jpg",
      },
    ]);

    // Wait for the upload to start
    await waitFor(() => {
      expect(result.current.uploads.length).toBe(1);
    });

    expect(result.current.uploads[0].fileName).toBe("image.jpg");

    // Wait for upload to complete
    const results = await uploadPromise;

    await waitFor(() => {
      expect(result.current.uploads[0].status).toBe("completed");
    });

    expect(results).toHaveLength(1);
    expect(results[0].id).toBe("test-artifact-id");
  });

  it("should handle multiple URL uploads", async () => {
    const { result } = renderHook(() => useMultiUpload());

    const uploadPromise = result.current.uploadMultiple([
      {
        boardId: "test-board-id",
        artifactType: ArtifactType.IMAGE,
        source: "https://example.com/image1.jpg",
      },
      {
        boardId: "test-board-id",
        artifactType: ArtifactType.IMAGE,
        source: "https://example.com/image2.jpg",
      },
    ]);

    await waitFor(() => {
      expect(result.current.uploads.length).toBe(2);
    });

    const results = await uploadPromise;

    await waitFor(() => {
      expect(result.current.uploads.filter((u) => u.status === "completed")).toHaveLength(2);
    });

    expect(results).toHaveLength(2);
  });

  it("should track upload progress", async () => {
    const { result } = renderHook(() => useMultiUpload());

    result.current.uploadMultiple([
      {
        boardId: "test-board-id",
        artifactType: ArtifactType.IMAGE,
        source: "https://example.com/image.jpg",
      },
    ]);

    await waitFor(() => {
      expect(result.current.uploads.length).toBeGreaterThan(0);
    });

    // Initially progress should be 0
    expect(result.current.overallProgress).toBeGreaterThanOrEqual(0);
  });

  it("should clear uploads", async () => {
    const { result } = renderHook(() => useMultiUpload());

    await result.current.uploadMultiple([
      {
        boardId: "test-board-id",
        artifactType: ArtifactType.IMAGE,
        source: "https://example.com/image.jpg",
      },
    ]);

    await waitFor(() => {
      expect(result.current.uploads.length).toBeGreaterThan(0);
    });

    result.current.clearUploads();

    await waitFor(() => {
      expect(result.current.uploads).toEqual([]);
    });
  });

  it("should extract filename from URL", async () => {
    const { result } = renderHook(() => useMultiUpload());

    result.current.uploadMultiple([
      {
        boardId: "test-board-id",
        artifactType: ArtifactType.IMAGE,
        source: "https://example.com/path/to/my-image.jpg",
      },
    ]);

    await waitFor(() => {
      expect(result.current.uploads.length).toBe(1);
    });

    expect(result.current.uploads[0].fileName).toBe("my-image.jpg");
  });

  it("should handle upload failures gracefully", async () => {
    // Mock a failed mutation
    const { useMutation } = await import("urql");
    vi.mocked(useMutation).mockReturnValueOnce([
      {},
      vi.fn().mockResolvedValue({
        error: new Error("Upload failed"),
      }),
    ]);

    const { result } = renderHook(() => useMultiUpload());

    const uploadPromise = result.current.uploadMultiple([
      {
        boardId: "test-board-id",
        artifactType: ArtifactType.IMAGE,
        source: "https://example.com/image.jpg",
      },
    ]);

    await waitFor(() => {
      expect(result.current.uploads.length).toBe(1);
    });

    const results = await uploadPromise;

    // Should return empty array when all uploads fail
    expect(results).toEqual([]);

    await waitFor(() => {
      expect(result.current.uploads[0].status).toBe("failed");
    });

    expect(result.current.uploads[0].error).toBeDefined();
  });

  it("should calculate overall progress correctly", async () => {
    const { result } = renderHook(() => useMultiUpload());

    result.current.uploadMultiple([
      {
        boardId: "test-board-id",
        artifactType: ArtifactType.IMAGE,
        source: "https://example.com/image1.jpg",
      },
      {
        boardId: "test-board-id",
        artifactType: ArtifactType.IMAGE,
        source: "https://example.com/image2.jpg",
      },
    ]);

    await waitFor(() => {
      expect(result.current.uploads.length).toBe(2);
    });

    // Wait for completion
    await waitFor(() => {
      expect(result.current.uploads.filter((u) => u.status === "completed")).toHaveLength(2);
    });

    // Overall progress should be 100 when all complete
    expect(result.current.overallProgress).toBe(100);
  });
});

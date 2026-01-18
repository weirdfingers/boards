import { describe, test, expect, beforeEach, afterEach, vi } from "vitest";
import fs from "fs-extra";
import path from "path";
import os from "os";
import { createHash } from "crypto";
import {
  fetchTemplateManifest,
  verifyChecksum,
  downloadTemplate,
  getCacheDir,
  clearCache,
  clearTemplateCache,
  getCacheSize,
  type TemplateManifest,
} from "../template-downloader.js";

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch as any;

describe("Template Downloader", () => {
  const mockManifest: TemplateManifest = {
    version: "0.8.0",
    templates: [
      {
        name: "baseboards",
        description: "Full-featured Boards application (recommended)",
        file: "template-baseboards-v0.8.0.tar.gz",
        size: 1024000,
        checksum: "sha256:abc123def456",
        frameworks: ["next.js"],
        features: ["auth", "generators", "boards", "themes"],
      },
      {
        name: "basic",
        description: "Minimal Next.js starter with @weirdfingers/boards",
        file: "template-basic-v0.8.0.tar.gz",
        size: 512000,
        checksum: "sha256:def456ghi789",
        frameworks: ["next.js"],
        features: ["minimal"],
      },
    ],
  };

  beforeEach(async () => {
    vi.clearAllMocks();
    mockFetch.mockClear();
    // Clean the actual cache directory before each test
    await clearCache().catch(() => {
      // Ignore errors if cache doesn't exist
    });
  });

  afterEach(async () => {
    // Clean up cache directory after tests
    await clearCache().catch(() => {
      // Ignore errors
    });
  });

  describe("fetchTemplateManifest", () => {
    test("fetches manifest for specific version", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => mockManifest,
      } as any);

      const result = await fetchTemplateManifest("0.8.0");

      expect(result).toEqual(mockManifest);
      expect(mockFetch).toHaveBeenCalledWith(
        "https://github.com/weirdfingers/boards/releases/download/v0.8.0/template-manifest.json",
        expect.objectContaining({
          headers: expect.objectContaining({
            "User-Agent": "@weirdfingers/baseboards-cli",
          }),
        })
      );
    });

    test("fetches latest version manifest", async () => {
      const latestRelease = {
        tag_name: "v0.9.0",
      };

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => latestRelease,
        } as any)
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({ ...mockManifest, version: "0.9.0" }),
        } as any);

      const result = await fetchTemplateManifest("latest");

      expect(result.version).toBe("0.9.0");
      expect(mockFetch).toHaveBeenCalledTimes(2);
      expect(mockFetch).toHaveBeenNthCalledWith(
        1,
        "https://api.github.com/repos/weirdfingers/boards/releases/latest",
        expect.any(Object)
      );
      expect(mockFetch).toHaveBeenNthCalledWith(
        2,
        "https://github.com/weirdfingers/boards/releases/download/v0.9.0/template-manifest.json",
        expect.any(Object)
      );
    });

    test("throws error for 404 (version not found)", async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 404,
        statusText: "Not Found",
      } as any);

      await expect(fetchTemplateManifest("99.99.99")).rejects.toThrow(
        "Version 99.99.99 not found"
      );
    });

    test("throws error for network failures", async () => {
      mockFetch.mockRejectedValue(new Error("Network error"));

      await expect(fetchTemplateManifest("0.8.0")).rejects.toThrow(
        "Failed to fetch template manifest"
      );
    });

    test("throws error for invalid manifest structure", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ version: "0.8.0" }), // Missing templates array
      } as any);

      await expect(fetchTemplateManifest("0.8.0")).rejects.toThrow(
        "Invalid manifest structure"
      );
    });

    test("retries on transient failures", async () => {
      mockFetch
        .mockRejectedValueOnce(new Error("Temporary network error"))
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => mockManifest,
        } as any);

      const result = await fetchTemplateManifest("0.8.0");

      expect(result).toEqual(mockManifest);
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    test("throws error after max retries", async () => {
      mockFetch.mockRejectedValue(new Error("Persistent network error"));

      await expect(fetchTemplateManifest("0.8.0")).rejects.toThrow(
        "Failed to fetch template manifest"
      );
      expect(mockFetch).toHaveBeenCalledTimes(3); // Max retries
    });
  });

  describe("verifyChecksum", () => {
    let tempDir: string;
    let testFilePath: string;

    beforeEach(async () => {
      tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "template-test-"));
      testFilePath = path.join(tempDir, "test-file.txt");
    });

    afterEach(async () => {
      await fs.remove(tempDir);
    });

    test("returns true for matching checksum", async () => {
      const content = "test content";
      await fs.writeFile(testFilePath, content);

      const hash = createHash("sha256");
      hash.update(content);
      const expectedChecksum = `sha256:${hash.digest("hex")}`;

      const result = await verifyChecksum(testFilePath, expectedChecksum);

      expect(result).toBe(true);
    });

    test("throws error for checksum mismatch", async () => {
      await fs.writeFile(testFilePath, "test content");

      await expect(
        verifyChecksum(testFilePath, "sha256:wrongchecksum123")
      ).rejects.toThrow("Checksum mismatch");
    });

    test("throws error for invalid checksum format", async () => {
      await fs.writeFile(testFilePath, "test content");

      await expect(
        verifyChecksum(testFilePath, "md5:abc123")
      ).rejects.toThrow('Invalid checksum format: must start with "sha256:"');
    });

    test("throws error for missing file", async () => {
      const nonExistentPath = path.join(tempDir, "nonexistent.txt");

      await expect(
        verifyChecksum(nonExistentPath, "sha256:abc123")
      ).rejects.toThrow("Failed to read file for checksum");
    });
  });

  describe("downloadTemplate", () => {
    let tempDir: string;
    let targetDir: string;

    beforeEach(async () => {
      tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "template-test-"));
      targetDir = path.join(tempDir, "target");
      await fs.ensureDir(targetDir);
    });

    afterEach(async () => {
      await fs.remove(tempDir);
    });

    test("throws error when template not found in manifest", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => mockManifest,
      } as any);

      await expect(
        downloadTemplate("nonexistent", "0.8.0", targetDir)
      ).rejects.toThrow('Template "nonexistent" not found');
    });

    test("throws error for download failures", async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => mockManifest,
        } as any)
        .mockResolvedValueOnce({
          ok: false,
          status: 404,
          statusText: "Not Found",
        } as any);

      await expect(
        downloadTemplate("basic", "0.8.0", targetDir)
      ).rejects.toThrow("Failed to download template");
    });

    test("lists available templates when template not found", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => mockManifest,
      } as any);

      try {
        await downloadTemplate("nonexistent", "0.8.0", targetDir);
      } catch (error) {
        expect((error as Error).message).toContain("Available templates:");
        expect((error as Error).message).toContain("baseboards");
        expect((error as Error).message).toContain("basic");
      }
    });
  });

  describe("Integration scenarios", () => {
    test("handles empty response body", async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => mockManifest,
        } as any)
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          body: null,
        } as any);

      const tempDir = await fs.mkdtemp(
        path.join(os.tmpdir(), "template-test-")
      );
      const targetDir = path.join(tempDir, "target");

      try {
        await expect(
          downloadTemplate("basic", "0.8.0", targetDir)
        ).rejects.toThrow("Response body is empty");
      } finally {
        await fs.remove(tempDir);
      }
    });

    test("validates manifest schema", async () => {
      const invalidManifest = {
        version: "0.8.0",
        templates: "not-an-array", // Invalid type
      };

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => invalidManifest,
      } as any);

      await expect(fetchTemplateManifest("0.8.0")).rejects.toThrow(
        "Invalid manifest structure"
      );
    });

    test("removes 'v' prefix from tag_name when fetching latest", async () => {
      const latestRelease = {
        tag_name: "v0.10.0",
      };

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => latestRelease,
        } as any)
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({ ...mockManifest, version: "0.10.0" }),
        } as any);

      await fetchTemplateManifest("latest");

      expect(mockFetch).toHaveBeenNthCalledWith(
        2,
        "https://github.com/weirdfingers/boards/releases/download/v0.10.0/template-manifest.json",
        expect.any(Object)
      );
    });
  });

  describe("Cache Management", () => {
    describe("getCacheDir", () => {
      test("returns cache directory path in home directory", () => {
        const cacheDir = getCacheDir();

        expect(cacheDir).toContain(".baseboards");
        expect(cacheDir).toContain("templates");
        expect(cacheDir).toContain(os.homedir());
      });
    });

    describe("clearCache", () => {
      test("clears all files from cache directory", async () => {
        const cacheDir = getCacheDir();
        // Create test files
        const file1 = path.join(cacheDir, "template-basic-v0.8.0.tar.gz");
        const file2 = path.join(cacheDir, "manifest-v0.8.0.json");
        await fs.ensureDir(cacheDir);
        await fs.writeFile(file1, "test data 1");
        await fs.writeFile(file2, "test data 2");

        await clearCache();

        // Verify files are deleted
        expect(await fs.pathExists(file1)).toBe(false);
        expect(await fs.pathExists(file2)).toBe(false);

        // Verify directory still exists
        expect(await fs.pathExists(cacheDir)).toBe(true);
      });

      test("handles empty cache directory", async () => {
        await expect(clearCache()).resolves.not.toThrow();
      });
    });

    describe("clearTemplateCache", () => {
      test("clears specific template from cache", async () => {
        const cacheDir = getCacheDir();
        const file1 = path.join(cacheDir, "template-basic-v0.8.0.tar.gz");
        const file2 = path.join(cacheDir, "template-baseboards-v0.8.0.tar.gz");
        await fs.ensureDir(cacheDir);
        await fs.writeFile(file1, "test data 1");
        await fs.writeFile(file2, "test data 2");

        await clearTemplateCache("basic", "0.8.0");

        // Verify only the specified template is deleted
        expect(await fs.pathExists(file1)).toBe(false);
        expect(await fs.pathExists(file2)).toBe(true);
      });

      test("handles clearing non-existent template", async () => {
        await expect(
          clearTemplateCache("nonexistent", "0.8.0")
        ).resolves.not.toThrow();
      });
    });

    describe("getCacheSize", () => {
      test("calculates total cache size", async () => {
        const cacheDir = getCacheDir();
        const file1 = path.join(cacheDir, "template-basic-v0.8.0.tar.gz");
        const file2 = path.join(cacheDir, "manifest-v0.8.0.json");
        const content1 = "x".repeat(1000);
        const content2 = "y".repeat(500);
        await fs.ensureDir(cacheDir);
        await fs.writeFile(file1, content1);
        await fs.writeFile(file2, content2);

        const size = await getCacheSize();

        expect(size).toBe(1500);
      });

      test("returns 0 for empty cache", async () => {
        const size = await getCacheSize();

        expect(size).toBe(0);
      });
    });

    describe("Manifest caching", () => {
      test("caches manifest after fetching", async () => {
        mockFetch.mockResolvedValue({
          ok: true,
          status: 200,
          json: async () => mockManifest,
        } as any);

        await fetchTemplateManifest("0.8.0");

        const cacheDir = getCacheDir();
        const cachedManifestPath = path.join(cacheDir, "manifest-v0.8.0.json");
        expect(await fs.pathExists(cachedManifestPath)).toBe(true);

        const cachedData = await fs.readJson(cachedManifestPath);
        expect(cachedData).toEqual(mockManifest);
      });

      test("uses cached manifest on subsequent calls", async () => {
        // Pre-populate cache
        const cacheDir = getCacheDir();
        const cachedManifestPath = path.join(cacheDir, "manifest-v0.8.0.json");
        await fs.ensureDir(cacheDir);
        await fs.writeJson(cachedManifestPath, mockManifest);

        const result = await fetchTemplateManifest("0.8.0");

        // Fetch should not be called if cache is used
        expect(mockFetch).not.toHaveBeenCalled();
        expect(result).toEqual(mockManifest);
      });

      test("re-fetches manifest if cached version is corrupted", async () => {
        // Pre-populate cache with invalid data
        const cacheDir = getCacheDir();
        const cachedManifestPath = path.join(cacheDir, "manifest-v0.8.0.json");
        await fs.ensureDir(cacheDir);
        await fs.writeFile(cachedManifestPath, "invalid json");

        mockFetch.mockResolvedValue({
          ok: true,
          status: 200,
          json: async () => mockManifest,
        } as any);

        const result = await fetchTemplateManifest("0.8.0");

        // Should have re-fetched from network
        expect(mockFetch).toHaveBeenCalled();
        expect(result).toEqual(mockManifest);
      });
    });
  });
});

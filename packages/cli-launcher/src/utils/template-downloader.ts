/**
 * Template Downloader Utility
 *
 * Provides utilities for downloading Boards templates from GitHub Releases,
 * validating checksums, and extracting them to target directories.
 *
 * This module enables the CLI to fetch templates on-demand instead of bundling
 * them in the npm package.
 */

import fs from "fs-extra";
import path from "path";
import { createHash } from "crypto";
import { Readable } from "stream";
import { pipeline } from "stream/promises";
import { extract } from "tar";
import { tmpdir } from "os";

/**
 * Information about a single template
 */
export interface TemplateInfo {
  /** Template name (e.g., "baseboards", "basic") */
  name: string;
  /** Human-readable description */
  description: string;
  /** Filename of the tarball (e.g., "template-baseboards-v0.8.0.tar.gz") */
  file: string;
  /** File size in bytes */
  size: number;
  /** SHA-256 checksum with "sha256:" prefix */
  checksum: string;
  /** Frameworks used (e.g., ["next.js"]) */
  frameworks: string[];
  /** Features included (e.g., ["auth", "generators"]) */
  features: string[];
}

/**
 * Template manifest containing version and available templates
 */
export interface TemplateManifest {
  /** Version string (e.g., "0.8.0") */
  version: string;
  /** Array of available templates */
  templates: TemplateInfo[];
}

/**
 * GitHub Release base URL
 */
const GITHUB_RELEASE_BASE =
  "https://github.com/weirdfingers/boards/releases/download";

/**
 * Fetch template manifest from GitHub Release
 *
 * @param version - Version string (e.g., "0.8.0") or "latest" for the latest release
 * @returns Template manifest containing available templates
 * @throws Error if version not found or network error occurs
 *
 * @example
 * ```typescript
 * const manifest = await fetchTemplateManifest("0.8.0");
 * console.log(manifest.templates); // List of available templates
 * ```
 */
export async function fetchTemplateManifest(
  version: string
): Promise<TemplateManifest> {
  let manifestUrl: string;

  if (version === "latest") {
    // Fetch latest release version from GitHub API
    const apiUrl = "https://api.github.com/repos/weirdfingers/boards/releases/latest";

    try {
      const response = await fetch(apiUrl, {
        headers: {
          "User-Agent": "@weirdfingers/baseboards-cli",
          Accept: "application/vnd.github.v3+json",
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error(
            "No releases found. Please specify a version explicitly."
          );
        }
        throw new Error(
          `Failed to fetch latest release: ${response.status} ${response.statusText}`
        );
      }

      const release = (await response.json()) as { tag_name: string };
      version = release.tag_name.replace(/^v/, ""); // Remove 'v' prefix
      manifestUrl = `${GITHUB_RELEASE_BASE}/v${version}/template-manifest.json`;
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Failed to fetch latest release: ${error.message}`);
      }
      throw error;
    }
  } else {
    manifestUrl = `${GITHUB_RELEASE_BASE}/v${version}/template-manifest.json`;
  }

  // Retry configuration
  const maxRetries = 3;
  const retryDelay = 1000; // 1 second

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(manifestUrl, {
        headers: {
          "User-Agent": "@weirdfingers/baseboards-cli",
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error(
            `Version ${version} not found. Please check that this version exists in GitHub Releases.`
          );
        }
        throw new Error(
          `Failed to fetch manifest: ${response.status} ${response.statusText}`
        );
      }

      const manifest = (await response.json()) as TemplateManifest;

      // Validate manifest structure
      if (!manifest.version || !Array.isArray(manifest.templates)) {
        throw new Error("Invalid manifest structure");
      }

      return manifest;
    } catch (error) {
      if (attempt === maxRetries) {
        if (error instanceof Error) {
          throw new Error(`Failed to fetch template manifest: ${error.message}`);
        }
        throw error;
      }

      // Wait before retrying
      await new Promise((resolve) => setTimeout(resolve, retryDelay));
    }
  }

  // Should never reach here, but TypeScript requires a return
  throw new Error("Failed to fetch template manifest after all retries");
}

/**
 * Verify file checksum matches expected value
 *
 * @param filePath - Path to file to verify
 * @param expectedChecksum - Expected checksum in format "sha256:abcd1234..."
 * @returns true if checksum matches
 * @throws Error if checksum mismatch or invalid format
 *
 * @example
 * ```typescript
 * await verifyChecksum("/tmp/file.tar.gz", "sha256:abc123...");
 * ```
 */
export async function verifyChecksum(
  filePath: string,
  expectedChecksum: string
): Promise<boolean> {
  // Validate checksum format
  if (!expectedChecksum.startsWith("sha256:")) {
    throw new Error(
      `Invalid checksum format: must start with "sha256:" (got: ${expectedChecksum})`
    );
  }

  const expectedHash = expectedChecksum.replace("sha256:", "");

  // Calculate file hash
  const hash = createHash("sha256");
  const fileStream = fs.createReadStream(filePath);

  return new Promise((resolve, reject) => {
    fileStream.on("data", (chunk) => {
      hash.update(chunk);
    });

    fileStream.on("end", () => {
      const actualHash = hash.digest("hex");

      if (actualHash !== expectedHash) {
        reject(
          new Error(
            `Checksum mismatch for ${path.basename(filePath)}:\n` +
              `  Expected: sha256:${expectedHash}\n` +
              `  Actual:   sha256:${actualHash}\n` +
              `The file may be corrupted or tampered with.`
          )
        );
      } else {
        resolve(true);
      }
    });

    fileStream.on("error", (error) => {
      reject(new Error(`Failed to read file for checksum: ${error.message}`));
    });
  });
}

/**
 * Download and extract template to target directory
 *
 * @param name - Template name (e.g., "baseboards", "basic")
 * @param version - Version string (e.g., "0.8.0") or "latest"
 * @param targetDir - Directory to extract template into
 * @throws Error if template not found, network error, or checksum mismatch
 *
 * @example
 * ```typescript
 * await downloadTemplate("basic", "0.8.0", "/tmp/my-project");
 * // Files will be extracted to /tmp/my-project/
 * ```
 */
export async function downloadTemplate(
  name: string,
  version: string,
  targetDir: string
): Promise<void> {
  let tempFilePath: string | null = null;

  try {
    // Fetch manifest to get template metadata
    const manifest = await fetchTemplateManifest(version);

    // Find template in manifest
    const template = manifest.templates.find((t) => t.name === name);
    if (!template) {
      const available = manifest.templates.map((t) => t.name).join(", ");
      throw new Error(
        `Template "${name}" not found in version ${manifest.version}.\n` +
          `Available templates: ${available}`
      );
    }

    // Construct download URL
    const downloadUrl = `${GITHUB_RELEASE_BASE}/v${manifest.version}/${template.file}`;

    // Create temporary file
    const tempDir = tmpdir();
    tempFilePath = path.join(tempDir, template.file);

    // Download tarball
    const response = await fetch(downloadUrl, {
      headers: {
        "User-Agent": "@weirdfingers/baseboards-cli",
      },
    });

    if (!response.ok) {
      throw new Error(
        `Failed to download template: ${response.status} ${response.statusText}`
      );
    }

    if (!response.body) {
      throw new Error("Response body is empty");
    }

    // Save to temporary file
    const fileStream = fs.createWriteStream(tempFilePath);
    await pipeline(Readable.fromWeb(response.body as any), fileStream);

    // Verify checksum
    await verifyChecksum(tempFilePath, template.checksum);

    // Ensure target directory exists
    await fs.ensureDir(targetDir);

    // Extract tarball
    // The tarball contains a directory (e.g., "baseboards/"), so we need to:
    // 1. Extract to a temporary location
    // 2. Move the contents to the target directory
    const extractTempDir = path.join(tempDir, `extract-${name}-${Date.now()}`);
    await fs.ensureDir(extractTempDir);

    await extract({
      file: tempFilePath,
      cwd: extractTempDir,
      strip: 1, // Strip the top-level directory
    });

    // Move extracted files to target directory
    const files = await fs.readdir(extractTempDir);
    for (const file of files) {
      const srcPath = path.join(extractTempDir, file);
      const destPath = path.join(targetDir, file);
      await fs.move(srcPath, destPath, { overwrite: true });
    }

    // Clean up extraction directory
    await fs.remove(extractTempDir);
  } catch (error) {
    // Ensure we clean up on error
    if (tempFilePath && (await fs.pathExists(tempFilePath))) {
      await fs.remove(tempFilePath);
    }

    throw error;
  } finally {
    // Clean up temporary file on success
    if (tempFilePath && (await fs.pathExists(tempFilePath))) {
      await fs.remove(tempFilePath);
    }
  }
}

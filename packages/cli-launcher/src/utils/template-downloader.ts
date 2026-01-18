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
import { tmpdir, homedir } from "os";
import ora, { Ora } from "ora";

/**
 * Base error class for template download errors
 */
export class TemplateDownloadError extends Error {
  constructor(
    message: string,
    public cause?: string,
    public suggestion?: string
  ) {
    super(message);
    this.name = "TemplateDownloadError";
    // Maintain proper stack trace for where error was thrown (V8 only)
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, this.constructor);
    }
  }
}

/**
 * Error thrown when template or version is not found
 */
export class TemplateNotFoundError extends TemplateDownloadError {
  constructor(message: string, cause?: string, suggestion?: string) {
    super(message, cause, suggestion);
    this.name = "TemplateNotFoundError";
  }
}

/**
 * Error thrown when network operations fail
 */
export class NetworkError extends TemplateDownloadError {
  constructor(message: string, cause?: string, suggestion?: string) {
    super(message, cause, suggestion);
    this.name = "NetworkError";
  }
}

/**
 * Error thrown when checksum verification fails
 */
export class ChecksumError extends TemplateDownloadError {
  constructor(message: string, cause?: string, suggestion?: string) {
    super(message, cause, suggestion);
    this.name = "ChecksumError";
  }
}

/**
 * Error thrown when disk space issues occur
 */
export class DiskSpaceError extends TemplateDownloadError {
  constructor(message: string, cause?: string, suggestion?: string) {
    super(message, cause, suggestion);
    this.name = "DiskSpaceError";
  }
}

/**
 * Error thrown when permission issues occur
 */
export class PermissionError extends TemplateDownloadError {
  constructor(message: string, cause?: string, suggestion?: string) {
    super(message, cause, suggestion);
    this.name = "PermissionError";
  }
}

/**
 * Error thrown when GitHub API rate limit is exceeded
 */
export class RateLimitError extends TemplateDownloadError {
  constructor(message: string, cause?: string, suggestion?: string) {
    super(message, cause, suggestion);
    this.name = "RateLimitError";
  }
}

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
 * Format bytes to human-readable string
 *
 * @param bytes - Number of bytes
 * @returns Formatted string (e.g., "1.2 MB", "45 KB")
 *
 * @example
 * ```typescript
 * formatBytes(1024); // "1.0 KB"
 * formatBytes(1024 * 1024); // "1.0 MB"
 * ```
 */
function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/**
 * Display error message with consistent formatting
 *
 * @param error - Error to display
 *
 * @example
 * ```typescript
 * try {
 *   await downloadTemplate("basic", "0.8.0", "./my-project");
 * } catch (error) {
 *   displayError(error);
 * }
 * ```
 */
export function displayError(error: TemplateDownloadError | Error): void {
  console.error(`\n❌ Error: ${error.message}`);

  if (error instanceof TemplateDownloadError) {
    if (error.cause) {
      console.error(`Cause: ${error.cause}`);
    }

    if (error.suggestion) {
      console.error(`\nSuggestion: ${error.suggestion}`);
    }
  }

  console.error(); // Empty line
}

/**
 * Check if an error is a transient network error that should be retried
 *
 * @param error - Error to check
 * @returns true if error is transient
 */
function isTransientError(error: any): boolean {
  const transientCodes = [
    "ETIMEDOUT",
    "ECONNRESET",
    "ECONNREFUSED",
    "EPIPE",
    "ENOTFOUND",
    "ENETUNREACH",
    "EAI_AGAIN",
  ];

  if (error.code && transientCodes.includes(error.code)) {
    return true;
  }

  // Check for fetch-specific errors
  if (error.name === "AbortError" || error.name === "FetchError") {
    return true;
  }

  return false;
}

/**
 * Handle fetch errors and convert to user-friendly errors
 *
 * @param error - Error from fetch operation
 * @param context - Context string for error message (e.g., "template manifest")
 * @throws Appropriate TemplateDownloadError subclass
 */
function handleFetchError(error: any, context: string): never {
  // Network errors
  if (error.code === "ENOTFOUND") {
    throw new NetworkError(
      `Failed to download ${context}`,
      "DNS resolution failed - cannot reach github.com",
      "Check your internet connection and DNS settings. Verify you can access https://github.com"
    );
  }

  if (error.code === "ECONNREFUSED") {
    throw new NetworkError(
      `Failed to download ${context}`,
      "Connection refused",
      "Check your internet connection and firewall settings"
    );
  }

  if (error.code === "ETIMEDOUT") {
    throw new NetworkError(
      `Failed to download ${context}`,
      "Connection timed out",
      "Check your internet connection. Try again later or check if you're behind a proxy"
    );
  }

  if (error.code === "ENETUNREACH") {
    throw new NetworkError(
      `Failed to download ${context}`,
      "Network unreachable",
      "Check your internet connection and network settings"
    );
  }

  if (
    error.code &&
    (error.code.startsWith("CERT_") || error.code === "UNABLE_TO_VERIFY_LEAF_SIGNATURE")
  ) {
    throw new NetworkError(
      `Failed to download ${context}`,
      "SSL/TLS certificate verification failed",
      "Check your system date/time settings. If you're behind a corporate proxy, you may need to configure SSL certificates"
    );
  }

  // Generic network error
  if (isTransientError(error)) {
    throw new NetworkError(
      `Failed to download ${context}`,
      error.message || "Network error occurred",
      "Check your internet connection and try again"
    );
  }

  // Re-throw if not a network error
  throw error;
}

/**
 * Get the cache directory path for templates
 *
 * @returns Path to cache directory (~/.baseboards/templates/)
 *
 * @example
 * ```typescript
 * const cacheDir = getCacheDir();
 * console.log(cacheDir); // ~/.baseboards/templates/
 * ```
 */
export function getCacheDir(): string {
  return path.join(homedir(), ".baseboards", "templates");
}

/**
 * Ensure cache directory exists
 * @throws PermissionError if directory cannot be created
 */
async function ensureCacheDir(): Promise<void> {
  const cacheDir = getCacheDir();

  try {
    await fs.ensureDir(cacheDir);
  } catch (error: any) {
    if (error.code === "EACCES" || error.code === "EPERM") {
      throw new PermissionError(
        "Cannot write to cache directory",
        `Permission denied: ${cacheDir}`,
        "Check file permissions or try running with appropriate permissions"
      );
    }
    throw error;
  }
}

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
  let actualVersion = version;

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
        // Handle rate limiting
        if (response.status === 403 || response.status === 429) {
          const resetTime = response.headers.get("x-ratelimit-reset");
          let suggestion = "Please try again later";

          if (resetTime) {
            const resetDate = new Date(parseInt(resetTime) * 1000);
            const minutesUntilReset = Math.ceil(
              (resetDate.getTime() - Date.now()) / 60000
            );
            suggestion = `Please try again in ${minutesUntilReset} minute${minutesUntilReset !== 1 ? "s" : ""}`;
          }

          throw new RateLimitError(
            "GitHub API rate limit exceeded",
            "Too many requests to GitHub API",
            suggestion
          );
        }

        if (response.status === 404) {
          throw new TemplateNotFoundError(
            "No releases found",
            "No releases exist for this project yet",
            "Please specify a version explicitly or wait for the first release"
          );
        }

        throw new NetworkError(
          `Failed to fetch latest release`,
          `HTTP ${response.status}: ${response.statusText}`,
          "Check your internet connection and try again"
        );
      }

      const release = (await response.json()) as { tag_name: string };
      actualVersion = release.tag_name.replace(/^v/, ""); // Remove 'v' prefix
      manifestUrl = `${GITHUB_RELEASE_BASE}/v${actualVersion}/template-manifest.json`;
    } catch (error) {
      // Re-throw our custom errors
      if (
        error instanceof TemplateDownloadError ||
        error instanceof NetworkError ||
        error instanceof RateLimitError
      ) {
        throw error;
      }

      // Handle network errors
      handleFetchError(error, "latest release information");
    }
  } else {
    actualVersion = version;
    manifestUrl = `${GITHUB_RELEASE_BASE}/v${version}/template-manifest.json`;
  }

  // Check cache first
  await ensureCacheDir();
  const cacheDir = getCacheDir();
  const cachedManifestPath = path.join(cacheDir, `manifest-v${actualVersion}.json`);

  if (await fs.pathExists(cachedManifestPath)) {
    try {
      const cachedManifest = await fs.readJson(cachedManifestPath);
      // Validate cached manifest structure
      if (cachedManifest.version && Array.isArray(cachedManifest.templates)) {
        return cachedManifest as TemplateManifest;
      }
    } catch (error) {
      // If cache is corrupted, delete it and continue to download
      await fs.remove(cachedManifestPath);
    }
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
        // Handle rate limiting
        if (response.status === 403 || response.status === 429) {
          const resetTime = response.headers.get("x-ratelimit-reset");
          let suggestion = "Please try again later";

          if (resetTime) {
            const resetDate = new Date(parseInt(resetTime) * 1000);
            const minutesUntilReset = Math.ceil(
              (resetDate.getTime() - Date.now()) / 60000
            );
            suggestion = `Please try again in ${minutesUntilReset} minute${minutesUntilReset !== 1 ? "s" : ""}`;
          }

          throw new RateLimitError(
            "GitHub API rate limit exceeded",
            "Too many requests to GitHub API",
            suggestion
          );
        }

        if (response.status === 404) {
          throw new TemplateNotFoundError(
            `Template manifest not found for version ${actualVersion}`,
            `Version ${actualVersion} may not be released yet`,
            `Check available versions at: https://github.com/weirdfingers/boards/releases`
          );
        }

        throw new NetworkError(
          `Failed to fetch template manifest`,
          `HTTP ${response.status}: ${response.statusText}`,
          "Check your internet connection and try again"
        );
      }

      const manifest = (await response.json()) as TemplateManifest;

      // Validate manifest structure
      if (!manifest.version || !Array.isArray(manifest.templates)) {
        throw new Error("Invalid manifest structure");
      }

      // Cache manifest for future use
      try {
        await fs.writeJson(cachedManifestPath, manifest, { spaces: 2 });
      } catch (error: any) {
        // Non-critical error - check if it's a permission issue
        if (error.code === "EACCES" || error.code === "EPERM") {
          // Continue without caching
        } else if (error.code === "ENOSPC") {
          // Continue without caching - low disk space
        }
        // Otherwise continue without throwing
      }

      return manifest;
    } catch (error) {
      // Don't retry on non-transient errors
      if (
        error instanceof TemplateNotFoundError ||
        error instanceof RateLimitError
      ) {
        throw error;
      }

      // On the last attempt, throw the error
      if (attempt === maxRetries) {
        if (error instanceof TemplateDownloadError) {
          throw error;
        }

        // Handle network errors
        handleFetchError(error, "template manifest");
      }

      // Only retry on transient errors
      if (isTransientError(error)) {
        // Wait before retrying with exponential backoff
        await new Promise((resolve) =>
          setTimeout(resolve, retryDelay * attempt)
        );
      } else {
        // Non-transient error, throw immediately
        if (error instanceof Error) {
          throw new NetworkError(
            `Failed to fetch template manifest`,
            error.message,
            "Check your internet connection and try again"
          );
        }
        throw error;
      }
    }
  }

  // Should never reach here, but TypeScript requires a return
  throw new NetworkError(
    "Failed to fetch template manifest after all retries",
    "Network error occurred",
    "Check your internet connection and try again"
  );
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
    throw new ChecksumError(
      "Invalid checksum format",
      `Checksum must start with "sha256:" (got: ${expectedChecksum})`,
      "This is likely a bug in the template manifest. Please report it at: https://github.com/weirdfingers/boards/issues"
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
          new ChecksumError(
            "Template verification failed",
            "Downloaded file checksum does not match expected value",
            "The download may have been corrupted. It will be automatically retried."
          )
        );
      } else {
        resolve(true);
      }
    });

    fileStream.on("error", (error) => {
      reject(
        new Error(`Failed to read file for checksum: ${error.message}`)
      );
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
  let extractTempDir: string | null = null;
  const isInteractive = process.stdout.isTTY;
  let spinner: Ora | null = null;

  try {
    // Fetch manifest to get template metadata
    const manifest = await fetchTemplateManifest(version);

    // Find template in manifest
    const template = manifest.templates.find((t) => t.name === name);
    if (!template) {
      const available = manifest.templates.map((t) => t.name).join(", ");
      throw new TemplateNotFoundError(
        `Template "${name}" not found in version ${manifest.version}`,
        `Template "${name}" does not exist in this version`,
        `Available templates: ${available}`
      );
    }

    // Check cache first
    await ensureCacheDir();
    const cacheDir = getCacheDir();
    const cachedFilePath = path.join(
      cacheDir,
      `template-${name}-v${manifest.version}.tar.gz`
    );

    let sourceFilePath: string;
    let cacheHit = false;

    if (await fs.pathExists(cachedFilePath)) {
      // Verify cached file checksum
      try {
        await verifyChecksum(cachedFilePath, template.checksum);
        sourceFilePath = cachedFilePath;
        cacheHit = true;

        // Show cache hit message
        if (isInteractive) {
          console.log(`Using cached template ${name}...`);
        } else {
          console.log(`Using cached template ${name}...`);
        }
      } catch (error) {
        // Cached file is corrupted, delete it and re-download
        await fs.remove(cachedFilePath);

        // Start download progress
        if (isInteractive) {
          console.log(`\nDownloading template ${name}...`);
          spinner = ora().start();
        } else {
          console.log(`Downloading template ${name}...`);
        }

        sourceFilePath = await downloadAndCache(
          manifest.version,
          template,
          cachedFilePath,
          spinner
        );
      }
    } else {
      // Download and cache
      if (isInteractive) {
        console.log(`\nDownloading template ${name}...`);
        spinner = ora().start();
      } else {
        console.log(`Downloading template ${name}...`);
      }

      sourceFilePath = await downloadAndCache(
        manifest.version,
        template,
        cachedFilePath,
        spinner
      );
    }

    // Ensure target directory exists
    try {
      await fs.ensureDir(targetDir);
    } catch (error: any) {
      if (error.code === "EACCES" || error.code === "EPERM") {
        throw new PermissionError(
          "Cannot create target directory",
          `Permission denied: ${targetDir}`,
          "Check file permissions or choose a different directory"
        );
      }
      if (error.code === "ENOSPC") {
        throw new DiskSpaceError(
          "Cannot create target directory",
          "Not enough disk space",
          `Free up disk space and try again. Required: ~${formatBytes(template.size)}`
        );
      }
      throw error;
    }

    // Show extraction stage
    if (spinner && isInteractive) {
      spinner.text = "Extracting template...";
    } else if (!cacheHit) {
      console.log("Extracting template...");
    }

    // Extract tarball
    // The tarball contains a directory (e.g., "baseboards/"), so we need to:
    // 1. Extract to a temporary location
    // 2. Move the contents to the target directory
    const tempDir = tmpdir();
    extractTempDir = path.join(tempDir, `extract-${name}-${Date.now()}`);

    try {
      await fs.ensureDir(extractTempDir);
    } catch (error: any) {
      if (error.code === "ENOSPC") {
        throw new DiskSpaceError(
          "Cannot extract template",
          "Not enough disk space",
          `Free up disk space and try again. Required: ~${formatBytes(template.size)}`
        );
      }
      throw error;
    }

    try {
      await extract({
        file: sourceFilePath,
        cwd: extractTempDir,
        strip: 1, // Strip the top-level directory
      });
    } catch (error: any) {
      throw new Error(
        `Failed to extract template: ${error.message || "Unknown error"}`
      );
    }

    // Move extracted files to target directory
    try {
      const files = await fs.readdir(extractTempDir);
      for (const file of files) {
        const srcPath = path.join(extractTempDir, file);
        const destPath = path.join(targetDir, file);
        await fs.move(srcPath, destPath, { overwrite: true });
      }
    } catch (error: any) {
      if (error.code === "EACCES" || error.code === "EPERM") {
        throw new PermissionError(
          "Cannot write template files",
          `Permission denied: ${targetDir}`,
          "Check file permissions or choose a different directory"
        );
      }
      if (error.code === "ENOSPC") {
        throw new DiskSpaceError(
          "Cannot write template files",
          "Not enough disk space",
          `Free up disk space and try again. Required: ~${formatBytes(template.size)}`
        );
      }
      throw error;
    }

    // Clean up extraction directory
    await fs.remove(extractTempDir);
    extractTempDir = null;

    // Show success
    if (spinner && isInteractive) {
      spinner.succeed("Template ready");
    } else if (!cacheHit) {
      console.log("Template downloaded successfully");
    }
  } catch (error) {
    // Show failure
    if (spinner && isInteractive) {
      spinner.fail("Download failed");
    }

    // Clean up on error
    try {
      // Clean up partial downloads
      if (tempFilePath && (await fs.pathExists(tempFilePath))) {
        await fs.remove(tempFilePath);
      }

      // Clean up partial extraction
      if (extractTempDir && (await fs.pathExists(extractTempDir))) {
        await fs.remove(extractTempDir);
      }
    } catch (cleanupError) {
      // Ignore cleanup errors
    }

    throw error;
  }
}

/**
 * Download template tarball and cache it
 *
 * @param version - Version string
 * @param template - Template metadata
 * @param cachedFilePath - Path where to cache the file
 * @param spinner - Optional ora spinner for progress updates
 * @returns Path to the downloaded file
 */
async function downloadAndCache(
  version: string,
  template: TemplateInfo,
  cachedFilePath: string,
  spinner: Ora | null = null
): Promise<string> {
  // Construct download URL
  const downloadUrl = `${GITHUB_RELEASE_BASE}/v${version}/${template.file}`;

  // Retry configuration for checksum failures
  const maxChecksumRetries = 2;

  for (let checksumAttempt = 1; checksumAttempt <= maxChecksumRetries; checksumAttempt++) {
    // Create temporary file for atomic write
    const tempDir = tmpdir();
    const tempFilePath = path.join(tempDir, `${template.file}.tmp-${Date.now()}`);

    try {
      // Download with retry for transient network errors
      const maxDownloadRetries = 3;
      let downloadedBytes = 0;
      let response: Response | null = null;

      for (let downloadAttempt = 1; downloadAttempt <= maxDownloadRetries; downloadAttempt++) {
        try {
          response = await fetch(downloadUrl, {
            headers: {
              "User-Agent": "@weirdfingers/baseboards-cli",
            },
          });

          if (!response.ok) {
            // Handle rate limiting
            if (response.status === 403 || response.status === 429) {
              const resetTime = response.headers.get("x-ratelimit-reset");
              let suggestion = "Please try again later";

              if (resetTime) {
                const resetDate = new Date(parseInt(resetTime) * 1000);
                const minutesUntilReset = Math.ceil(
                  (resetDate.getTime() - Date.now()) / 60000
                );
                suggestion = `Please try again in ${minutesUntilReset} minute${minutesUntilReset !== 1 ? "s" : ""}`;
              }

              throw new RateLimitError(
                "GitHub API rate limit exceeded",
                "Too many requests to GitHub API",
                suggestion
              );
            }

            if (response.status === 404) {
              throw new TemplateNotFoundError(
                `Template file not found`,
                `File ${template.file} does not exist in version ${version}`,
                "This version may be incomplete. Try a different version."
              );
            }

            throw new NetworkError(
              `Failed to download template`,
              `HTTP ${response.status}: ${response.statusText}`,
              "Check your internet connection and try again"
            );
          }

          if (!response.body) {
            throw new NetworkError(
              "Failed to download template",
              "Response body is empty",
              "Try again later or check if you're behind a proxy"
            );
          }

          break; // Success, exit retry loop
        } catch (error) {
          // Re-throw non-transient errors
          if (error instanceof TemplateDownloadError) {
            throw error;
          }

          // On the last attempt, handle the error
          if (downloadAttempt === maxDownloadRetries) {
            handleFetchError(error, "template file");
          }

          // Retry on transient errors
          if (isTransientError(error)) {
            if (spinner) {
              spinner.text = `Network error, retrying (${downloadAttempt}/${maxDownloadRetries})...`;
            }
            await new Promise((resolve) =>
              setTimeout(resolve, 1000 * downloadAttempt)
            );
          } else {
            // Non-transient error, throw immediately
            handleFetchError(error, "template file");
          }
        }
      }

      // At this point, response should be valid
      if (!response || !response.body) {
        throw new NetworkError(
          "Failed to download template",
          "Could not establish connection",
          "Check your internet connection and try again"
        );
      }

      // Set up progress tracking
      const totalBytes = template.size;
      downloadedBytes = 0;
      let lastTime = Date.now();
      let lastLoaded = 0;

      // Create transform stream for progress tracking
      const reader = response.body.getReader();
      const fileStream = fs.createWriteStream(tempFilePath);

      // Read and track progress
      try {
        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            break;
          }

          // Write chunk to file
          fileStream.write(value);
          downloadedBytes += value.length;

          // Update progress
          if (spinner) {
            const now = Date.now();
            const timeDiff = (now - lastTime) / 1000; // seconds
            const loadedDiff = downloadedBytes - lastLoaded;

            // Calculate speed (only update every 100ms to avoid too frequent updates)
            if (timeDiff >= 0.1) {
              const speed = loadedDiff / timeDiff; // bytes per second
              const speedStr = formatBytes(speed) + "/s";
              const percent = Math.round((downloadedBytes / totalBytes) * 100);
              const currentSize = formatBytes(downloadedBytes);
              const totalSize = formatBytes(totalBytes);

              spinner.text = `${percent}% (${currentSize} / ${totalSize}) [${speedStr}]`;

              lastTime = now;
              lastLoaded = downloadedBytes;
            }
          }
        }
      } catch (error: any) {
        if (error.code === "ENOSPC") {
          throw new DiskSpaceError(
            "Failed to save template",
            "Not enough disk space",
            `Free up disk space and try again. Required: ~${formatBytes(template.size)}`
          );
        }
        throw error;
      }

      // Close the file stream
      await new Promise<void>((resolve, reject) => {
        fileStream.end(() => resolve());
        fileStream.on("error", reject);
      });

      // Verify checksum
      try {
        if (spinner) {
          spinner.text = "Verifying download...";
        }
        await verifyChecksum(tempFilePath, template.checksum);

        // Success! Move to cache atomically
        try {
          await fs.move(tempFilePath, cachedFilePath, { overwrite: true });
        } catch (error: any) {
          if (error.code === "ENOSPC") {
            throw new DiskSpaceError(
              "Failed to save template to cache",
              "Not enough disk space",
              `Free up disk space and try again. Required: ~${formatBytes(template.size)}`
            );
          }
          if (error.code === "EACCES" || error.code === "EPERM") {
            throw new PermissionError(
              "Cannot write to cache directory",
              `Permission denied: ${cachedFilePath}`,
              "Check file permissions or try running with appropriate permissions"
            );
          }
          throw error;
        }

        return cachedFilePath;
      } catch (error) {
        // Checksum verification failed
        if (error instanceof ChecksumError) {
          if (checksumAttempt < maxChecksumRetries) {
            // Clean up and retry
            if (await fs.pathExists(tempFilePath)) {
              await fs.remove(tempFilePath);
            }

            if (spinner) {
              spinner.text = `Checksum verification failed. Retrying download (attempt ${checksumAttempt + 1}/${maxChecksumRetries})...`;
            } else {
              console.log(
                `Checksum verification failed. Retrying download (attempt ${checksumAttempt + 1}/${maxChecksumRetries})...`
              );
            }

            // Wait a bit before retrying
            await new Promise((resolve) => setTimeout(resolve, 1000));
            continue; // Retry the entire download
          } else {
            // Final attempt failed
            throw new ChecksumError(
              "Template verification failed",
              "Downloaded file is corrupted after multiple attempts",
              "Please try again later. If the problem persists, report it at: https://github.com/weirdfingers/boards/issues"
            );
          }
        }

        throw error;
      }
    } catch (error) {
      // Clean up temporary file on error
      try {
        const tempFilePath = path.join(tempDir, `${template.file}.tmp-${Date.now()}`);
        if (await fs.pathExists(tempFilePath)) {
          await fs.remove(tempFilePath);
        }
      } catch (cleanupError) {
        // Ignore cleanup errors
      }

      throw error;
    }
  }

  // Should never reach here
  throw new ChecksumError(
    "Template verification failed",
    "Downloaded file is corrupted after multiple attempts",
    "Please try again later. If the problem persists, report it at: https://github.com/weirdfingers/boards/issues"
  );
}

/**
 * Clear entire template cache
 *
 * Deletes all cached templates and manifests from ~/.baseboards/templates/
 * The cache directory itself is preserved.
 *
 * @throws Error if cache cannot be cleared (e.g., permission denied)
 *
 * @example
 * ```typescript
 * await clearCache();
 * console.log("Cache cleared successfully");
 * ```
 */
export async function clearCache(): Promise<void> {
  const cacheDir = getCacheDir();

  // Ensure cache directory exists
  await ensureCacheDir();

  try {
    // Read all files in cache directory
    const files = await fs.readdir(cacheDir);

    // Delete each file
    for (const file of files) {
      const filePath = path.join(cacheDir, file);
      const stat = await fs.stat(filePath);

      if (stat.isFile()) {
        await fs.remove(filePath);
      }
    }
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(`Failed to clear cache: ${error.message}`);
    }
    throw error;
  }
}

/**
 * Clear a specific template from cache
 *
 * Deletes a specific cached template tarball. Useful for forcing a re-download.
 *
 * @param name - Template name (e.g., "baseboards", "basic")
 * @param version - Version string (e.g., "0.8.0")
 *
 * @example
 * ```typescript
 * await clearTemplateCache("basic", "0.8.0");
 * console.log("Template cache cleared");
 * ```
 */
export async function clearTemplateCache(
  name: string,
  version: string
): Promise<void> {
  const cacheDir = getCacheDir();
  const cachedFilePath = path.join(cacheDir, `template-${name}-v${version}.tar.gz`);

  try {
    if (await fs.pathExists(cachedFilePath)) {
      await fs.remove(cachedFilePath);
    }
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(`Failed to clear template cache: ${error.message}`);
    }
    throw error;
  }
}

/**
 * Get total size of template cache
 *
 * Calculates the total size of all cached files in bytes.
 *
 * @returns Total cache size in bytes
 *
 * @example
 * ```typescript
 * const sizeBytes = await getCacheSize();
 * const sizeMB = (sizeBytes / (1024 * 1024)).toFixed(2);
 * console.log(`Cache size: ${sizeMB} MB`);
 * ```
 */
export async function getCacheSize(): Promise<number> {
  const cacheDir = getCacheDir();

  // Ensure cache directory exists
  await ensureCacheDir();

  try {
    const files = await fs.readdir(cacheDir);
    let totalSize = 0;

    for (const file of files) {
      const filePath = path.join(cacheDir, file);
      const stat = await fs.stat(filePath);

      if (stat.isFile()) {
        totalSize += stat.size;
      }
    }

    return totalSize;
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(`Failed to calculate cache size: ${error.message}`);
    }
    throw error;
  }
}

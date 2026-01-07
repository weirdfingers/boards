/**
 * Utility functions for the Baseboards CLI
 */

import { execa } from "execa";
import fs from "fs-extra";
import path from "path";
import { fileURLToPath } from "url";
import which from "which";
import type { Prerequisites, ProjectContext } from "./types.js";
import chalk from "chalk";
import crypto from "crypto";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Get the templates directory (bundled with the CLI package)
 */
export function getTemplatesDir(): string {
  // In built package, templates are at root level next to dist/
  return path.join(__dirname, "../templates");
}

/**
 * Check system prerequisites
 */
export async function checkPrerequisites(): Promise<Prerequisites> {
  const prereqs: Prerequisites = {
    docker: { installed: false },
    node: { installed: true, satisfies: false },
    platform: { name: process.platform },
  };

  // Check Docker
  try {
    const dockerPath = await which("docker");
    prereqs.docker.installed = !!dockerPath;

    if (dockerPath) {
      const { stdout } = await execa("docker", ["--version"]);
      const match = stdout.match(/Docker version ([\d.]+)/);
      if (match) {
        prereqs.docker.version = match[1];
      }

      // Check Docker Compose
      try {
        const { stdout: composeStdout } = await execa("docker", [
          "compose",
          "version",
        ]);
        const composeMatch = composeStdout.match(/version v?([\d.]+)/);
        if (composeMatch) {
          prereqs.docker.composeVersion = composeMatch[1];
        }
      } catch (e) {
        // Compose not available
      }
    }
  } catch (e) {
    // Docker not installed
  }

  // Check Node version
  const nodeVersion = process.version.replace("v", "");
  prereqs.node.version = nodeVersion;

  const majorVersion = parseInt(nodeVersion.split(".")[0], 10);
  prereqs.node.satisfies = majorVersion >= 20;

  // Check if WSL
  if (process.platform === "linux") {
    try {
      const { stdout } = await execa("uname", ["-r"]);
      if (
        stdout.toLowerCase().includes("microsoft") ||
        stdout.toLowerCase().includes("wsl")
      ) {
        prereqs.platform.isWSL = true;
      }
    } catch (e) {
      // Not WSL or can't determine
    }
  }

  return prereqs;
}

/**
 * Assert that prerequisites are met, or exit with helpful error
 */
export async function assertPrerequisites(): Promise<void> {
  const prereqs = await checkPrerequisites();

  const errors: string[] = [];

  if (!prereqs.docker.installed) {
    errors.push(
      "🐳 Docker is not installed.",
      "   Install from: https://docs.docker.com/get-docker/"
    );
  } else if (!prereqs.docker.composeVersion) {
    errors.push(
      "🐳 Docker Compose (v2) is not available.",
      "   Update Docker to get Compose v2: https://docs.docker.com/compose/install/"
    );
  }

  if (!prereqs.node.satisfies) {
    errors.push(
      `⚠️  Node.js ${prereqs.node.version} is too old (need v20+).`,
      "   Install from: https://nodejs.org/"
    );
  }

  if (errors.length > 0) {
    console.error(chalk.red("\n❌ Prerequisites not met:\n"));
    errors.forEach((err) => console.error(chalk.yellow(err)));
    console.error("");
    process.exit(1);
  }
}

/**
 * Check if a directory is already scaffolded
 */
export function isScaffolded(dir: string): boolean {
  // Check for key files that indicate scaffolding
  const keyFiles = ["compose.yaml", "web/package.json", "api/pyproject.toml"];

  return keyFiles.every((file) => fs.existsSync(path.join(dir, file)));
}

/**
 * Find an available port
 */
export async function findAvailablePort(
  preferred: number,
  maxAttempts = 50
): Promise<number> {
  for (let port = preferred; port < preferred + maxAttempts; port++) {
    if (await isPortAvailable(port)) {
      return port;
    }
  }
  throw new Error(`No available port found near ${preferred}`);
}

/**
 * Check if a port is available
 */
async function isPortAvailable(port: number): Promise<boolean> {
  const { createServer } = await import("net");
  return new Promise((resolve) => {
    const server = createServer();
    server.once("error", () => resolve(false));
    server.once("listening", () => {
      server.close();
      resolve(true);
    });
    server.listen(port);
  });
}

/**
 * Generate a random secure string
 */
export function generateSecret(length = 32): string {
  return crypto.randomBytes(length).toString("hex");
}

/**
 * Generate a random password
 */
export function generatePassword(length = 24): string {
  const charset =
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#%^&*";
  let password = "";
  const bytes = crypto.randomBytes(length);

  for (let i = 0; i < length; i++) {
    password += charset[bytes[i] % charset.length];
  }

  return password;
}

/**
 * Parse custom ports string (e.g., "web=3300 api=8800")
 */
export function parsePortsOption(portsStr: string): Partial<{
  web: number;
  api: number;
  db: number;
  redis: number;
}> {
  const ports: any = {};
  const pairs = portsStr.split(/\s+/);

  for (const pair of pairs) {
    const [service, port] = pair.split("=");
    const portNum = parseInt(port, 10);
    if (
      service &&
      ["web", "api", "db", "redis"].includes(service) &&
      !isNaN(portNum)
    ) {
      ports[service] = portNum;
    }
  }

  return ports;
}

/**
 * Read package.json version
 */
export function getCliVersion(): string {
  const packagePath = path.join(__dirname, "../package.json");
  const packageJson = JSON.parse(fs.readFileSync(packagePath, "utf-8"));
  return packageJson.version;
}

/**
 * Detect missing provider API keys in .env file
 */
export function detectMissingProviderKeys(envPath: string): string[] {
  if (!fs.existsSync(envPath)) {
    return [];
  }

  const envContent = fs.readFileSync(envPath, "utf-8");
  const providerKeys = [
    "REPLICATE_API_TOKEN",
    "FAL_KEY",
    "KIE_API_KEY",
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
  ];

  const missingKeys: string[] = [];

  for (const key of providerKeys) {
    const regex = new RegExp(`^${key}=(.*)$`, "m");
    const match = envContent.match(regex);

    // Key is missing if not found or if value is empty
    if (!match || !match[1] || match[1].trim() === "") {
      missingKeys.push(key);
    }
  }

  // If all keys are missing, user hasn't configured any
  if (missingKeys.length === providerKeys.length) {
    return missingKeys;
  }

  return [];
}

/**
 * Wait for a condition with timeout
 */
export async function waitFor(
  condition: () => Promise<boolean>,
  options: {
    timeoutMs: number;
    intervalMs?: number;
    onProgress?: (elapsed: number) => void;
  }
): Promise<boolean> {
  const { timeoutMs, intervalMs = 1000, onProgress } = options;
  const startTime = Date.now();

  while (Date.now() - startTime < timeoutMs) {
    if (await condition()) {
      return true;
    }

    if (onProgress) {
      onProgress(Date.now() - startTime);
    }

    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }

  return false;
}

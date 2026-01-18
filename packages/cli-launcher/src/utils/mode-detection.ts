/**
 * Mode Detection Utility
 *
 * Detects whether a Baseboards project is running in default mode (frontend in Docker)
 * or app-dev mode (frontend running locally).
 *
 * NOTE: This is a stub implementation for CLI-7.5.
 * Full implementation is tracked in CLI-7.4.
 */

import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import fs from 'fs-extra';
import type { ProjectMode } from '../types.js';

const execAsync = promisify(exec);

/**
 * Detect project mode (default vs app-dev)
 */
export async function detectProjectMode(projectDir: string): Promise<ProjectMode> {
  // Method 1: Check running containers
  try {
    const result = await execAsync('docker compose ps --services', { cwd: projectDir });
    const services = result.stdout.split('\n').filter(Boolean);

    // If 'web' service is running, it's default mode
    if (services.includes('web')) {
      return 'default';
    }
  } catch (error) {
    // Docker Compose not running or error - fall through to other methods
  }

  // Method 2: Check for .baseboards-mode file (saved during up command)
  const modeFile = path.join(projectDir, '.baseboards-mode');
  if (await fs.pathExists(modeFile)) {
    const mode = (await fs.readFile(modeFile, 'utf-8')).trim();
    if (mode === 'default' || mode === 'app-dev') {
      return mode as ProjectMode;
    }
  }

  // Method 3: Check if web/node_modules exists (suggests app-dev)
  const webNodeModules = path.join(projectDir, 'web', 'node_modules');
  if (await fs.pathExists(webNodeModules)) {
    return 'app-dev';
  }

  // Default assumption
  return 'default';
}

/**
 * Save project mode to metadata file
 */
export async function saveProjectMode(projectDir: string, mode: ProjectMode): Promise<void> {
  const modeFile = path.join(projectDir, '.baseboards-mode');
  await fs.writeFile(modeFile, mode, 'utf-8');
}

/**
 * Docker Compose utilities shared across CLI commands
 */

import fs from 'fs-extra';
import path from 'path';

/**
 * Get compose files that exist in the project directory.
 * Always includes base compose.yaml, and includes compose.web.yaml if it exists.
 * This ensures all services are managed regardless of how they were started.
 */
export function getComposeFiles(dir: string): string[] {
  const files = ['compose.yaml'];

  if (fs.existsSync(path.join(dir, 'compose.web.yaml'))) {
    files.push('compose.web.yaml');
  }

  return files;
}

/**
 * Get base docker compose arguments for compose commands.
 * Includes env file and compose file configuration to match the up command.
 */
export function getComposeBaseArgs(dir: string): string[] {
  return [
    'compose',
    '--env-file',
    'docker/.env',
    ...getComposeFiles(dir).flatMap((f) => ['-f', f]),
  ];
}

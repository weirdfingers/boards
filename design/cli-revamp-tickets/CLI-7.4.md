# CLI-7.4: Implement Mode Detection (Default vs App-Dev)

## Description

Implement logic to detect whether a Baseboards project is running in default mode (frontend in Docker) or app-dev mode (frontend running locally). This detection is crucial for the upgrade command to handle each mode differently.

Detection strategy:
- Check if `compose.web.yaml` is currently loaded in the Docker Compose project
- Check if web service is running in Docker
- Store mode preference in project metadata file

## Dependencies

- CLI-3.5 (Compose File Loading Logic) - need to understand how compose files are loaded
- CLI-4.5 (App-Dev Success Message) - need to understand app-dev setup

## Files to Create/Modify

### New Files
- `packages/cli-launcher/src/utils/mode-detection.ts` - Mode detection logic
- `packages/cli-launcher/src/utils/__tests__/mode-detection.test.ts` - Tests

### Modified Files
- `packages/cli-launcher/src/types.ts` - Add ProjectMode type

## Implementation Details

```typescript
// packages/cli-launcher/src/types.ts
export type ProjectMode = 'default' | 'app-dev';

// packages/cli-launcher/src/utils/mode-detection.ts
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import fs from 'fs-extra';

const execAsync = promisify(exec);

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

export async function saveProjectMode(projectDir: string, mode: ProjectMode): Promise<void> {
  const modeFile = path.join(projectDir, '.baseboards-mode');
  await fs.writeFile(modeFile, mode, 'utf-8');
}
```

## Testing

Test scenarios:
- Default mode with web container running
- App-dev mode with no web container
- Mode file exists and is read correctly
- Mode file missing but web/node_modules exists
- Fallback to 'default' when no indicators found

## Acceptance Criteria

- [ ] `detectProjectMode()` correctly identifies default mode when web container is running
- [ ] Correctly identifies app-dev mode when web container is not running
- [ ] Reads mode from `.baseboards-mode` file if present
- [ ] Falls back to checking `web/node_modules` directory
- [ ] Defaults to 'default' mode when no indicators found
- [ ] `saveProjectMode()` writes mode to `.baseboards-mode` file
- [ ] Mode file is gitignored (update .gitignore in templates)
- [ ] All unit tests pass
- [ ] Integration test with actual Docker Compose setup

## Notes

- The `.baseboards-mode` file should be added to `.gitignore` in templates
- This file is created during `baseboards up` command (update CLI-4.5 to save mode)
- Mode detection must be fast (< 1 second) to avoid slowing down upgrade command

# CLI-7.7: Implement App-Dev Mode Upgrade Flow

## Description

Implement the upgrade flow for projects running in app-dev mode (frontend running locally). This flow upgrades the backend automatically but requires the user to manually update frontend dependencies since they manage the frontend codebase.

The app-dev mode upgrade should:
- Stop Docker services (backend only, no web container)
- Pull new backend Docker images
- Update `docker/.env` with new `BACKEND_VERSION`
- Start Docker services (backend only)
- Verify backend services are healthy
- Print clear instructions for manual frontend upgrade

## Dependencies

- CLI-7.5 (Replace Update Command)
- CLI-4.5 (App-Dev Success Message) - understand app-dev setup

## Files to Create/Modify

### New Files
- `packages/cli-launcher/src/commands/upgrade-app-dev.ts` - App-dev mode upgrade implementation
- `packages/cli-launcher/src/commands/__tests__/upgrade-app-dev.test.ts` - Tests

## Implementation Details

```typescript
// packages/cli-launcher/src/commands/upgrade-app-dev.ts
import path from 'path';
import fs from 'fs-extra';
import chalk from 'chalk';
import { execAsync, waitForHealth, detectPackageManager } from '../utils.js';

export async function upgradeAppDevMode(
  projectDir: string,
  currentVersion: string,
  targetVersion: string
): Promise<void> {
  console.log(chalk.blue(`\n📦 Upgrading backend from v${currentVersion} to v${targetVersion}\n`));

  try {
    // 1. Stop backend services
    console.log(chalk.gray('⏸️  Stopping backend services...'));
    await execAsync('docker compose down', { cwd: projectDir });

    // 2. Pull new backend images
    console.log(chalk.gray('⬇️  Pulling new backend images...'));
    await execAsync('docker compose pull api worker', { cwd: projectDir });

    // 3. Update docker/.env
    console.log(chalk.gray('⚙️  Updating configuration...'));
    await updateEnvVersion(projectDir, targetVersion);

    // 4. Start backend services (no web)
    console.log(chalk.gray('🚀 Starting backend services...'));
    await execAsync('docker compose up -d db cache api worker', { cwd: projectDir });

    // 5. Wait for backend health
    console.log(chalk.gray('🏥 Waiting for backend to be healthy...'));
    await waitForHealth(projectDir, ['db', 'cache', 'api', 'worker']);

    console.log(chalk.green(`\n✅ Backend upgraded to v${targetVersion}!\n`));

    // 6. Print manual frontend upgrade instructions
    await printAppDevUpgradeInstructions(projectDir, currentVersion, targetVersion);

  } catch (error) {
    console.error(chalk.red(`\n❌ Upgrade failed: ${error.message}\n`));
    console.log(chalk.yellow('To rollback:'));
    console.log(chalk.gray(`  1. Edit docker/.env and set BACKEND_VERSION=${currentVersion}`));
    console.log(chalk.gray('  2. Run: docker compose pull'));
    console.log(chalk.gray('  3. Run: docker compose up -d db cache api worker\n'));
    throw error;
  }
}

async function updateEnvVersion(projectDir: string, version: string): Promise<void> {
  const envPath = path.join(projectDir, 'docker', '.env');
  let content = await fs.readFile(envPath, 'utf-8');

  // Replace BACKEND_VERSION line
  content = content.replace(
    /^BACKEND_VERSION=.*/m,
    `BACKEND_VERSION=${version}`
  );

  await fs.writeFile(envPath, content, 'utf-8');
}

async function printAppDevUpgradeInstructions(
  projectDir: string,
  oldVersion: string,
  newVersion: string
): Promise<void> {
  // Detect package manager from web/package-lock.json, pnpm-lock.yaml, etc.
  const packageManager = await detectPackageManager(path.join(projectDir, 'web'));

  const updateCommand = packageManager === 'npm'
    ? `npm install @weirdfingers/boards@${newVersion}`
    : packageManager === 'yarn'
    ? `yarn upgrade @weirdfingers/boards@${newVersion}`
    : packageManager === 'bun'
    ? `bun update @weirdfingers/boards@${newVersion}`
    : `pnpm update @weirdfingers/boards@${newVersion}`;

  console.log(chalk.yellow('⚠️  Frontend requires manual upgrade:\n'));
  console.log(chalk.gray('   1. Stop your dev server (Ctrl+C if running)\n'));
  console.log(chalk.gray('   2. Update the frontend package:\n'));
  console.log(chalk.cyan(`      cd ${path.basename(projectDir)}/web`));
  console.log(chalk.cyan(`      ${updateCommand}\n`));
  console.log(chalk.gray('   3. Check for breaking changes:\n'));
  console.log(chalk.gray(`      https://github.com/weirdfingers/boards/releases/tag/v${newVersion}\n`));
  console.log(chalk.gray('   4. Restart your dev server:\n'));
  console.log(chalk.cyan(`      ${packageManager} dev\n`));

  // Check if there are uncommitted changes
  const webDir = path.join(projectDir, 'web');
  try {
    const { stdout } = await execAsync('git status --porcelain', { cwd: webDir });
    if (stdout.trim()) {
      console.log(chalk.yellow('⚠️  You have uncommitted changes in web/'));
      console.log(chalk.gray('   Consider committing before updating dependencies.\n'));
    }
  } catch {
    // Not a git repo or git not available, skip warning
  }
}
```

## Testing

### Integration Test

```typescript
// packages/cli-launcher/src/commands/__tests__/upgrade-app-dev.test.ts
describe('App-Dev Mode Upgrade', () => {
  test('upgrades backend successfully', async () => {
    const projectDir = await createTestProject('0.7.0', 'app-dev');

    // Run upgrade
    await upgradeAppDevMode(projectDir, '0.7.0', '0.8.0');

    // Verify:
    // 1. docker/.env has new version
    const envContent = await fs.readFile(path.join(projectDir, 'docker', '.env'), 'utf-8');
    expect(envContent).toContain('BACKEND_VERSION=0.8.0');

    // 2. Backend services are running (not web)
    const services = await getRunningServices(projectDir);
    expect(services).toContain('api');
    expect(services).toContain('worker');
    expect(services).not.toContain('web');

    // 3. web/package.json is unchanged (user must update manually)
    const packageJson = await fs.readJson(path.join(projectDir, 'web', 'package.json'));
    expect(packageJson.dependencies['@weirdfingers/boards']).toBe('0.7.0');
  });

  test('detects package manager and prints correct update command', async () => {
    // Test with pnpm project
    // Test with npm project
    // Test with yarn project
    // Verify correct update command is shown
  });

  test('warns about uncommitted changes', async () => {
    // Create app-dev project with uncommitted changes
    // Verify warning is displayed
  });
});
```

## Acceptance Criteria

- [ ] Stops backend services with `docker compose down`
- [ ] Pulls new backend images (api, worker)
- [ ] Updates `docker/.env` with new `BACKEND_VERSION`
- [ ] Starts backend services only (db, cache, api, worker) - NOT web
- [ ] Waits for backend services to be healthy
- [ ] Detects package manager (pnpm, npm, yarn, bun) from lockfiles
- [ ] Prints manual frontend update instructions with correct package manager command
- [ ] Warns user if web/ directory has uncommitted git changes
- [ ] Includes link to release notes for breaking changes
- [ ] On failure, prints rollback instructions
- [ ] Does NOT modify `web/package.json` (user controls this)
- [ ] Does NOT modify `web/node_modules` or frontend code
- [ ] Integration test passes with real Docker Compose

## Notes

- Package manager detection:
  - `pnpm-lock.yaml` → pnpm
  - `package-lock.json` → npm
  - `yarn.lock` → yarn
  - `bun.lockb` → bun
- Frontend update is intentionally manual because user may have customizations
- User must check release notes for frontend breaking changes
- Warn about uncommitted changes to prevent accidental loss of work
- Backend migrations still run automatically during API startup

# CLI-7.6: Implement Default Mode Upgrade Flow

## Description

Implement the upgrade flow for projects running in default mode (frontend in Docker). This flow automates the entire upgrade process: stopping services, pulling new images, updating configurations, rebuilding the frontend Docker image, and restarting services.

The default mode upgrade should:
- Stop all running services
- Pull new backend Docker images
- Update `web/package.json` with new `@weirdfingers/boards` version
- Rebuild frontend Docker image (`docker compose build web`)
- Update `docker/.env` with new `BACKEND_VERSION`
- Start services (migrations run automatically via healthcheck)
- Verify all services are healthy

## Dependencies

- CLI-7.5 (Replace Update Command)
- CLI-3.5 (Compose File Loading Logic)

## Files to Create/Modify

### New Files
- `packages/cli-launcher/src/commands/upgrade-default.ts` - Default mode upgrade implementation
- `packages/cli-launcher/src/commands/__tests__/upgrade-default.test.ts` - Tests

## Implementation Details

```typescript
// packages/cli-launcher/src/commands/upgrade-default.ts
import path from 'path';
import fs from 'fs-extra';
import chalk from 'chalk';
import { execAsync, waitForHealth } from '../utils.js';

export async function upgradeDefaultMode(
  projectDir: string,
  currentVersion: string,
  targetVersion: string
): Promise<void> {
  console.log(chalk.blue(`\n📦 Upgrading from v${currentVersion} to v${targetVersion}\n`));

  try {
    // 1. Stop services
    console.log(chalk.gray('⏸️  Stopping services...'));
    await execAsync('docker compose down', { cwd: projectDir });

    // 2. Pull new backend images
    console.log(chalk.gray('⬇️  Pulling new backend images...'));
    await execAsync(`docker compose pull api worker`, { cwd: projectDir });

    // 3. Update web/package.json
    console.log(chalk.gray('📝 Updating frontend dependencies...'));
    await updateWebPackageJson(projectDir, targetVersion);

    // 4. Rebuild frontend Docker image
    console.log(chalk.gray('🔨 Rebuilding frontend image (this may take a few minutes)...'));
    await execAsync('docker compose build web', { cwd: projectDir });

    // 5. Update docker/.env with new version
    console.log(chalk.gray('⚙️  Updating configuration...'));
    await updateEnvVersion(projectDir, targetVersion);

    // 6. Start services
    console.log(chalk.gray('🚀 Starting services...'));
    await execAsync('docker compose up -d', { cwd: projectDir });

    // 7. Wait for health checks
    console.log(chalk.gray('🏥 Waiting for services to be healthy...'));
    await waitForHealth(projectDir, ['db', 'cache', 'api', 'worker', 'web']);

    // Success!
    console.log(chalk.green(`\n✅ Successfully upgraded to v${targetVersion}!\n`));
    printUpgradeSuccess(projectDir, targetVersion);

  } catch (error) {
    console.error(chalk.red(`\n❌ Upgrade failed: ${error.message}\n`));
    console.log(chalk.yellow('To rollback:'));
    console.log(chalk.gray(`  1. Edit docker/.env and set BACKEND_VERSION=${currentVersion}`));
    console.log(chalk.gray('  2. Run: docker compose pull'));
    console.log(chalk.gray('  3. Run: docker compose build web'));
    console.log(chalk.gray('  4. Run: docker compose up -d\n'));
    throw error;
  }
}

async function updateWebPackageJson(projectDir: string, version: string): Promise<void> {
  const packageJsonPath = path.join(projectDir, 'web', 'package.json');
  const packageJson = await fs.readJson(packageJsonPath);

  // Update @weirdfingers/boards version
  if (packageJson.dependencies && packageJson.dependencies['@weirdfingers/boards']) {
    packageJson.dependencies['@weirdfingers/boards'] = version;
  }

  await fs.writeJson(packageJsonPath, packageJson, { spaces: 2 });
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

function printUpgradeSuccess(projectDir: string, version: string): void {
  console.log(chalk.gray('   Your Baseboards installation has been upgraded.'));
  console.log(chalk.gray('   All services are running and healthy.\n'));

  console.log(chalk.gray('Next steps:'));
  console.log(chalk.gray(`  • Check release notes: https://github.com/weirdfingers/boards/releases/tag/v${version}`));
  console.log(chalk.gray(`  • View logs: baseboards logs ${path.basename(projectDir)}`));
  console.log(chalk.gray(`  • Check status: baseboards status ${path.basename(projectDir)}\n`));
}
```

## Testing

### Integration Test

```typescript
// packages/cli-launcher/src/commands/__tests__/upgrade-default.test.ts
describe('Default Mode Upgrade', () => {
  test('upgrades successfully', async () => {
    // Create test project with current version
    const projectDir = await createTestProject('0.7.0', 'default');

    // Run upgrade
    await upgradeDefaultMode(projectDir, '0.7.0', '0.8.0');

    // Verify:
    // 1. web/package.json has new version
    const packageJson = await fs.readJson(path.join(projectDir, 'web', 'package.json'));
    expect(packageJson.dependencies['@weirdfingers/boards']).toBe('0.8.0');

    // 2. docker/.env has new version
    const envContent = await fs.readFile(path.join(projectDir, 'docker', '.env'), 'utf-8');
    expect(envContent).toContain('BACKEND_VERSION=0.8.0');

    // 3. Services are running
    const services = await getRunningServices(projectDir);
    expect(services).toContain('web');
    expect(services).toContain('api');
  });

  test('provides rollback instructions on failure', async () => {
    // Mock docker compose failure
    // Verify error message includes rollback steps
  });
});
```

## Acceptance Criteria

- [ ] Stops all services with `docker compose down`
- [ ] Pulls new backend images (api, worker)
- [ ] Updates `web/package.json` with new `@weirdfingers/boards` version
- [ ] Rebuilds frontend Docker image with `docker compose build web`
- [ ] Updates `docker/.env` with new `BACKEND_VERSION`
- [ ] Starts services with `docker compose up -d`
- [ ] Waits for all services to be healthy (db, cache, api, worker, web)
- [ ] Prints success message with next steps
- [ ] On failure, prints rollback instructions
- [ ] Preserves all configuration files and data
- [ ] Integration test passes with real Docker Compose

## Notes

- The frontend rebuild can take 3-5 minutes depending on the template
- Database migrations run automatically during API container startup
- If healthcheck times out, provide diagnostic information (check logs)
- Configuration files (`config/*.yaml`, `api/.env`, `web/.env`) are preserved
- Storage data (`data/storage/`) is preserved via Docker volumes

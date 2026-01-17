# CLI-7.5: Replace Update Command with Upgrade Command

## Description

Replace the existing placeholder `update` command with the new `upgrade` command. This command serves as the entry point for the upgrade workflow, handling CLI arguments, detecting project mode, and routing to the appropriate upgrade flow (default or app-dev).

The upgrade command should:
- Validate the project directory is a Baseboards project
- Determine current version from `docker/.env`
- Determine target version (from `--version` flag or latest from npm)
- Detect project mode (default vs app-dev)
- Check compatibility and display warnings
- Prompt for confirmation unless `--force`
- Route to appropriate upgrade flow

## Dependencies

- CLI-7.2 (Compatibility Manifest Fetcher)
- CLI-7.3 (Compatibility Checker)
- CLI-7.4 (Mode Detection)

## Files to Create/Modify

### Modified Files
- `packages/cli-launcher/src/commands/upgrade.ts` - Replace placeholder with full implementation
- `packages/cli-launcher/src/types.ts` - Add UpgradeOptions interface
- `packages/cli-launcher/src/commands/index.ts` - Export upgrade command

## Implementation Details

```typescript
// packages/cli-launcher/src/types.ts
export interface UpgradeOptions {
  version?: string;
  dryRun?: boolean;
  force?: boolean;
}

// packages/cli-launcher/src/commands/upgrade.ts
import path from 'path';
import chalk from 'chalk';
import prompts from 'prompts';
import { isScaffolded, getCurrentVersion } from '../utils.js';
import { detectProjectMode } from '../utils/mode-detection.js';
import { checkCompatibility } from '../utils/compatibility-checker.js';
import { upgradeDefaultMode } from './upgrade-default.js';
import { upgradeAppDevMode } from './upgrade-app-dev.js';
import type { UpgradeOptions } from '../types.js';

export async function upgrade(
  directory: string,
  options: UpgradeOptions
): Promise<void> {
  const dir = path.resolve(process.cwd(), directory);

  // 1. Validate project directory
  if (!isScaffolded(dir)) {
    console.error(chalk.red('\n❌ Error: Not a Baseboards project'));
    console.log(chalk.gray('   Run'), chalk.cyan('baseboards up'), chalk.gray('to scaffold a project first.'));
    process.exit(1);
  }

  // 2. Determine current version
  const currentVersion = await getCurrentVersion(dir);
  if (!currentVersion) {
    console.error(chalk.red('\n❌ Error: Could not determine current version'));
    console.log(chalk.gray('   Check docker/.env for BACKEND_VERSION'));
    process.exit(1);
  }

  // 3. Determine target version
  const targetVersion = options.version || await getLatestVersion();

  // 4. Check if already at target version
  if (currentVersion === targetVersion) {
    console.log(chalk.green(`\n✅ Already at v${targetVersion}`));
    return;
  }

  console.log(chalk.blue(`\n📦 Upgrade: v${currentVersion} → v${targetVersion}\n`));

  // 5. Check compatibility
  const compatCheck = await checkCompatibility(currentVersion, targetVersion);

  // Display warnings
  if (compatCheck.warnings.length > 0) {
    console.log(compatCheck.warnings.join('\n'));
    console.log('');
  }

  if (compatCheck.requiredActions.length > 0) {
    console.log(chalk.yellow('⚠️  Required manual actions:'));
    compatCheck.requiredActions.forEach((action) => {
      console.log(chalk.gray(`   • ${action}`));
    });
    console.log('');
  }

  // 6. Dry run mode - stop here
  if (options.dryRun) {
    console.log(chalk.blue('🔍 Dry run mode - no changes made\n'));
    return;
  }

  // 7. Prompt for confirmation (unless --force)
  if (!options.force && compatCheck.breaking) {
    const { proceed } = await prompts({
      type: 'confirm',
      name: 'proceed',
      message: 'Continue with upgrade?',
      initial: false,
    });

    if (!proceed) {
      console.log(chalk.gray('\nUpgrade cancelled\n'));
      return;
    }
  }

  // 8. Detect project mode
  const mode = await detectProjectMode(dir);

  // 9. Route to appropriate upgrade flow
  if (mode === 'app-dev') {
    await upgradeAppDevMode(dir, currentVersion, targetVersion);
  } else {
    await upgradeDefaultMode(dir, currentVersion, targetVersion);
  }
}

async function getLatestVersion(): Promise<string> {
  // Fetch latest version from npm registry
  const { execAsync } = await import('../utils.js');
  try {
    const result = await execAsync('npm view @weirdfingers/baseboards version');
    return result.stdout.trim();
  } catch (error) {
    throw new Error('Failed to fetch latest version from npm');
  }
}
```

## Testing

### Manual Testing Checklist

```bash
# 1. Test with default mode project
cd test-projects/default-mode
baseboards upgrade . --dry-run
baseboards upgrade . --version 0.8.0

# 2. Test with app-dev mode project
cd test-projects/app-dev-mode
baseboards upgrade . --dry-run
baseboards upgrade .

# 3. Test already at target version
baseboards upgrade . --version 0.7.0  # Current version

# 4. Test with breaking changes
# (use test fixtures with compatibility manifests)

# 5. Test force flag
baseboards upgrade . --force  # Should skip confirmation

# 6. Test invalid project directory
baseboards upgrade ./not-a-project
```

## Acceptance Criteria

- [ ] Command validates project directory is scaffolded
- [ ] Detects current version from `docker/.env` BACKEND_VERSION
- [ ] Determines target version from `--version` flag or npm latest
- [ ] Exits early if already at target version
- [ ] Checks compatibility and displays warnings
- [ ] Displays required actions if present
- [ ] Dry-run mode shows warnings but makes no changes
- [ ] Prompts for confirmation when breaking changes detected (unless `--force`)
- [ ] Detects project mode (default vs app-dev)
- [ ] Routes to `upgradeDefaultMode()` for default projects
- [ ] Routes to `upgradeAppDevMode()` for app-dev projects
- [ ] Error handling for network failures, invalid versions, etc.
- [ ] Help text updated with examples
- [ ] All unit tests pass

## Notes

- The `getCurrentVersion()` utility reads `docker/.env` and parses `BACKEND_VERSION`
- The `getLatestVersion()` utility queries npm registry
- Confirmation prompt is skipped when `--force` is used
- Dry-run mode is useful for CI/CD pipelines to check compatibility before upgrading

## Documentation Requirements

After implementing this command, ensure the following documentation is updated in **CLI-6.2**:

- [ ] Add `baseboards upgrade` to Commands Reference page with:
  - Command syntax and all flags (--version, --dry-run, --force)
  - Examples for common upgrade scenarios
  - Exit codes and error messages
  - Comparison with old `update` command (deprecated)

- [ ] Update Migration Guide to explain upgrade workflow
- [ ] Add troubleshooting section for upgrade failures
- [ ] Update CLI README with upgrade command examples

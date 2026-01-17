# CLI-7.8: Add Dry-Run and Force Flags

## Description

Add support for `--dry-run` and `--force` flags to the upgrade command. These flags provide users with more control over the upgrade process:

- `--dry-run`: Preview the upgrade without making any changes (check compatibility, show warnings)
- `--force`: Skip confirmation prompts and compatibility warnings (useful for automation)

These flags are important for:
- CI/CD pipelines that want to check compatibility before upgrading
- Automated deployments that need non-interactive upgrades
- Users who want to see what will happen before committing to an upgrade

## Dependencies

- CLI-7.5 (Replace Update Command)
- CLI-7.6 (Default Mode Upgrade Flow)
- CLI-7.7 (App-Dev Mode Upgrade Flow)

## Files to Create/Modify

### Modified Files
- `packages/cli-launcher/src/commands/upgrade.ts` - Add flag handling
- `packages/cli-launcher/src/types.ts` - Update UpgradeOptions interface
- `packages/cli-launcher/src/cli.ts` - Add command-line argument parsing

## Implementation Details

### Command-Line Arguments

```typescript
// packages/cli-launcher/src/cli.ts
program
  .command('upgrade [directory]')
  .description('Upgrade an existing Baseboards installation')
  .option('--version <version>', 'Target version (default: latest)')
  .option('--dry-run', 'Show what would be upgraded without making changes')
  .option('--force', 'Skip compatibility checks and confirmation prompts')
  .action(async (directory, options) => {
    await upgrade(directory || '.', {
      version: options.version,
      dryRun: options.dryRun || false,
      force: options.force || false,
    });
  });
```

### Dry-Run Implementation

```typescript
// packages/cli-launcher/src/commands/upgrade.ts (modifications)
export async function upgrade(
  directory: string,
  options: UpgradeOptions
): Promise<void> {
  // ... existing validation and version detection ...

  // Check compatibility
  const compatCheck = await checkCompatibility(currentVersion, targetVersion);

  // Display upgrade plan
  console.log(chalk.blue('📋 Upgrade Plan:\n'));
  console.log(chalk.gray(`   Current version: ${currentVersion}`));
  console.log(chalk.gray(`   Target version:  ${targetVersion}`));
  console.log(chalk.gray(`   Project mode:    ${mode}`));
  console.log('');

  // Display what would be upgraded
  if (mode === 'default') {
    console.log(chalk.gray('   Steps:'));
    console.log(chalk.gray('   1. Stop all services'));
    console.log(chalk.gray('   2. Pull new backend images'));
    console.log(chalk.gray('   3. Update web/package.json'));
    console.log(chalk.gray('   4. Rebuild frontend Docker image'));
    console.log(chalk.gray('   5. Update docker/.env'));
    console.log(chalk.gray('   6. Start services'));
    console.log(chalk.gray('   7. Wait for health checks'));
  } else {
    console.log(chalk.gray('   Steps:'));
    console.log(chalk.gray('   1. Stop backend services'));
    console.log(chalk.gray('   2. Pull new backend images'));
    console.log(chalk.gray('   3. Update docker/.env'));
    console.log(chalk.gray('   4. Start backend services'));
    console.log(chalk.gray('   5. Print manual frontend update instructions'));
  }
  console.log('');

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

  // Dry run mode - stop here
  if (options.dryRun) {
    console.log(chalk.blue('🔍 Dry run complete - no changes made\n'));
    return;
  }

  // Prompt for confirmation (unless --force)
  if (!options.force && (compatCheck.breaking || compatCheck.warnings.length > 0)) {
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

  // ... route to upgrade flow ...
}
```

### Force Flag Implementation

```typescript
// The force flag affects:
// 1. Skips confirmation prompt
// 2. Proceeds even with breaking changes
// 3. Useful for CI/CD automation

// In upgrade.ts:
if (!options.force && compatCheck.breaking) {
  // Show confirmation prompt
}

// Warning when using --force with breaking changes:
if (options.force && compatCheck.breaking) {
  console.log(chalk.yellow('⚠️  --force flag used: skipping confirmation despite breaking changes\n'));
}
```

## Testing

### Manual Testing

```bash
# Test dry-run flag
baseboards upgrade test-project --dry-run
# Should show: upgrade plan, warnings, but make no changes

baseboards upgrade test-project --dry-run --version 0.8.0
# Should show: specific version upgrade plan

# Test force flag
baseboards upgrade test-project --force
# Should: skip confirmation, proceed immediately

baseboards upgrade test-project --force --version 0.8.0
# Should: upgrade to specific version without prompts

# Test combination
baseboards upgrade test-project --dry-run --force
# Should: dry-run takes precedence, no actual upgrade

# Test in CI/CD simulation
baseboards upgrade test-project --dry-run; echo $?
# Should: exit 0 even with breaking changes (just shows warnings)

baseboards upgrade test-project --force; echo $?
# Should: exit 0 on success, non-zero on failure
```

### Unit Tests

```typescript
// packages/cli-launcher/src/commands/__tests__/upgrade.test.ts
describe('Upgrade Command Flags', () => {
  test('--dry-run shows upgrade plan without making changes', async () => {
    const mockConsoleLog = jest.spyOn(console, 'log');

    await upgrade('test-project', { dryRun: true });

    expect(mockConsoleLog).toHaveBeenCalledWith(
      expect.stringContaining('Dry run complete - no changes made')
    );

    // Verify no actual changes were made
    // (check files, docker services, etc.)
  });

  test('--force skips confirmation prompt', async () => {
    const mockPrompts = jest.spyOn(prompts, 'prompt');

    await upgrade('test-project', { force: true });

    expect(mockPrompts).not.toHaveBeenCalled();
  });

  test('--force shows warning when breaking changes present', async () => {
    const mockConsoleLog = jest.spyOn(console, 'log');

    // Mock compatibility check with breaking changes
    await upgrade('test-project', { force: true });

    expect(mockConsoleLog).toHaveBeenCalledWith(
      expect.stringContaining('--force flag used')
    );
  });

  test('--dry-run with --force still performs dry run', async () => {
    await upgrade('test-project', { dryRun: true, force: true });

    // Verify no changes made (dry-run takes precedence)
  });
});
```

## Acceptance Criteria

- [ ] `--dry-run` flag displays upgrade plan without making changes
- [ ] Dry-run shows: current version, target version, project mode, steps
- [ ] Dry-run shows all compatibility warnings and required actions
- [ ] Dry-run exits without prompting or making changes
- [ ] Dry-run exits with code 0 (success) even with warnings
- [ ] `--force` flag skips confirmation prompts
- [ ] Force flag proceeds even with breaking changes
- [ ] Force flag shows warning when skipping breaking change confirmation
- [ ] Dry-run takes precedence when both `--dry-run` and `--force` are used
- [ ] Flags work with `--version` flag
- [ ] Exit codes: 0 for success/dry-run, non-zero for errors
- [ ] Help text documents both flags with examples
- [ ] All unit tests pass
- [ ] Manual testing checklist complete

## Notes

- Dry-run is useful for CI/CD pipelines to check compatibility without upgrading
- Force flag is useful for automated deployments in non-interactive environments
- When both flags are used, dry-run takes precedence (safer default)
- Exit codes should be meaningful:
  - 0: success or dry-run complete
  - 1: user cancelled or validation error
  - 2: upgrade failed (docker, network, etc.)
- Dry-run should still validate network connectivity to fetch manifests

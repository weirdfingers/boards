/**
 * Tests for the upgrade command with --dry-run and --force flags
 */

import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { upgrade } from '../upgrade.js';
import * as utils from '../../utils.js';
import * as modeDetection from '../../utils/mode-detection.js';
import * as compatibilityChecker from '../../utils/compatibility-checker.js';
import * as upgradeDefault from '../upgrade-default.js';
import * as upgradeAppDev from '../upgrade-app-dev.js';
import prompts from 'prompts';

// Mock dependencies
vi.mock('../../utils.js');
vi.mock('../../utils/mode-detection.js');
vi.mock('../../utils/compatibility-checker.js');
vi.mock('../upgrade-default.js');
vi.mock('../upgrade-app-dev.js');
vi.mock('prompts');

describe('Upgrade Command Flags', () => {
  const mockDir = '/test-project';
  const mockCurrentVersion = '0.7.0';
  const mockTargetVersion = '0.8.0';

  beforeEach(() => {
    // Reset all mocks before each test
    vi.clearAllMocks();

    // Setup default mocks
    vi.mocked(utils.isScaffolded).mockReturnValue(true);
    vi.mocked(utils.getCurrentVersion).mockResolvedValue(mockCurrentVersion);
    vi.mocked(utils.execAsync).mockResolvedValue({ stdout: mockTargetVersion, stderr: '' });
    vi.mocked(modeDetection.detectProjectMode).mockResolvedValue('default');
    vi.mocked(compatibilityChecker.checkCompatibility).mockResolvedValue({
      fromVersion: mockCurrentVersion,
      toVersion: mockTargetVersion,
      breaking: false,
      warnings: [],
      requiredActions: [],
    });
    vi.mocked(upgradeDefault.upgradeDefaultMode).mockResolvedValue(undefined);
    vi.mocked(upgradeAppDev.upgradeAppDevMode).mockResolvedValue(undefined);

    // Mock console methods
    vi.spyOn(console, 'log').mockImplementation(() => undefined);
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('--dry-run flag', () => {
    test('shows upgrade plan without making changes', async () => {
      const mockConsoleLog = vi.spyOn(console, 'log');

      await upgrade(mockDir, { dryRun: true });

      // Should show upgrade plan
      expect(mockConsoleLog).toHaveBeenCalledWith(
        expect.stringContaining('📋 Upgrade Plan:')
      );
      expect(mockConsoleLog).toHaveBeenCalledWith(
        expect.stringContaining('Current version:')
      );
      expect(mockConsoleLog).toHaveBeenCalledWith(
        expect.stringContaining('Target version:')
      );
      expect(mockConsoleLog).toHaveBeenCalledWith(
        expect.stringContaining('Project mode:')
      );

      // Should show dry run complete message
      expect(mockConsoleLog).toHaveBeenCalledWith(
        expect.stringContaining('🔍 Dry run complete - no changes made')
      );

      // Should NOT call upgrade functions
      expect(upgradeDefault.upgradeDefaultMode).not.toHaveBeenCalled();
      expect(upgradeAppDev.upgradeAppDevMode).not.toHaveBeenCalled();
    });

    test('shows detailed steps for default mode', async () => {
      const mockConsoleLog = vi.spyOn(console, 'log');
      vi.mocked(modeDetection.detectProjectMode).mockResolvedValue('default');

      await upgrade(mockDir, { dryRun: true });

      expect(mockConsoleLog).toHaveBeenCalledWith(
        expect.stringContaining('Stop all services')
      );
      expect(mockConsoleLog).toHaveBeenCalledWith(
        expect.stringContaining('Pull new backend images')
      );
      expect(mockConsoleLog).toHaveBeenCalledWith(
        expect.stringContaining('Rebuild frontend Docker image')
      );
    });

    test('shows detailed steps for app-dev mode', async () => {
      const mockConsoleLog = vi.spyOn(console, 'log');
      vi.mocked(modeDetection.detectProjectMode).mockResolvedValue('app-dev');

      await upgrade(mockDir, { dryRun: true });

      expect(mockConsoleLog).toHaveBeenCalledWith(
        expect.stringContaining('Stop backend services')
      );
      expect(mockConsoleLog).toHaveBeenCalledWith(
        expect.stringContaining('Print manual frontend update instructions')
      );
    });

    test('shows warnings and required actions', async () => {
      const mockConsoleLog = vi.spyOn(console, 'log');
      vi.mocked(compatibilityChecker.checkCompatibility).mockResolvedValue({
        fromVersion: mockCurrentVersion,
        toVersion: mockTargetVersion,
        breaking: true,
        warnings: ['⚠️  Warning: Breaking changes detected'],
        requiredActions: ['Run migration manually', 'Update config'],
      });

      await upgrade(mockDir, { dryRun: true });

      expect(mockConsoleLog).toHaveBeenCalledWith(
        expect.stringContaining('Breaking changes detected')
      );
      expect(mockConsoleLog).toHaveBeenCalledWith(
        expect.stringContaining('Required manual actions')
      );
      expect(mockConsoleLog).toHaveBeenCalledWith(
        expect.stringContaining('Run migration manually')
      );
    });

    test('works with --version flag', async () => {
      await upgrade(mockDir, { dryRun: true, version: '0.9.0' });

      // Should not call upgrade functions
      expect(upgradeDefault.upgradeDefaultMode).not.toHaveBeenCalled();
    });

    test('exits with success even with warnings', async () => {
      vi.mocked(compatibilityChecker.checkCompatibility).mockResolvedValue({
        fromVersion: mockCurrentVersion,
        toVersion: mockTargetVersion,
        breaking: true,
        warnings: ['⚠️  Warning: Breaking changes'],
        requiredActions: [],
      });

      // Should not throw
      await expect(upgrade(mockDir, { dryRun: true })).resolves.toBeUndefined();
    });
  });

  describe('--force flag', () => {
    test('skips confirmation prompt', async () => {
      vi.mocked(compatibilityChecker.checkCompatibility).mockResolvedValue({
        fromVersion: mockCurrentVersion,
        toVersion: mockTargetVersion,
        breaking: true,
        warnings: [],
        requiredActions: [],
      });

      await upgrade(mockDir, { force: true });

      // Should not prompt
      expect(prompts).not.toHaveBeenCalled();

      // Should proceed with upgrade
      expect(upgradeDefault.upgradeDefaultMode).toHaveBeenCalled();
    });

    test('shows warning when skipping breaking change confirmation', async () => {
      const mockConsoleLog = vi.spyOn(console, 'log');
      vi.mocked(compatibilityChecker.checkCompatibility).mockResolvedValue({
        fromVersion: mockCurrentVersion,
        toVersion: mockTargetVersion,
        breaking: true,
        warnings: [],
        requiredActions: [],
      });

      await upgrade(mockDir, { force: true });

      expect(mockConsoleLog).toHaveBeenCalledWith(
        expect.stringContaining('--force flag used: skipping confirmation despite breaking changes')
      );
    });

    test('does not show warning when no breaking changes', async () => {
      const mockConsoleLog = vi.spyOn(console, 'log');
      vi.mocked(compatibilityChecker.checkCompatibility).mockResolvedValue({
        fromVersion: mockCurrentVersion,
        toVersion: mockTargetVersion,
        breaking: false,
        warnings: [],
        requiredActions: [],
      });

      await upgrade(mockDir, { force: true });

      expect(mockConsoleLog).not.toHaveBeenCalledWith(
        expect.stringContaining('--force flag used')
      );
    });

    test('works with --version flag', async () => {
      await upgrade(mockDir, { force: true, version: '0.9.0' });

      expect(upgradeDefault.upgradeDefaultMode).toHaveBeenCalled();
    });
  });

  describe('--dry-run and --force together', () => {
    test('dry-run takes precedence - no actual upgrade', async () => {
      await upgrade(mockDir, { dryRun: true, force: true });

      // Should show dry run message
      expect(console.log).toHaveBeenCalledWith(
        expect.stringContaining('🔍 Dry run complete - no changes made')
      );

      // Should NOT call upgrade functions (dry-run takes precedence)
      expect(upgradeDefault.upgradeDefaultMode).not.toHaveBeenCalled();
      expect(upgradeAppDev.upgradeAppDevMode).not.toHaveBeenCalled();
    });
  });

  describe('Normal confirmation flow', () => {
    test('prompts for confirmation when breaking changes and no --force', async () => {
      vi.mocked(compatibilityChecker.checkCompatibility).mockResolvedValue({
        fromVersion: mockCurrentVersion,
        toVersion: mockTargetVersion,
        breaking: true,
        warnings: [],
        requiredActions: [],
      });
      vi.mocked(prompts).mockResolvedValue({ proceed: true });

      await upgrade(mockDir, {});

      expect(prompts).toHaveBeenCalledWith({
        type: 'confirm',
        name: 'proceed',
        message: 'Continue with upgrade?',
        initial: false,
      });
    });

    test('cancels upgrade when user declines', async () => {
      const mockConsoleLog = vi.spyOn(console, 'log');
      vi.mocked(compatibilityChecker.checkCompatibility).mockResolvedValue({
        fromVersion: mockCurrentVersion,
        toVersion: mockTargetVersion,
        breaking: true,
        warnings: [],
        requiredActions: [],
      });
      vi.mocked(prompts).mockResolvedValue({ proceed: false });

      await upgrade(mockDir, {});

      expect(mockConsoleLog).toHaveBeenCalledWith(
        expect.stringContaining('Upgrade cancelled')
      );
      expect(upgradeDefault.upgradeDefaultMode).not.toHaveBeenCalled();
    });

    test('proceeds when no breaking changes', async () => {
      vi.mocked(compatibilityChecker.checkCompatibility).mockResolvedValue({
        fromVersion: mockCurrentVersion,
        toVersion: mockTargetVersion,
        breaking: false,
        warnings: [],
        requiredActions: [],
      });

      await upgrade(mockDir, {});

      // Should not prompt
      expect(prompts).not.toHaveBeenCalled();

      // Should proceed
      expect(upgradeDefault.upgradeDefaultMode).toHaveBeenCalled();
    });
  });

  describe('Already at target version', () => {
    test('exits early when already at target version', async () => {
      const mockConsoleLog = vi.spyOn(console, 'log');
      vi.mocked(utils.getCurrentVersion).mockResolvedValue(mockTargetVersion);

      await upgrade(mockDir, { version: mockTargetVersion });

      expect(mockConsoleLog).toHaveBeenCalledWith(
        expect.stringContaining(`Already at v${mockTargetVersion}`)
      );
      expect(upgradeDefault.upgradeDefaultMode).not.toHaveBeenCalled();
    });
  });
});

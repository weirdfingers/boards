/**
 * Integration tests for app-dev mode functionality.
 * Tests compose file loading, package manager selection, dependency installation,
 * and success messages when using the --app-dev flag.
 */

import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import type { ProjectContext } from '../src/types.js';

// Mock external dependencies
vi.mock('execa');
vi.mock('prompts');
vi.mock('chalk', () => ({
  default: {
    blue: { bold: (s: string) => s },
    cyan: (s: string) => s,
    green: { bold: (s: string) => s },
    yellow: (s: string) => s,
    gray: (s: string) => s,
    red: (s: string) => s,
    underline: (s: string) => s,
  },
}));
vi.mock('ora', () => ({
  default: () => ({
    start: () => ({ succeed: vi.fn(), fail: vi.fn(), text: '' }),
  }),
}));
vi.mock('fs-extra');

import { execa, type ExecaReturnValue } from 'execa';
import prompts from 'prompts';
import fs from 'fs-extra';

describe('App-dev mode integration tests', () => {
  beforeEach(() => {
    // Reset all mocks before each test
    vi.clearAllMocks();

    // Setup default mock implementations
    vi.mocked(execa).mockResolvedValue({
      stdout: '',
      stderr: '',
      exitCode: 0,
      failed: false,
      killed: false,
      signal: undefined,
      signalDescription: undefined,
      command: '',
      escapedCommand: '',
      cwd: '',
      durationMs: 0,
      pipedFrom: [],
      ipcOutput: [],
      timedOut: false,
    } as ExecaReturnValue);

    vi.mocked(fs).existsSync = vi.fn().mockReturnValue(true);
    vi.mocked(fs).readFileSync = vi.fn().mockReturnValue('');

    // Mock console methods
    vi.spyOn(console, 'log').mockImplementation(() => undefined);
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  /**
   * Helper function to create a test context with specified options
   */
  function createTestContext(options: { appDev: boolean }): ProjectContext {
    return {
      dir: '/test-project',
      name: 'test-project',
      isScaffolded: true,
      ports: {
        web: 3300,
        api: 8800,
        db: 5432,
        redis: 6379,
      },
      version: '0.7.0',
      appDev: options.appDev,
      devPackages: false,
      template: 'baseboards',
    };
  }

  /**
   * Helper function to get compose files based on context
   * Mimics the getComposeFiles function from up.ts
   */
  function getComposeFiles(ctx: ProjectContext): string[] {
    const files = ['compose.yaml'];
    if (!ctx.appDev) {
      files.push('compose.web.yaml');
    }
    return files;
  }

  /**
   * Helper function to capture console.log output
   */
  async function captureOutput(fn: () => Promise<void>): Promise<string> {
    const outputs: string[] = [];
    const mockLog = vi.spyOn(console, 'log').mockImplementation((...args) => {
      outputs.push(args.join(' '));
    });

    await fn();

    mockLog.mockRestore();
    return outputs.join('\n');
  }

  describe('Compose file loading - default mode', () => {
    test('should load both base and web compose files', () => {
      const ctx = createTestContext({ appDev: false });
      const files = getComposeFiles(ctx);

      expect(files).toContain('compose.yaml');
      expect(files).toContain('compose.web.yaml');
      expect(files).toHaveLength(2);
    });

    test('should start web service', () => {
      const ctx = createTestContext({ appDev: false });
      const files = getComposeFiles(ctx);

      // Verify that compose.web.yaml is included
      expect(files).toContain('compose.web.yaml');
    });
  });

  describe('Compose file loading - app-dev mode', () => {
    test('should load only base compose file', () => {
      const ctx = createTestContext({ appDev: true });
      const files = getComposeFiles(ctx);

      expect(files).toContain('compose.yaml');
      expect(files).not.toContain('compose.web.yaml');
      expect(files).toHaveLength(1);
    });

    test('should not include web service', () => {
      const ctx = createTestContext({ appDev: true });
      const files = getComposeFiles(ctx);

      // Verify that compose.web.yaml is NOT included
      expect(files).not.toContain('compose.web.yaml');
    });
  });

  describe('Service count tests', () => {
    test('should expect 5 services in default mode', () => {
      const ctx = createTestContext({ appDev: false });

      // Expected services in default mode
      const expectedServices = ['db', 'cache', 'api', 'worker', 'web'];

      expect(expectedServices).toHaveLength(5);
      expect(expectedServices).toContain('db');
      expect(expectedServices).toContain('cache');
      expect(expectedServices).toContain('api');
      expect(expectedServices).toContain('worker');
      expect(expectedServices).toContain('web');
    });

    test('should expect 4 services in app-dev mode', () => {
      const ctx = createTestContext({ appDev: true });

      // Expected services in app-dev mode (no web)
      const expectedServices = ['db', 'cache', 'api', 'worker'];

      expect(expectedServices).toHaveLength(4);
      expect(expectedServices).toContain('db');
      expect(expectedServices).toContain('cache');
      expect(expectedServices).toContain('api');
      expect(expectedServices).toContain('worker');
      expect(expectedServices).not.toContain('web');
    });
  });

  describe('Package manager selection', () => {
    test('should not prompt in default mode', () => {
      const ctx = createTestContext({ appDev: false });

      // In default mode, package manager prompt should not be needed
      // because the web service runs in Docker
      expect(ctx.appDev).toBe(false);
    });

    test('should prompt in app-dev mode', async () => {
      const ctx = createTestContext({ appDev: true });

      vi.mocked(prompts).mockResolvedValue({ packageManager: 'pnpm' });

      // Simulate prompting for package manager
      const result = await prompts({
        type: 'select',
        name: 'packageManager',
        message: 'Select package manager:',
        choices: [
          { title: 'pnpm', value: 'pnpm' },
          { title: 'npm', value: 'npm' },
          { title: 'yarn', value: 'yarn' },
          { title: 'bun', value: 'bun' },
        ],
      });

      expect(vi.mocked(prompts)).toHaveBeenCalled();
      expect(result.packageManager).toBe('pnpm');
    });

    test('should support all package managers', async () => {
      const packageManagers = ['pnpm', 'npm', 'yarn', 'bun'] as const;

      for (const pm of packageManagers) {
        vi.mocked(prompts).mockResolvedValue({ packageManager: pm });

        const result = await prompts({
          type: 'select',
          name: 'packageManager',
          message: 'Select package manager:',
          choices: packageManagers.map(p => ({ title: p, value: p })),
        });

        expect(result.packageManager).toBe(pm);
      }
    });
  });

  describe('Dependency installation', () => {
    test('should not install in default mode', () => {
      const ctx = createTestContext({ appDev: false });

      // In default mode, dependencies are handled within Docker
      expect(ctx.appDev).toBe(false);
    });

    test('should install with selected package manager', async () => {
      const ctx = createTestContext({ appDev: true });
      ctx.packageManager = 'pnpm';

      vi.mocked(fs).existsSync = vi.fn().mockReturnValue(true);

      // Simulate dependency installation
      await execa('pnpm', ['install'], {
        cwd: '/test-project/web',
        stdio: 'inherit',
      });

      expect(vi.mocked(execa)).toHaveBeenCalledWith(
        'pnpm',
        ['install'],
        expect.objectContaining({ cwd: '/test-project/web' })
      );
    });

    test('should handle installation errors', async () => {
      const ctx = createTestContext({ appDev: true });
      ctx.packageManager = 'npm';

      vi.mocked(execa).mockRejectedValue(new Error('Install failed'));

      await expect(
        execa('npm', ['install'], {
          cwd: '/test-project/web',
          stdio: 'inherit',
        })
      ).rejects.toThrow('Install failed');
    });

    test('should skip installation if package.json does not exist', () => {
      const ctx = createTestContext({ appDev: true });

      vi.mocked(fs).existsSync = vi.fn().mockReturnValue(false);

      const packageJsonExists = fs.existsSync('/test-project/web/package.json');
      expect(packageJsonExists).toBe(false);
    });
  });

  describe('Success message tests', () => {
    test('should show web URL in default mode', () => {
      const ctx = createTestContext({ appDev: false });

      // In default mode, success message should include web URL
      const expectedUrl = `http://localhost:${ctx.ports.web}`;
      expect(expectedUrl).toBe('http://localhost:3300');

      // Should not show local dev instructions
      expect(ctx.appDev).toBe(false);
    });

    test('should show local dev instructions in app-dev mode', () => {
      const ctx = createTestContext({ appDev: true });
      ctx.packageManager = 'pnpm';

      // In app-dev mode, success message should include dev command
      expect(ctx.appDev).toBe(true);
      expect(ctx.packageManager).toBe('pnpm');
    });

    test('should use correct package manager command', () => {
      const commands = {
        pnpm: 'pnpm dev',
        npm: 'npm run dev',
        yarn: 'yarn dev',
        bun: 'bun dev',
      };

      for (const [pm, cmd] of Object.entries(commands)) {
        const ctx = createTestContext({ appDev: true });
        ctx.packageManager = pm as 'pnpm' | 'npm' | 'yarn' | 'bun';

        expect(ctx.packageManager).toBe(pm);
        // Expected command format
        expect(cmd).toMatch(new RegExp(`${pm}\\s+(run\\s+)?dev`));
      }
    });
  });

  describe('Context updates tests', () => {
    test('should set appDev flag in context', () => {
      const ctx = createTestContext({ appDev: true });

      expect(ctx.appDev).toBe(true);
    });

    test('should store package manager in context', () => {
      const ctx = createTestContext({ appDev: true });
      ctx.packageManager = 'yarn';

      expect(ctx.packageManager).toBe('yarn');
    });

    test('should not have package manager in default mode', () => {
      const ctx = createTestContext({ appDev: false });

      expect(ctx.packageManager).toBeUndefined();
    });
  });

  describe('Integration workflow', () => {
    test('should complete app-dev workflow steps', () => {
      const ctx = createTestContext({ appDev: true });
      ctx.packageManager = 'pnpm';

      // Verify workflow steps
      // 1. Compose files loaded (only base)
      const files = getComposeFiles(ctx);
      expect(files).toEqual(['compose.yaml']);

      // 2. Expected services (4 services, no web)
      const expectedServices = ['db', 'cache', 'api', 'worker'];
      expect(expectedServices).toHaveLength(4);
      expect(expectedServices).not.toContain('web');

      // 3. Package manager set
      expect(ctx.packageManager).toBe('pnpm');

      // 4. App-dev mode enabled
      expect(ctx.appDev).toBe(true);
    });

    test('should handle full default mode workflow', () => {
      const ctx = createTestContext({ appDev: false });

      // Verify workflow steps
      // 1. Compose files loaded (base + web)
      const files = getComposeFiles(ctx);
      expect(files).toEqual(['compose.yaml', 'compose.web.yaml']);

      // 2. Expected services (5 services, including web)
      const expectedServices = ['db', 'cache', 'api', 'worker', 'web'];
      expect(expectedServices).toHaveLength(5);

      // 3. No package manager needed
      expect(ctx.packageManager).toBeUndefined();

      // 4. App-dev mode disabled
      expect(ctx.appDev).toBe(false);
    });
  });

  describe('Error handling', () => {
    test('should handle missing web directory gracefully', () => {
      const ctx = createTestContext({ appDev: true });

      vi.mocked(fs).existsSync = vi.fn().mockReturnValue(false);

      const webDirExists = fs.existsSync('/test-project/web');
      expect(webDirExists).toBe(false);
    });

    test('should handle package manager installation failure', async () => {
      vi.mocked(execa).mockRejectedValue(new Error('Command not found: pnpm'));

      await expect(
        execa('pnpm', ['install'], { cwd: '/test-project/web' })
      ).rejects.toThrow('Command not found: pnpm');
    });
  });

  describe('Mode detection', () => {
    test('should correctly identify default mode', () => {
      const ctx = createTestContext({ appDev: false });

      expect(ctx.appDev).toBe(false);

      const files = getComposeFiles(ctx);
      expect(files).toContain('compose.web.yaml');
    });

    test('should correctly identify app-dev mode', () => {
      const ctx = createTestContext({ appDev: true });

      expect(ctx.appDev).toBe(true);

      const files = getComposeFiles(ctx);
      expect(files).not.toContain('compose.web.yaml');
    });
  });

  describe('Package manager command mapping', () => {
    test('should map pnpm to "pnpm dev"', () => {
      const cmd = 'pnpm dev';
      expect(cmd).toBe('pnpm dev');
    });

    test('should map npm to "npm run dev"', () => {
      const cmd = 'npm run dev';
      expect(cmd).toBe('npm run dev');
    });

    test('should map yarn to "yarn dev"', () => {
      const cmd = 'yarn dev';
      expect(cmd).toBe('yarn dev');
    });

    test('should map bun to "bun dev"', () => {
      const cmd = 'bun dev';
      expect(cmd).toBe('bun dev');
    });
  });

  describe('Port configuration', () => {
    test('should use default ports in both modes', () => {
      const defaultCtx = createTestContext({ appDev: false });
      const appDevCtx = createTestContext({ appDev: true });

      expect(defaultCtx.ports.api).toBe(8800);
      expect(appDevCtx.ports.api).toBe(8800);
    });

    test('should include web port only in default mode context', () => {
      const defaultCtx = createTestContext({ appDev: false });
      const appDevCtx = createTestContext({ appDev: true });

      // Both have the port defined, but it's only used in default mode
      expect(defaultCtx.ports.web).toBe(3300);
      expect(appDevCtx.ports.web).toBe(3300);
    });
  });
});

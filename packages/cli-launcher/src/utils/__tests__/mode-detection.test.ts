import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs-extra';
import path from 'path';
import os from 'os';
import { exec } from 'child_process';
import { promisify } from 'util';
import { detectProjectMode, saveProjectMode } from '../mode-detection.js';

const execAsync = promisify(exec);

// Mock child_process exec
vi.mock('child_process', () => ({
  exec: vi.fn(),
}));

describe('Mode Detection', () => {
  let testDir: string;

  beforeEach(async () => {
    // Create a temporary test directory
    testDir = await fs.mkdtemp(path.join(os.tmpdir(), 'mode-detection-test-'));
    vi.clearAllMocks();
  });

  afterEach(async () => {
    // Clean up test directory
    await fs.remove(testDir);
  });

  describe('detectProjectMode', () => {
    test('should detect default mode when web container is running', async () => {
      // Mock docker compose ps to return 'web' service
      const mockExec = vi.mocked(exec);
      mockExec.mockImplementation(((
        cmd: string,
        options: any,
        callback?: (error: Error | null, stdout: any, stderr: any) => void
      ) => {
        if (callback) {
          callback(null, { stdout: 'web\napi\ndb\nredis\n', stderr: '' }, '');
        }
        return {} as any;
      }) as any);

      const mode = await detectProjectMode(testDir);
      expect(mode).toBe('default');
    });

    test('should fall through to other methods when docker command fails', async () => {
      // Mock docker compose ps to fail
      const mockExec = vi.mocked(exec);
      mockExec.mockImplementation(((
        cmd: string,
        options: any,
        callback?: (error: Error | null, stdout: any, stderr: any) => void
      ) => {
        if (callback) {
          callback(new Error('Docker not running'), { stdout: '', stderr: '' }, '');
        }
        return {} as any;
      }) as any);

      // Create .baseboards-mode file with 'app-dev'
      await fs.writeFile(path.join(testDir, '.baseboards-mode'), 'app-dev', 'utf-8');

      const mode = await detectProjectMode(testDir);
      expect(mode).toBe('app-dev');
    });

    test('should read mode from .baseboards-mode file (default)', async () => {
      // Mock docker to not include web service
      const mockExec = vi.mocked(exec);
      mockExec.mockImplementation(((
        cmd: string,
        options: any,
        callback?: (error: Error | null, stdout: any, stderr: any) => void
      ) => {
        if (callback) {
          callback(null, { stdout: 'api\ndb\nredis\n', stderr: '' }, '');
        }
        return {} as any;
      }) as any);

      // Create .baseboards-mode file with 'default'
      await fs.writeFile(path.join(testDir, '.baseboards-mode'), 'default', 'utf-8');

      const mode = await detectProjectMode(testDir);
      expect(mode).toBe('default');
    });

    test('should read mode from .baseboards-mode file (app-dev)', async () => {
      // Mock docker to not include web service
      const mockExec = vi.mocked(exec);
      mockExec.mockImplementation(((
        cmd: string,
        options: any,
        callback?: (error: Error | null, stdout: any, stderr: any) => void
      ) => {
        if (callback) {
          callback(null, { stdout: 'api\ndb\nredis\n', stderr: '' }, '');
        }
        return {} as any;
      }) as any);

      // Create .baseboards-mode file with 'app-dev'
      await fs.writeFile(path.join(testDir, '.baseboards-mode'), 'app-dev', 'utf-8');

      const mode = await detectProjectMode(testDir);
      expect(mode).toBe('app-dev');
    });

    test('should handle .baseboards-mode file with whitespace', async () => {
      // Mock docker to not include web service
      const mockExec = vi.mocked(exec);
      mockExec.mockImplementation(((
        cmd: string,
        options: any,
        callback?: (error: Error | null, stdout: any, stderr: any) => void
      ) => {
        if (callback) {
          callback(null, { stdout: 'api\ndb\nredis\n', stderr: '' }, '');
        }
        return {} as any;
      }) as any);

      // Create .baseboards-mode file with whitespace
      await fs.writeFile(path.join(testDir, '.baseboards-mode'), '  app-dev  \n', 'utf-8');

      const mode = await detectProjectMode(testDir);
      expect(mode).toBe('app-dev');
    });

    test('should ignore invalid mode in .baseboards-mode file', async () => {
      // Mock docker to not include web service
      const mockExec = vi.mocked(exec);
      mockExec.mockImplementation(((
        cmd: string,
        options: any,
        callback?: (error: Error | null, stdout: any, stderr: any) => void
      ) => {
        if (callback) {
          callback(null, { stdout: 'api\ndb\nredis\n', stderr: '' }, '');
        }
        return {} as any;
      }) as any);

      // Create .baseboards-mode file with invalid content
      await fs.writeFile(path.join(testDir, '.baseboards-mode'), 'invalid-mode', 'utf-8');

      // Should fall through to web/node_modules check
      const mode = await detectProjectMode(testDir);
      expect(mode).toBe('default'); // Fallback to default
    });

    test('should detect app-dev mode when web/node_modules exists', async () => {
      // Mock docker to not include web service
      const mockExec = vi.mocked(exec);
      mockExec.mockImplementation(((
        cmd: string,
        options: any,
        callback?: (error: Error | null, stdout: any, stderr: any) => void
      ) => {
        if (callback) {
          callback(null, { stdout: 'api\ndb\nredis\n', stderr: '' }, '');
        }
        return {} as any;
      }) as any);

      // Create web/node_modules directory
      const webNodeModules = path.join(testDir, 'web', 'node_modules');
      await fs.ensureDir(webNodeModules);

      const mode = await detectProjectMode(testDir);
      expect(mode).toBe('app-dev');
    });

    test('should default to default mode when no indicators found', async () => {
      // Mock docker to not include web service
      const mockExec = vi.mocked(exec);
      mockExec.mockImplementation(((
        cmd: string,
        options: any,
        callback?: (error: Error | null, stdout: any, stderr: any) => void
      ) => {
        if (callback) {
          callback(null, { stdout: 'api\ndb\nredis\n', stderr: '' }, '');
        }
        return {} as any;
      }) as any);

      // No .baseboards-mode file, no web/node_modules
      const mode = await detectProjectMode(testDir);
      expect(mode).toBe('default');
    });

    test('should prioritize running web container over mode file', async () => {
      // Mock docker compose ps to return 'web' service
      const mockExec = vi.mocked(exec);
      mockExec.mockImplementation(((
        cmd: string,
        options: any,
        callback?: (error: Error | null, stdout: any, stderr: any) => void
      ) => {
        if (callback) {
          callback(null, { stdout: 'web\napi\ndb\nredis\n', stderr: '' }, '');
        }
        return {} as any;
      }) as any);

      // Create .baseboards-mode file with 'app-dev' (conflicting)
      await fs.writeFile(path.join(testDir, '.baseboards-mode'), 'app-dev', 'utf-8');

      const mode = await detectProjectMode(testDir);
      // Should prioritize actual running container
      expect(mode).toBe('default');
    });

    test('should prioritize mode file over web/node_modules', async () => {
      // Mock docker to not include web service
      const mockExec = vi.mocked(exec);
      mockExec.mockImplementation(((
        cmd: string,
        options: any,
        callback?: (error: Error | null, stdout: any, stderr: any) => void
      ) => {
        if (callback) {
          callback(null, { stdout: 'api\ndb\nredis\n', stderr: '' }, '');
        }
        return {} as any;
      }) as any);

      // Create .baseboards-mode file with 'default'
      await fs.writeFile(path.join(testDir, '.baseboards-mode'), 'default', 'utf-8');

      // Create web/node_modules directory (conflicting)
      const webNodeModules = path.join(testDir, 'web', 'node_modules');
      await fs.ensureDir(webNodeModules);

      const mode = await detectProjectMode(testDir);
      // Should prioritize mode file
      expect(mode).toBe('default');
    });
  });

  describe('saveProjectMode', () => {
    test('should save default mode to .baseboards-mode file', async () => {
      await saveProjectMode(testDir, 'default');

      const modeFile = path.join(testDir, '.baseboards-mode');
      expect(await fs.pathExists(modeFile)).toBe(true);

      const content = await fs.readFile(modeFile, 'utf-8');
      expect(content).toBe('default');
    });

    test('should save app-dev mode to .baseboards-mode file', async () => {
      await saveProjectMode(testDir, 'app-dev');

      const modeFile = path.join(testDir, '.baseboards-mode');
      expect(await fs.pathExists(modeFile)).toBe(true);

      const content = await fs.readFile(modeFile, 'utf-8');
      expect(content).toBe('app-dev');
    });

    test('should overwrite existing .baseboards-mode file', async () => {
      // Create initial mode file
      await fs.writeFile(path.join(testDir, '.baseboards-mode'), 'default', 'utf-8');

      // Overwrite with new mode
      await saveProjectMode(testDir, 'app-dev');

      const modeFile = path.join(testDir, '.baseboards-mode');
      const content = await fs.readFile(modeFile, 'utf-8');
      expect(content).toBe('app-dev');
    });

    test('should create .baseboards-mode file if it does not exist', async () => {
      const modeFile = path.join(testDir, '.baseboards-mode');
      expect(await fs.pathExists(modeFile)).toBe(false);

      await saveProjectMode(testDir, 'default');

      expect(await fs.pathExists(modeFile)).toBe(true);
    });
  });

  describe('Integration', () => {
    test('should correctly round-trip save and detect mode', async () => {
      // Mock docker to not affect result
      const mockExec = vi.mocked(exec);
      mockExec.mockImplementation(((
        cmd: string,
        options: any,
        callback?: (error: Error | null, stdout: any, stderr: any) => void
      ) => {
        if (callback) {
          callback(null, { stdout: 'api\ndb\nredis\n', stderr: '' }, '');
        }
        return {} as any;
      }) as any);

      // Save mode as default
      await saveProjectMode(testDir, 'default');
      let detectedMode = await detectProjectMode(testDir);
      expect(detectedMode).toBe('default');

      // Save mode as app-dev
      await saveProjectMode(testDir, 'app-dev');
      detectedMode = await detectProjectMode(testDir);
      expect(detectedMode).toBe('app-dev');
    });
  });
});

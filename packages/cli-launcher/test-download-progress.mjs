#!/usr/bin/env node

/**
 * Test script for template download with progress indicator
 * Run this from packages/cli-launcher directory
 */

import { downloadTemplate, clearCache } from './src/utils/template-downloader.ts';
import path from 'path';
import fs from 'fs-extra';

async function testDownload() {
  console.log('Testing template download with progress indicator...\n');

  const testDir = '/tmp/test-template-download';

  // Clean up test directory
  await fs.remove(testDir);

  try {
    console.log('='.repeat(60));
    console.log('Test 1: Download basic template (first time)');
    console.log('='.repeat(60));
    await downloadTemplate('basic', '0.8.0', path.join(testDir, 'basic-1'));
    console.log('✅ Test 1 passed\n');

    console.log('='.repeat(60));
    console.log('Test 2: Download basic template again (should use cache)');
    console.log('='.repeat(60));
    await downloadTemplate('basic', '0.8.0', path.join(testDir, 'basic-2'));
    console.log('✅ Test 2 passed\n');

    console.log('='.repeat(60));
    console.log('Test 3: Clear cache and download again');
    console.log('='.repeat(60));
    await clearCache();
    console.log('Cache cleared');
    await downloadTemplate('basic', '0.8.0', path.join(testDir, 'basic-3'));
    console.log('✅ Test 3 passed\n');

    console.log('🎉 All tests passed!');
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    process.exit(1);
  }
}

testDownload();

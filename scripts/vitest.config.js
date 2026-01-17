/// <reference types="vitest" />
const { defineConfig } = require('vitest/config');

module.exports = defineConfig({
  test: {
    globals: true,
    testTimeout: 30000, // Longer timeout for exec tests
  },
});

module.exports = {
  root: true,
  env: {
    browser: true,
    es2020: true,
    node: true,
  },
  extends: [
    'eslint:recommended',
  ],
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: 'module',
  },
  rules: {
    // Basic JavaScript rules
    'no-console': 'warn',
    'no-unused-vars': 'warn',
  },
  overrides: [
    // TypeScript files
    {
      files: ['**/*.ts', '**/*.tsx'],
      parser: '@typescript-eslint/parser',
      plugins: ['@typescript-eslint'],
      extends: [
        'eslint:recommended',
      ],
      rules: {
        // Basic TypeScript rules without extending recommended
        '@typescript-eslint/no-unused-vars': 'warn',
        'no-unused-vars': 'off', // Turn off base rule for TS files
        '@typescript-eslint/no-explicit-any': 'warn',
        '@typescript-eslint/no-var-requires': 'error',
      },
    },
    // React/JSX files
    {
      files: ['**/*.tsx', '**/*.jsx'],
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
      settings: {
        react: {
          version: 'detect',
        },
      },
    },
    // Next.js app specific rules
    {
      files: ['apps/example-nextjs/**/*'],
      extends: ['next/core-web-vitals'],
    },
  ],
  ignorePatterns: [
    'node_modules/',
    'dist/',
    '.next/',
    '.turbo/',
    '*.config.js',
    '*.config.ts',
    'packages/backend/**/*', // Skip Python backend
  ],
};
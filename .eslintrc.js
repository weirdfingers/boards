module.exports = {
  root: true,
  env: {
    browser: true,
    es2020: true,
    node: true,
  },
  extends: ["eslint:recommended"],
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: "module",
  },
  rules: {
    // Basic JavaScript rules
    "no-console": "off",
    "no-unused-vars": "warn",
  },
  overrides: [
    // TypeScript files
    {
      files: ["**/*.ts", "**/*.tsx"],
      parser: "@typescript-eslint/parser",
      plugins: ["@typescript-eslint"],
      extends: ["eslint:recommended"],
      rules: {
        // Basic TypeScript rules without extending recommended
        "@typescript-eslint/no-unused-vars": "warn",
        "no-unused-vars": "off", // Turn off base rule for TS files
        "@typescript-eslint/no-explicit-any": "warn",
        "@typescript-eslint/no-var-requires": "error",
      },
    },
    // React/JSX files
    {
      files: ["**/*.tsx", "**/*.jsx"],
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
      settings: {
        react: {
          version: "detect",
        },
      },
    },
    // Next.js app specific rules
    {
      files: ["apps/example-nextjs/**/*"],
      extends: ["next/core-web-vitals"],
      rules: {
        // Prevent direct GraphQL/urql usage in example apps
        // GraphQL should be abstracted behind hooks from @weirdfingers/boards
        "no-restricted-imports": [
          "error",
          {
            paths: [
              {
                name: "urql",
                message:
                  "Do not import urql directly in example apps. Use hooks from @weirdfingers/boards instead (e.g., useBoards, useBoard, useGenerators).",
              },
              {
                name: "@weirdfingers/boards/graphql/operations",
                message:
                  "Do not import GraphQL operations directly in example apps. Use hooks from @weirdfingers/boards instead.",
              },
            ],
            patterns: [
              {
                group: ["**/graphql/*"],
                message:
                  "Do not import GraphQL code directly in example apps. Use hooks from @weirdfingers/boards instead.",
              },
            ],
          },
        ],
      },
    },
  ],
  ignorePatterns: [
    "node_modules/",
    "dist/",
    ".next/",
    ".turbo/",
    "*.config.js",
    "*.config.ts",
    "packages/backend/**/*", // Skip Python backend
  ],
};

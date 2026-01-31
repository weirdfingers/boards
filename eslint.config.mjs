// Flat config that loads the legacy .eslintrc.js
// This stops ESLint from walking up to parent directories.
import { FlatCompat } from "@eslint/eslintrc";
import js from "@eslint/js";

const compat = new FlatCompat({
  baseDirectory: import.meta.dirname,
  recommendedConfig: js.configs.recommended,
});

export default compat.config({
  extends: ["./.eslintrc.js"],
});

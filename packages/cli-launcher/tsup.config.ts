import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/index.ts"],
  format: ["esm"],
  dts: true,
  clean: true,
  shims: false,
  bundle: true,
  splitting: false,
  sourcemap: true,
  minify: false,
  target: "node20",
  outDir: "dist",
});

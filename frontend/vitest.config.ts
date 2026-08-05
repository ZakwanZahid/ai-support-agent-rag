import path from "node:path";

import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    // Mirrors the "@/*" path alias from tsconfig.json.
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  // esbuild handles the JSX transform, so @vitejs/plugin-react is unnecessary
  // here. It also brings its own copy of Vite, whose plugin types conflict
  // with the one Next installs.
  esbuild: { jsx: "automatic" },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    // Playwright specs live in tests/e2e and are run by Playwright, not Vitest.
    include: ["tests/unit/**/*.test.ts", "tests/unit/**/*.test.tsx"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json-summary", "html"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        // Presentational primitives and barrels carry no logic worth asserting.
        "src/components/ui/**",
        "src/**/index.ts",
        "src/types/**",
      ],
    },
  },
});

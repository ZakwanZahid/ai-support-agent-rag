import { defineConfig, devices } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:3000";

/**
 * The end-to-end suite drives the real product against a real API: it signs
 * up, uploads a document, waits for preparation, and asks a question. That
 * means it needs the backend and its database running, and it will spend
 * OpenAI credit on embeddings and one chat completion.
 *
 * Start the backend first, then: npm run test:e2e
 */
export default defineConfig({
  testDir: "./tests/e2e",
  // Preparation involves an embedding round trip, so these are slower than
  // typical UI specs.
  timeout: 120_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : [["list"]],
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  // Reuses an already-running dev server locally; starts one in CI.
  webServer: {
    command: "npm run dev",
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});

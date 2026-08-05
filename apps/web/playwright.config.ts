import { defineConfig, devices } from "@playwright/test";

// E2E runs against a production build of the web app. NEXT_PUBLIC_* vars are
// inlined at build time, so the web server BUILDS with a same-origin mock base
// (/mock-api/v1) served by the app's own route handlers, then starts. This lets
// E2E run with clearly-labelled synthetic fixtures and no Python API.
const PORT = Number(process.env.E2E_PORT ?? 3199);

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  // The app must be built beforehand with NEXT_PUBLIC_API_BASE=/mock-api/v1
  // (NEXT_PUBLIC_* is inlined at build time). E2E only starts the server here to
  // keep startup fast and robust; see apps/web/README for the exact commands.
  webServer: {
    command: `npx next start -p ${PORT}`,
    url: `http://localhost:${PORT}`,
    timeout: 120_000,
    reuseExistingServer: false,
    env: {
      NEXT_PUBLIC_API_BASE: "/mock-api/v1",
    },
  },
});

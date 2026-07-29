import { defineConfig, devices } from "@playwright/test";

/**
 * Three independent backend+frontend pairs, so tests never share mutable
 * state across scenarios and never touch OpenAI:
 *
 *  - primary: seeded with dataset items, prompt versions, and one
 *    pre-seeded COMPLETED experiment (see backend/scripts/e2e_seed.py).
 *    Used by every scenario except the datasets empty/error checks.
 *  - datasets-empty: migrated but otherwise empty database. Used only to
 *    exercise the datasets page's empty-state UI.
 *  - datasets-error: frontend only, pointed at a backend port nothing
 *    listens on, so its server-side fetches fail deterministically. Used
 *    only to exercise the datasets page's error-state UI.
 *
 * All three use a real production build (`next build` && `next start`),
 * one per pair, each with its own `distDir` (see next.config.ts) since
 * Next.js inlines NEXT_PUBLIC_* env vars at compile time and each pair
 * needs a different API base URL. `next dev`'s hot-reload client depends
 * on a websocket handshake that this environment can't complete, which
 * silently prevents React from ever hydrating -- so dev mode is not an
 * option here. One consequence: Next.js redacts thrown Server Component
 * error messages in production, so the datasets-error test asserts on the
 * generic (but still readable) message it actually renders, not the
 * original ApiError text.
 */

const PRIMARY_BACKEND_PORT = 8000;
const PRIMARY_FRONTEND_PORT = 3000;
const EMPTY_BACKEND_PORT = 8001;
const EMPTY_FRONTEND_PORT = 3001;
const ERROR_FRONTEND_PORT = 3002;
const ERROR_BACKEND_PORT = 8002; // intentionally never started

const PRIMARY_BASE_URL = `http://127.0.0.1:${PRIMARY_FRONTEND_PORT}`;
const EMPTY_BASE_URL = `http://127.0.0.1:${EMPTY_FRONTEND_PORT}`;
const ERROR_BASE_URL = `http://127.0.0.1:${ERROR_FRONTEND_PORT}`;

export const PRIMARY_BACKEND_URL = `http://127.0.0.1:${PRIMARY_BACKEND_PORT}`;

const BACKEND_DIR = "../backend";
const IS_CI = !!process.env.CI;

export default defineConfig({
  testDir: "./e2e",
  timeout: 45_000,
  fullyParallel: false,
  workers: 1,
  forbidOnly: IS_CI,
  retries: IS_CI ? 1 : 0,
  reporter: IS_CI
    ? [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]]
    : [["list"]],
  use: {
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "primary",
      use: { ...devices["Desktop Chrome"], baseURL: PRIMARY_BASE_URL },
      testIgnore: [/datasets-empty\.spec\.ts$/, /datasets-error\.spec\.ts$/],
    },
    {
      name: "datasets-empty",
      use: { ...devices["Desktop Chrome"], baseURL: EMPTY_BASE_URL },
      testMatch: /datasets-empty\.spec\.ts$/,
    },
    {
      name: "datasets-error",
      use: { ...devices["Desktop Chrome"], baseURL: ERROR_BASE_URL },
      testMatch: /datasets-error\.spec\.ts$/,
    },
  ],
  webServer: [
    {
      command:
        "rm -rf .e2e-primary && mkdir -p .e2e-primary && " +
        "./.venv/bin/python -m alembic upgrade head && " +
        "./.venv/bin/python scripts/e2e_seed.py && " +
        `./.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port ${PRIMARY_BACKEND_PORT}`,
      cwd: BACKEND_DIR,
      url: `http://127.0.0.1:${PRIMARY_BACKEND_PORT}/health`,
      timeout: 120_000,
      reuseExistingServer: !IS_CI,
      env: {
        DATABASE_URL: "sqlite:///.e2e-primary/primary.db",
        OPENAI_API_KEY: "",
        CORS_ALLOWED_ORIGINS: PRIMARY_BASE_URL,
        MAX_RUNS_PER_EXPERIMENT: "30",
      },
    },
    {
      command:
        "rm -rf .e2e-empty && mkdir -p .e2e-empty && " +
        "./.venv/bin/python -m alembic upgrade head && " +
        `./.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port ${EMPTY_BACKEND_PORT}`,
      cwd: BACKEND_DIR,
      url: `http://127.0.0.1:${EMPTY_BACKEND_PORT}/health`,
      timeout: 120_000,
      reuseExistingServer: !IS_CI,
      env: {
        DATABASE_URL: "sqlite:///.e2e-empty/empty.db",
        OPENAI_API_KEY: "",
        CORS_ALLOWED_ORIGINS: EMPTY_BASE_URL,
      },
    },
    {
      command:
        "./node_modules/.bin/next build && " +
        `./node_modules/.bin/next start -p ${PRIMARY_FRONTEND_PORT}`,
      cwd: ".",
      url: PRIMARY_BASE_URL,
      timeout: 300_000,
      reuseExistingServer: !IS_CI,
      env: {
        NEXT_PUBLIC_API_BASE_URL: PRIMARY_BACKEND_URL,
        NEXT_E2E_DIST_DIR: ".next-e2e-primary",
      },
    },
    {
      command:
        "./node_modules/.bin/next build && " +
        `./node_modules/.bin/next start -p ${EMPTY_FRONTEND_PORT}`,
      cwd: ".",
      url: EMPTY_BASE_URL,
      timeout: 300_000,
      reuseExistingServer: !IS_CI,
      env: {
        NEXT_PUBLIC_API_BASE_URL: `http://127.0.0.1:${EMPTY_BACKEND_PORT}`,
        NEXT_E2E_DIST_DIR: ".next-e2e-empty",
      },
    },
    {
      command:
        "./node_modules/.bin/next build && " +
        `./node_modules/.bin/next start -p ${ERROR_FRONTEND_PORT}`,
      cwd: ".",
      url: ERROR_BASE_URL,
      timeout: 300_000,
      reuseExistingServer: !IS_CI,
      env: {
        NEXT_PUBLIC_API_BASE_URL: `http://127.0.0.1:${ERROR_BACKEND_PORT}`,
        NEXT_E2E_DIST_DIR: ".next-e2e-error",
      },
    },
  ],
});

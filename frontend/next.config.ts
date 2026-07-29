import type { NextConfig } from "next";

// Playwright runs several `next dev` instances from this same directory in
// parallel (see frontend/playwright.config.ts), each needing a distinct API
// base URL. Next.js's dev server takes an exclusive lock on its build
// output directory, so each instance needs its own `distDir` to coexist.
const nextConfig: NextConfig = {
  ...(process.env.NEXT_E2E_DIST_DIR ? { distDir: process.env.NEXT_E2E_DIST_DIR } : {}),
};

export default nextConfig;

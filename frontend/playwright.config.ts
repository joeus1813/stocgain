import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  use: {
    baseURL: process.env.TEST_WEB_BASE_URL ?? "http://localhost:3050",
    // Match Compose's IPv4 loopback binding, avoiding unrelated IPv6 listeners.
    launchOptions: { args: ["--host-resolver-rules=MAP localhost 127.0.0.1"] },
  },
});

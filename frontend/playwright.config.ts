import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  use: {
    baseURL: "http://localhost:3000",
    // Match Compose's IPv4 loopback binding, avoiding unrelated IPv6 listeners.
    launchOptions: { args: ["--host-resolver-rules=MAP localhost 127.0.0.1"] },
  },
});

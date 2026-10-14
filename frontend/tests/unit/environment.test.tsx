import { execFileSync } from "node:child_process";
import {
  mkdtempSync,
  mkdirSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import os from "node:os";
import path from "node:path";
import { expect, it } from "vitest";

it("loads the root environment after Next has cached the frontend environment", () => {
  const directory = mkdtempSync(path.join(os.tmpdir(), "stocgain-env-"));
  const frontend = path.join(directory, "frontend");
  mkdirSync(frontend);
  symlinkSync(
    path.resolve("node_modules"),
    path.join(frontend, "node_modules"),
    "dir",
  );
  writeFileSync(
    path.join(directory, ".env"),
    "NEXT_PUBLIC_API_BASE_URL=http://fixture.invalid/api/v1\n",
  );
  const configPath = path.resolve("next.config.ts");
  try {
    const result = execFileSync(
      process.execPath,
      [
        "-e",
        `
      const { loadEnvConfig } = require('@next/env');
      const { transpileConfig } = require('next/dist/build/next-config-ts/transpile-config.js');
      (async () => {
      process.chdir(${JSON.stringify(frontend)});
      loadEnvConfig(process.cwd());
      const { default: config } = await transpileConfig({ nextConfigPath: ${JSON.stringify(configPath)}, dir: process.cwd() });
      if (typeof config === 'function') config('phase-development-server');
      console.log(process.env.NEXT_PUBLIC_API_BASE_URL);
      })();
    `,
      ],
      { encoding: "utf8" },
    );
    expect(result.trim()).toBe("http://fixture.invalid/api/v1");
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

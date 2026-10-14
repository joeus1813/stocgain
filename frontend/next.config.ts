import type { NextConfig } from "next";
import { PHASE_DEVELOPMENT_SERVER } from "next/constants";
import { loadEnvConfig } from "@next/env";
import path from "node:path";

export default function nextConfig(phase: string): NextConfig {
  // Next has already loaded frontend/.env; explicitly reload the shared root.
  loadEnvConfig(
    path.resolve(process.cwd(), ".."),
    phase === PHASE_DEVELOPMENT_SERVER,
    console,
    true,
  );
  return { output: "standalone" };
}

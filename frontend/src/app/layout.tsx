import type { Metadata } from "next";
import { Suspense, type ReactNode } from "react";
import { Inter, JetBrains_Mono } from "next/font/google";
import { Providers } from "./providers";
import { AppShell } from "@/components/layout/app-shell";
import "@/styles/globals.css";
const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });
export const metadata: Metadata = {
  title: {
    default: "stocgain. — Inventory intelligence",
    template: "%s | stocgain.",
  },
  description:
    "Predictive Retail Inventory Intelligence Platform. Predict stockouts. Replenish smarter.",
};
export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${mono.variable}`}>
        <Providers>
          <Suspense fallback={<div className="loading">Loading stocgain…</div>}>
            <AppShell>{children}</AppShell>
          </Suspense>
        </Providers>
      </body>
    </html>
  );
}

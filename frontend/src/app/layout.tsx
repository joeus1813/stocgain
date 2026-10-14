import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Providers } from "./providers";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "stocgain. — Inventory overview",
  description:
    "Predictive Retail Inventory Intelligence Platform. Predict stockouts. Replenish smarter.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header>
          <span className="dataset-badge">Simulated Retail Dataset</span>
        </header>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

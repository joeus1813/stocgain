import { HealthStatus } from "@/components/health-status";
import { OverviewKpis } from "@/components/overview-kpis";

export default function Home() {
  return (
    <main>
      <h1>stocgain.</h1>
      <p>Predict stockouts. Replenish smarter.</p>
      <OverviewKpis />
      <details>
        <summary>Service health</summary>
        <HealthStatus />
      </details>
    </main>
  );
}

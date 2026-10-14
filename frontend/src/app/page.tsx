import { HealthStatus } from "@/components/health-status";

export default function Home() {
  return (
    <main>
      <h1>stocgain.</h1>
      <p>Predict stockouts. Replenish smarter.</p>
      <h2>Service health</h2>
      <p>
        Development foundation — checks the real API and database connection.
      </p>
      <HealthStatus />
    </main>
  );
}

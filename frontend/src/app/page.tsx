import { HealthStatus } from "@/components/health-status";

export default function Home() {
  return (
    <main>
      <h1>StockSense service health</h1>
      <p>
        Development foundation — checks the real API and database connection.
      </p>
      <HealthStatus />
    </main>
  );
}

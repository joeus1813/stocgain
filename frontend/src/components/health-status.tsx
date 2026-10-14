"use client";

import { useQuery } from "@tanstack/react-query";
import type { components } from "@/lib/api/schema";

type HealthResponse = components["schemas"]["HealthResponse"];

async function fetchHealth(signal: AbortSignal): Promise<HealthResponse> {
  const baseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
  const response = await fetch(`${baseUrl.replace(/\/$/, "")}/health`, {
    signal,
  });
  if (!response.ok)
    throw new Error(`Health request failed (${response.status})`);
  return response.json() as Promise<HealthResponse>;
}

export function HealthStatus() {
  const query = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => fetchHealth(signal),
    retry: false,
  });

  if (query.isPending) return <p role="status">Checking API and database…</p>;
  if (query.isError)
    return (
      <div role="alert">
        <p>Unable to reach the API. Start the backend with make api.</p>
        <button
          onClick={() => void query.refetch()}
          disabled={query.isFetching}
        >
          Retry
        </button>
      </div>
    );
  return (
    <div>
      <p role="status">
        API: {query.data.status} · Database: {query.data.database}
      </p>
      {query.data.database === "unavailable" && (
        <p>Start PostgreSQL with make db-up, then retry.</p>
      )}
      <button onClick={() => void query.refetch()} disabled={query.isFetching}>
        {query.isFetching ? "Checking…" : "Retry"}
      </button>
    </div>
  );
}

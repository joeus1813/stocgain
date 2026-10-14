import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { HealthStatus } from "@/components/health-status";

function renderHealth() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <HealthStatus />
    </QueryClientProvider>,
  );
}

describe("real API health client", () => {
  it("displays health fields received from the API", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            status: "ok",
            database: "unavailable",
            analytics_ready: false,
            current_run_id: null,
            version: "1.0.0",
          }),
        ),
      ),
    );
    renderHealth();
    expect(
      await screen.findByText("API: ok · Database: unavailable"),
    ).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/health",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it("shows loading until the request completes", () => {
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(() => {})));
    renderHealth();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Checking API and database",
    );
  });

  it("retries a failed request when the user clicks Retry", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockRejectedValueOnce(new Error("Network unavailable"))
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              status: "ok",
              database: "ok",
              analytics_ready: false,
              current_run_id: null,
              version: "1.0.0",
            }),
          ),
        ),
    );
    renderHealth();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Unable to reach the API",
    );
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(
      await screen.findByText("API: ok · Database: ok"),
    ).toBeInTheDocument();
  });
});

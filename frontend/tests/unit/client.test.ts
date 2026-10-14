import { it, expect, vi, afterEach } from "vitest";
import { request, ApiError } from "@/lib/api/client";
afterEach(() => vi.unstubAllGlobals());
it("preserves not-ready errors and cancellation", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: { code: "ANALYTICS_NOT_READY", message: "Run analytics" },
        }),
        { status: 503 },
      ),
    ),
  );
  await expect(request("/overview/summary")).rejects.toMatchObject({
    code: "ANALYTICS_NOT_READY",
    status: 503,
  });
  const error = new DOMException("Aborted", "AbortError");
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(error));
  await expect(request("/meta")).rejects.toBe(error);
});
it("network failure gives a useful message", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockRejectedValue(new TypeError("fetch failed")),
  );
  await expect(request("/meta")).rejects.toBeInstanceOf(ApiError);
});

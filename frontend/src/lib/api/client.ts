import type { components } from "./schema";
export type Schema<K extends keyof components["schemas"]> =
  components["schemas"][K];
export const apiBase = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"
).replace(/\/$/, "");
export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export async function request<T>(
  path: string,
  signal?: AbortSignal,
  body?: unknown,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBase}${path}`, {
      signal,
      ...(body === undefined
        ? {}
        : {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          }),
    });
  } catch (e) {
    if (
      typeof e === "object" &&
      e !== null &&
      "name" in e &&
      e.name === "AbortError"
    )
      throw e;
    throw new ApiError(
      "NETWORK_ERROR",
      "Unable to reach the API. Check your connection and start the backend with make api.",
      0,
    );
  }
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new ApiError(
      data?.error?.code ?? "REQUEST_FAILED",
      data?.error?.message ?? "Unable to load this information.",
      response.status,
    );
  }
  return response.json() as Promise<T>;
}

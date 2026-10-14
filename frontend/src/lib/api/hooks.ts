"use client";
import { useQuery } from "@tanstack/react-query";
import { request, type Schema } from "./client";
export function useMeta() {
  return useQuery({
    queryKey: ["meta"],
    queryFn: ({ signal }) => request<Schema<"Meta">>("/meta", signal),
    staleTime: 30000,
    retry: 1,
  });
}
export function useApi<T>(path: string) {
  const meta = useMeta();
  return useQuery({
    queryKey: [path, meta.data?.run?.run_id],
    enabled: !meta.isPending,
    queryFn: ({ signal }) => request<T>(path, signal),
    staleTime: 30000,
    retry: 1,
  });
}

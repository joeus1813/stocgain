"use client";
import type { ReactNode } from "react";
import { useApi } from "@/lib/api/hooks";
import { Loading, ErrorState } from "./ui";
export function QueryPanel<T>({
  path,
  children,
}: {
  path: string;
  children: (data: T) => ReactNode;
}) {
  const q = useApi<T>(path);
  if (q.isPending) return <Loading />;
  if (q.isError)
    return <ErrorState error={q.error} retry={() => void q.refetch()} />;
  return children(q.data);
}

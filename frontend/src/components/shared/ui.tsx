"use client";
import type { ReactNode } from "react";
import Link from "next/link";
import { ApiError } from "@/lib/api/client";
import { formatLabel, formatProbability, formatCount } from "@/lib/format";
import { definitions } from "@/lib/definitions";
export function Loading({ label = "Loading analytics…" }: { label?: string }) {
  return (
    <div className="loading" role="status">
      <span>{label}</span>
      <div className="skeleton" />
      <div className="skeleton" />
    </div>
  );
}
export function ErrorState({
  error,
  retry,
}: {
  error: Error;
  retry: () => void;
}) {
  return (
    <div className="error-state" role="alert">
      <h3>
        {error instanceof ApiError && error.code === "ANALYTICS_NOT_READY"
          ? "Analytics are not ready"
          : "Unable to load this section"}
      </h3>
      <p>{error.message}</p>
      {error instanceof ApiError && error.code === "ANALYTICS_NOT_READY" && (
        <p>
          Run <code>make analytics</code> to compute the dataset.
        </p>
      )}
      <small>{error instanceof ApiError ? error.code : "REQUEST_FAILED"}</small>
      <button onClick={retry}>Retry</button>
    </div>
  );
}
export function Empty({
  title = "No positions match these filters",
  children,
}: {
  title?: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      <p>Change the scope or reset filters to continue.</p>
      {children}
    </div>
  );
}
export function Card({
  title,
  subtitle,
  children,
  actions,
  className = "",
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card ${className}`} aria-label={title}>
      <div className="card-heading">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}
export function Tier({ tier }: { tier: string }) {
  return (
    <span className={`tier tier-${tier}`}>
      <i />
      {formatLabel(tier)}
    </span>
  );
}
export function Probability({
  value,
  tier = "low",
}: {
  value: number;
  tier?: string;
}) {
  return (
    <span
      className={`probability tier-${tier}`}
      title={definitions.probability}
    >
      <span className="meter">
        <i style={{ width: `${value * 100}%` }} />
      </span>
      {formatProbability(value)}
    </span>
  );
}
export function Action({
  action,
  units,
}: {
  action: string;
  units?: number | null;
}) {
  return (
    <span className="action-chip">
      {action === "no_action"
        ? "—"
        : `${formatLabel(action === "expedite_po" ? "expedite PO" : action)}${action === "reorder" && units != null ? ` ${formatCount(units)}` : ""}`}
    </span>
  );
}
export function Kpi({
  label,
  value,
  note,
  definition,
  href,
}: {
  label: string;
  value: string;
  note?: string;
  definition: keyof typeof definitions;
  href?: string;
}) {
  const title = (
    <span tabIndex={0} title={definitions[definition]}>
      {label} <span className="info">ⓘ</span>
    </span>
  );
  return (
    <div className="kpi">
      <dl>
        <dt>{href ? <Link href={href}>{title}</Link> : title}</dt>
        <dd>{value}</dd>
      </dl>
      {note && <p>{note}</p>}
    </div>
  );
}

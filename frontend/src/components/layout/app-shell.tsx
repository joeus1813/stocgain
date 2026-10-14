"use client";
import Link from "next/link";
import { usePathname, useSearchParams, useRouter } from "next/navigation";
import {
  useEffect,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import {
  LayoutDashboard,
  ShieldAlert,
  SlidersHorizontal,
  BookOpen,
  Truck,
  Menu,
  PanelLeftClose,
  FlaskConical,
} from "lucide-react";
import { useMeta } from "@/lib/api/hooks";
import { formatDate, formatCount } from "@/lib/format";
import { globalQuery } from "@/lib/url-state";
import { FilterBar } from "./filter-bar";
const subscribeSidebar = (notify: () => void) => {
  window.addEventListener("stocgain-sidebar", notify);
  return () => window.removeEventListener("stocgain-sidebar", notify);
};
const sidebarSnapshot = () => {
  try {
    return localStorage.getItem("stocgain.sidebar") === "compact";
  } catch {
    return false;
  }
};
const nav = [
  { href: "/", label: "Overview", Icon: LayoutDashboard },
  { href: "/risk", label: "Risk Monitor", Icon: ShieldAlert },
  { href: "/suppliers", label: "Suppliers", Icon: Truck },
  { href: "/scenarios", label: "Scenario Lab", Icon: SlidersHorizontal },
  { href: "/methodology", label: "Methodology", Icon: BookOpen },
];
export function AppShell({ children }: { children: ReactNode }) {
  const path = usePathname(),
    params = useSearchParams(),
    router = useRouter();
  const meta = useMeta();
  const [open, setOpen] = useState(false);
  const compact = useSyncExternalStore(
    subscribeSidebar,
    sidebarSnapshot,
    () => false,
  );
  const suffix = globalQuery(new URLSearchParams(params.toString()));
  useEffect(() => {
    try {
      const saved = localStorage.getItem("stocgain.filters.v1");
      if (
        !window.location.search &&
        saved &&
        ["/", "/risk", "/suppliers"].includes(window.location.pathname)
      )
        router.replace(`${window.location.pathname}?${saved}`);
    } catch {}
  }, [router]);
  const title =
    path === "/"
      ? "Executive Overview"
      : path.startsWith("/positions")
        ? "Product Risk Detail"
        : (nav.find((n) => path.startsWith(n.href) && n.href !== "/")?.label ??
          "stocgain.");
  return (
    <div
      className={`app-shell ${compact ? "compact" : ""} ${open ? "nav-open" : ""}`}
    >
      <a className="skip-link" href="#content">
        Skip to content
      </a>
      <aside className="sidebar">
        <Link href="/" className="wordmark">
          <span className="brand-mark">▤</span>
          <span>
            stocgain<span className="brand-dot">.</span>
          </span>
        </Link>
        <p className="nav-caption">WORKSPACE</p>
        <nav aria-label="Main navigation">
          {nav.map(({ href, label, Icon }) => (
            <Link
              key={href}
              href={`${href}${suffix ? "?" + suffix : ""}`}
              className={path === href ? "active" : ""}
              aria-current={path === href ? "page" : undefined}
              title={label}
              onClick={() => setOpen(false)}
            >
              <Icon size={18} />
              <span>{label}</span>
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <p>
            Predict stockouts.
            <br />
            Replenish smarter.
          </p>
          <small>
            v1.0 ·{" "}
            {meta.data?.run
              ? `Run ${meta.data.run.run_id}`
              : "No analytics run"}
          </small>
          <button
            className="collapse-button"
            aria-label="Toggle compact navigation"
            onClick={() => {
              try {
                localStorage.setItem(
                  "stocgain.sidebar",
                  !compact ? "compact" : "full",
                );
                window.dispatchEvent(new Event("stocgain-sidebar"));
              } catch {}
            }}
          >
            <PanelLeftClose size={18} />
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <button
            className="mobile-menu"
            aria-label="Toggle navigation"
            aria-expanded={open}
            onClick={() => setOpen(!open)}
          >
            <Menu size={20} />
          </button>
          <div>
            <strong>{title}</strong>
            <p>
              {meta.data?.run
                ? `As of ${formatDate(meta.data.run.as_of_date, true)} · Analytics run #${meta.data.run.run_id}`
                : "Connecting to analytics…"}
            </p>
          </div>
          <details className="dataset-popover">
            <summary className="dataset-badge">
              <FlaskConical size={14} />
              <span>Simulated Retail Dataset</span>
            </summary>
            <div className="dataset-content">
              <h3>Simulated Retail Dataset</h3>
              <p>
                {meta.data?.dataset?.provenance_statement ??
                  "Deterministic synthetic retail data. No real retailer affiliation."}
              </p>
              {meta.data?.dataset && (
                <p>
                  {meta.data.dataset.preset} · Seed{" "}
                  {formatCount(meta.data.dataset.seed)}
                  <br />
                  {formatDate(meta.data.dataset.history_start_date)} –{" "}
                  {formatDate(meta.data.dataset.history_end_date, true)}
                </p>
              )}
              <Link href="/methodology">Data & methodology →</Link>
            </div>
          </details>
        </header>
        {["/", "/risk", "/suppliers"].includes(path) && <FilterBar />}
        <main id="content">{children}</main>
        <footer>
          stocgain.{" "}
          <span>
            Predictive Retail Inventory Intelligence Platform · Decision support
            only
          </span>
        </footer>
      </div>
    </div>
  );
}

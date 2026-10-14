import Link from "next/link";
export default function NotFound() {
  return (
    <section className="empty">
      <h1>Page not found</h1>
      <p>This page or position is not available.</p>
      <Link href="/risk">Back to Risk Monitor →</Link> ·{" "}
      <Link href="/">Overview</Link>
    </section>
  );
}

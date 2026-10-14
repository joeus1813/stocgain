"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <section className="error-state" role="alert">
      <h1>This page could not load</h1>
      <p>Your data is preserved. Try loading the page again.</p>
      <button onClick={reset}>Retry</button>
    </section>
  );
}

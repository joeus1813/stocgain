# AGENTS.md — Instructions for Coding Agents Working on StockSense

These instructions apply to every coding agent (OpenAI Codex or otherwise) working in this repository. They override habits and defaults. When in doubt, choose correctness, honesty, and simplicity.

---

## 1. Read before you write

Before writing any code in a session:

1. Read `CODEX_HANDOFF.md` (the contract).
2. Read `docs/00_DESIGN_SUMMARY.md` — especially §4 **Canonical Constants**. These values are binding.
3. Read `docs/PROGRESS.md` to find the current phase and open issues.
4. Read the numbered docs relevant to the current phase (`docs/09_IMPLEMENTATION_ROADMAP.md` lists them per phase).

Conflict resolution order: `docs/00` §4 → numbered doc → `CODEX_HANDOFF.md`. Record any conflict you find, and how you resolved it, in `docs/DECISIONS_LOG.md`.

---

## 2. Scope discipline

- Implement **one phase at a time**, in the order in `docs/09`. Do not start a phase until the previous phase's Definition of Done is met and recorded in `docs/PROGRESS.md`.
- **P0 before P1. Never P2** unless the project owner explicitly asks.
- **Do not silently change product scope**, features, formulas, thresholds, table names, endpoint paths, or page structure. If something in the spec is wrong or impossible, stop, explain the problem in `docs/DECISIONS_LOG.md` and in your summary, propose the smallest fix, and implement it only if it does not change product behavior (e.g., a SQL syntax correction). Product-behavior changes need owner approval.
- You may make **low-level implementation decisions** (helper functions, file splits within a module, internal naming, component composition) without asking. Record non-obvious ones in `docs/DECISIONS_LOG.md`.
- Do not add features that were not specified "because they'd be nice". No extra pages, no extra charts, no auth, no deployment configs.

---

## 3. Follow the agreed stack

- Backend: Python 3.12, uv, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, psycopg 3, pandas, NumPy, SciPy, Typer.
- Frontend: Next.js (App Router) + TypeScript strict, Tailwind v4, shadcn/ui, TanStack Query, TanStack Table, Recharts, lucide-react.
- Database: PostgreSQL 17 via Docker Compose.
- **Avoid unnecessary dependencies.** Before adding any package not listed in `docs/02` §2, write a one-line justification in `docs/DECISIONS_LOG.md`. Prefer the standard library and existing dependencies. Never add Redis, Celery, schedulers, ORMs on the frontend, state-management libraries, mock-data libraries, or paid/networked services.
- Pin exact versions in lockfiles. Use current stable versions that are mutually compatible; follow current official setup instructions (e.g., shadcn/ui with Tailwind v4).

---

## 4. Data correctness is the top priority

- The inventory equation, non-negative stock, sales ≤ available, and the other data-quality rules in `docs/03` §10 must hold. If a DQ check fails, **fix the generator or loader**, never the check, never the data by hand.
- **Point-in-time correctness:** every pipeline query takes `:as_of` and must not read rows dated after it. Never use `sim_truth.*` outside `analytics/backtest.py` (simulation-only basis) and DQ15.
- Use exact formulas from `docs/05`. Window lengths, rounding (`ceil(x − 1e−9)` for integer levels), distribution parameterizations, and tie-breaks matter. The golden cases in `docs/05` §15 must pass.
- Money is rounded to cents only at storage/serialization; compute at full precision.
- The Scenario Lab must call the same analytics functions as the pipeline; neutral inputs must reproduce stored results.

---

## 5. No mock data. Ever. (In application code.)

- **Avoid mock dashboard responses.** Every value shown in the UI must come from an API response that reads PostgreSQL tables/views populated by the pipeline.
- **Connect displayed values to the actual database and analytical outputs.** No hardcoded numbers, no placeholder KPIs, no "sample" arrays in components, no lorem ipsum.
- Build **end-to-end vertical slices**: database → SQL → analytics → API → UI. Do not build all frontend screens with placeholder data before the backend exists. If an endpoint is not ready, the page is not built yet.
- Fake responses are allowed **only inside tests** (e.g., Playwright route stubs to test error states, unit-test fixtures).
- Illustrative content on the Methodology page (e.g., worked example 4) must be labeled "Illustrative example — not from the dataset".

---

## 6. Honesty in labels, logs, and summaries

- The UI must display the **Simulated Retail Dataset** badge on every page; estimated values carry "Est." / "Model estimate" labels.
- **Never invent implementation success.** Do not write "tests pass", "performance target met", "works on mobile" unless you ran the command and observed it in this session. Quote the actual command and summarize the actual output.
- **Never claim that unfinished features work.** If a feature is partial, say exactly what works and what doesn't.
- **Report known limitations** at the end of every phase in `docs/PROGRESS.md` and in your summary.
- Never fabricate model accuracy, business impact, or benchmark numbers in docs, README, UI copy, or commit messages. Accuracy statements come only from stored backtest results.
- Never imply affiliation with any real retailer; never use real company logos, trademarks, or brand colors.

---

## 7. Verification standards

At the end of each task group and before marking a phase done:

```bash
make lint          # ruff check, ruff format --check, eslint
make typecheck     # mypy (analytics strict), tsc --noEmit
make test          # pytest (unit, db, api) + vitest
make check-openapi # once Phase 4 starts
make e2e           # from Phase 6 onward (requires running stack)
```

- **Test completed functionality.** Every new module ships with tests at the level specified in `docs/10`. Bug fixes ship with a regression test.
- **Run lint and type checks** on every change; do not leave warnings you introduced.
- Run the phase's verification commands from `docs/09` and record results in `docs/PROGRESS.md` (date, command, pass/fail counts, timings, machine description for performance numbers).
- If a test is flaky, fix the cause (seed, ordering, timing). Do not skip or loosen tests to get green, and never delete a failing test without recording why.

---

## 8. Database and migration rules

- **Maintain database migrations.** All schema changes go through new Alembic revisions with working downgrades. Never edit an applied revision.
- Views live in `sql/views/` as repeatable, ordered files (`DROP … CASCADE; CREATE …`). `make migrate` applies Alembic then views.
- Keep SQL in `.sql` files with the header comment format from `docs/04`. Use bound parameters only; whitelist sort columns.
- After schema changes, run `make schema-dump` and confirm the ERD in `docs/03` still matches; update docs if not.

---

## 9. Keep configuration reproducible

- All model parameters live in `backend/config/analytics.toml`; generator presets and events in `backend/config/generator.toml`; environment in `.env` (template `.env.example`). No parameter is hardcoded in more than one place; tests read values from config.
- The full analytics config is stored in each `analytics_runs.config`.
- Deterministic generation: seeded NumPy streams only; no wall-clock, no Python `hash()`, no unordered iteration.
- A fresh clone must reach a populated dashboard using only the README commands. If you change a command, update the README, Makefile help, and `docs/02` §9 together.

---

## 10. Code quality conventions

- **Prefer maintainable code over clever abstractions.** Plain functions, explicit names, small modules. No metaprogramming, no generic repository frameworks, no premature plugin systems.
- Python: type hints everywhere; `analytics/` passes `mypy --strict`; Ruff defaults + `I` (isort) + `B` + `UP`; docstrings on public functions stating units and formula references (e.g., "See docs/05 §5.5").
- Analytics functions are **pure** and vectorized (NumPy arrays over positions). No DB access outside `analytics/pipeline.py` and repositories.
- API routers are thin; logic lives in services; SQL lives in files.
- TypeScript: `strict: true`; no `any` (use generated schema types); components are small and typed; client components only where interactivity requires it; formatting only via `lib/format.ts`; tooltip/definition text only via `lib/definitions.ts`.
- Styling only via design tokens (`docs/07` §3); no ad-hoc hex colors in components.
- Accessibility: labels for all inputs, keyboard support, visible focus, no color-only meaning.
- Naming: DB `snake_case`; API `snake_case`; TS variables `camelCase`, types `PascalCase`; files per `docs/02` §5.
- Commit messages: `phase-N: <imperative summary>`; small, focused commits.

---

## 11. Documentation duties

- **Document major decisions** in `docs/DECISIONS_LOG.md` (date · decision · reason · alternatives · impact).
- Update `docs/PROGRESS.md` at the end of every phase: status, verification summary (real output), known issues, deferred items with reasons.
- If implementation reveals a needed spec change, update the relevant numbered doc in the same commit and note it in the decisions log.
- README and resume bullets (Phase 9) use only verified facts from `docs/11` §9.

---

## 12. Interaction with the project owner

- Ask the owner only when blocked on a product decision the docs don't settle. Otherwise proceed with the documented default and record it.
- End every session with a summary: what was completed, commands run and their real results, what remains, known limitations, and any decisions that need owner review.

---

## 13. Quick reference — things you must never do

1. Ship UI that shows hardcoded, mocked, or placeholder numbers.
2. Claim a test, feature, or benchmark works without running it.
3. Read `sim_truth` from forecasting, risk, API, or UI code.
4. Use future data in a pipeline query or backtest.
5. Edit data or loosen a check to make validation pass.
6. Change formulas, thresholds, or scope without recording and justifying it.
7. Add P2 features or unlisted dependencies without approval.
8. Create purchase orders or any write-back feature.
9. Use real retailer branding or imply affiliation.
10. Leave a visible control that does nothing.

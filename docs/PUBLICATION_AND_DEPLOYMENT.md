# Publication and deployment handoff

These are preparation instructions. No remote repository or public service was changed by this execution. Local publication readiness is conditional on the outstanding acceptance items in IMPLEMENTATION_STATUS.md.

## Before GitHub publication

1. Confirm the intended repository, branch and visibility with the owner. Inspect the existing remote before adding or changing one; never reset or rewrite history.
2. Replace the MIT `<Project Owner>` copyright placeholder with the owner's preferred legal attribution. Review THIRD_PARTY_NOTICES.md.
3. Review staged files and repository history for credentials. `.env`, local tool installations, generated data, backups, node_modules and virtual environments must stay ignored. Local example credentials are for isolated development only.
4. Review README screenshots and statements against the verified facts register. Retain the Simulated Retail Dataset disclaimer and accuracy limitations.
5. Complete the isolated fresh-setup verification and outstanding accessibility gates before calling the repository fully accepted.
6. Only after explicit owner approval, push the reviewed local branch to the confirmed remote. This document deliberately performs no remote operation.

## Local launch

With Docker Desktop running: `make db-up`, then `make api` and `make web` in separate terminals. Frontend: http://localhost:3050; API: http://localhost:8000/docs. Existing data needs no regeneration. Fresh installs use `make setup` and `make pipeline` (migration → safe seed → analytics).

## Hosting preparation (not deployed or verified)

Keep the existing architecture: PostgreSQL 17, one FastAPI service and one Next.js service. Use environment-specific database credentials, an exact frontend CORS origin and TLS. Do not expose PostgreSQL publicly. Supply `NEXT_PUBLIC_API_BASE_URL` at frontend build time; it is not a runtime browser secret. Run migrations and the deterministic pipeline explicitly before opening the UI. Preserve the database volume across application restarts.

The supplied Compose `full` profile is a local deployment candidate, not a verified production release. Confirm backend SQL/config files are present in its image, persistent volume permissions, frontend assets, health checks and cold-cache behavior in an isolated environment. Set proper secrets and backup/restore procedures before any public deployment. The app has no authentication and no order write-back; hosting access controls and resource limits need an owner-approved deployment plan. Do not purchase services or expose the local demo as a substitute for that review.

## Safe fresh-setup verification

`scripts/verify_fresh_setup.sh` clones the committed source into a unique temporary folder and starts a separately named Compose project on host port 55433. It never deletes the active project database, generated dataset or volume. It retains its temporary container/volume for inspection. Ensure the port is free, run with Docker/uv/Node available, and record its actual result before claiming a fresh setup passed. The script has been prepared but not yet successfully executed as of this handoff.

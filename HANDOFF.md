# Session handoff — SupportMind

Written 6 Aug 2026, updated 7 Aug at the end of Phase 13. Delete this file once Phase 18 ships;
it is working state, not project documentation.

## Where things stand

`main` is at `4f8b1fa`. Phase 13 sits on `security-hardening`, unmerged and unpushed.

| | |
| --- | --- |
| Backend tests | 89 (pytest) — 81 on SQLite, 8 need Postgres |
| Frontend tests | 41 (Vitest) + 1 Playwright flow |
| ADRs | 39 |
| Phases complete | 1–13, plus 11b (CI) |
| Next | Phase 14 |

## The plan being followed

`C:\Users\LOQ\Downloads\supportmind-master-prompt.md` — **read it before starting a phase.** It
defines phases 11–18, their priorities, and a per-phase learning workflow: write
`docs/learning-notes/phase-N.md`, then explain in chat what was actually understood versus executed
from a spec, before moving on.

Remaining: **14** deletion and pagination → **15** eval harness and retrieval quality →
**17** observability and cost caps → **18** deploy.

**Phase 16 (LangGraph agent layer) is skipped** by the user's decision. The README's "what I'd build
next" already says so; keep it that way rather than letting it read as an oversight.

## Decisions already settled — do not relitigate

- **Skip the agent layer** (phase 16).
- **The 60-minute session with no refresh token is accepted**, as is the token in `localStorage`.
  ADR-039 records both tradeoffs; do not reopen them as bugs.
- **Branch names describe the change, not the process** — `security-hardening`, not
  `phase-13-security`. Few branches; trivial fixes go straight to `main`; delete once merged.
- **Commits are short**, conventional prefixes, and carry **no `Co-Authored-By` trailer**. This
  repository is a hiring artifact and the user's name is the only one that should appear.
- FastAPI's `{detail}` error shape stays; no custom error envelope.

## Phase 13, as built

All three items done, on `security-hardening`. Limitations 4, 6 and 8 are closed.

- **Rate limiting** — fixed window in Redis. Auth is keyed per client address, chat per
  organization. Fails open when Redis is unreachable. ADR-037.
- **Row-Level Security** — policies on the six tenant tables, scoped by a session variable that
  middleware sets from the request. CI now runs a Postgres service so the tests actually execute,
  and `REQUIRE_RLS_TESTS` turns a skip into a failure. ADR-038.
- **ADR-039** for the localStorage and 60-minute-session tradeoffs, plus
  `docs/learning-notes/phase-13.md`.

**The setup change this phase forces:** there are now two database URLs. `MIGRATION_DATABASE_URL`
is the owner (`postgres`), `DATABASE_URL` is a non-owning `supportmind_app` role the migration
creates. This is not optional — Postgres exempts superusers and table owners from row-level
security, so connecting as `postgres` silently bypasses every policy while `pg_class` still
reports them enabled and forced. `backend/.env` has already been updated locally and the migration
has been applied to the dev database. If the API logs a warning about bypassing RLS at startup,
`DATABASE_URL` is pointing at the wrong role.

Left for later, deliberately: proxy header trust for the auth limit (phase 18, it is a deployment
concern), and a daily token budget rather than a per-minute rate (phase 17's cost cap).

## Running it

Three processes. Without the worker, prepared documents never leave "Uploaded".

```bash
cd backend && docker compose up -d          # Postgres on 5433, Redis on 6379
cd backend && python -m uvicorn app.main:app --port 8000
cd backend && python worker.py
cd frontend && npm run dev                  # localhost:3000
```

Test accounts, password `testpassword123`: `onboard4@example.com` (full workspace, documents, chat
history), `onboard1@example.com` (workspace and knowledge space, no documents).

## Traps that have each cost real time

- **Never delete `.next` while the dev server runs**, and do not run `npm run build` while it is up.
  Both corrupt its state and produce phantom 404s or a UI that silently stops updating. Stop the
  server first.
- **Postgres is on 5433**, database `rag_support_agent`. One compose file only:
  `backend/docker-compose.yaml`. A duplicate at the repository root was deleted on 6 Aug.
- **A superuser silently ignores row-level security.** `ENABLE` and `FORCE` both read as on, every
  policy is listed in `pg_policies`, and none of them apply. This cost a debugging session on 7 Aug
  when the first RLS test suite passed while enforcing nothing. Any test of tenant isolation has to
  connect as `supportmind_app`, not `postgres`.
- **A `rls_test` database exists on the local Postgres** for the row-level security tests. It is
  torn down and rebuilt by the test module; leave it alone.
- **RQ on Windows** needs `SimpleWorker` and `TimerDeathPenalty`; `worker.py` handles this, because
  Windows has neither `os.fork` nor `SIGALRM`. Linux deployment gets the forking worker.
- **The GitHub API rate-limits at 60 requests/hour unauthenticated.** A tight CI-polling loop
  exhausts it.
- **CI shows a red badge from a cancelled run.** Both jobs sat 15 minutes with zero steps executed —
  GitHub had no runners. Not a code failure. Any push once Actions recovers turns it green.

## Open items not tied to a phase

- `OPENAI_API_KEY` needs adding as a repository secret before `e2e.yml` can run in CI.
- The three deployment blockers are still open by design and belong to phase 18: CORS registering
  only for local-looking `APP_ENV`, uploads written to an ephemeral container filesystem, and the
  JWT secret falling back to a known default.

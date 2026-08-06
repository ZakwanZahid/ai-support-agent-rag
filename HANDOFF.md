# Session handoff — SupportMind

Written 6 Aug 2026, at the end of Phase 12. Delete this file once Phase 18 ships; it is working
state, not project documentation.

## Where things stand

`main` is at `4f8b1fa`, everything pushed, working tree clean, and GitHub shows **only `main`** —
the phase-named branches were deleted after being merged.

| | |
| --- | --- |
| Backend tests | 69 (pytest) |
| Frontend tests | 41 (Vitest) + 1 Playwright flow |
| ADRs | 36 |
| Phases complete | 1–12, plus 11b (CI) |
| Next | Phase 13 |

## The plan being followed

`C:\Users\LOQ\Downloads\supportmind-master-prompt.md` — **read it before starting a phase.** It
defines phases 11–18, their priorities, and a per-phase learning workflow: write
`docs/learning-notes/phase-N.md`, then explain in chat what was actually understood versus executed
from a spec, before moving on.

Remaining: **13** security hardening → **14** deletion and pagination → **15** eval harness and
retrieval quality → **17** observability and cost caps → **18** deploy.

**Phase 16 (LangGraph agent layer) is skipped** by the user's decision. The README's "what I'd build
next" already says so; keep it that way rather than letting it read as an oversight.

## Decisions already settled — do not relitigate

- **Skip the agent layer** (phase 16).
- **The 60-minute session with no refresh token is accepted.** Phase 13 writes an ADR explaining the
  tradeoff instead of building refresh tokens.
- **Branch names describe the change, not the process.** Phase 13 goes on `security-hardening`, not
  `phase-13-security`. Few branches; trivial fixes go straight to `main`; delete once merged.
- **Commits are short**, conventional prefixes, and carry **no `Co-Authored-By` trailer**. This
  repository is a hiring artifact and the user's name is the only one that should appear.
- FastAPI's `{detail}` error shape stays; no custom error envelope.

## Phase 13 scope

- Rate limiting on auth and chat endpoints, Redis-backed (Redis already exists from phase 12). The
  chat limit matters most: it is the uncapped OpenAI spend path.
- Postgres Row-Level Security scoped to `organization_id`, as defence-in-depth on top of the
  existing dependency checks. **Note:** the test suite runs on in-memory SQLite, which cannot
  exercise RLS at all — that part needs a Postgres service in CI, which `ci.yml` does not currently
  have.
- An ADR for the localStorage and session-expiry tradeoffs.

Closes limitations 4, 6 and 8 in the tracked table.

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

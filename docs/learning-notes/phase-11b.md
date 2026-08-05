# Phase 11b — Continuous integration

## What problem this phase solved

After Phase 11 the repo had 90 tests that ran only when someone remembered to run them. That is close to having none: the value of a test is that it runs on code you weren't thinking about, written by someone who wasn't thinking about it either. Phases 12 to 15 change background jobs, add row-level security, add deletion, and rewrite retrieval — the four most regression-prone changes in the plan. Sequencing CI ahead of them means each of those lands against a suite that actually executes.

## The key design decision: two pipelines, not one

The obvious thing is one workflow that runs everything on every push. I split it, and the reasoning is the part worth defending.

**`ci.yml` runs on every push and pull request.** Backend tests, frontend lint, typecheck, unit tests, and a production build. It needs no secrets, no database service, and no network calls to a paid API. It finishes in a couple of minutes and costs nothing.

**`e2e.yml` runs only when triggered by hand.** It stands up Postgres with pgvector, migrates it, starts the API, and drives a real browser through signup to a sourced answer — including real embedding and chat calls.

The reason for the split is that the end-to-end test **spends money and time on every run**. A few cents and a few minutes is nothing once; on every push to every branch it becomes both a bill and a bottleneck, and the usual outcome is that someone disables it. Making it deliberate keeps it trustworthy. You run it before a release, or after touching onboarding, preparation, or chat.

The tradeoff, stated plainly: a regression that only the end-to-end test catches can reach `main` unnoticed. I think that is the right trade at this stage, and the mitigation is that the cheap pipeline covers the logic those flows depend on. If this were a team repo with real users, I would run e2e nightly on `main` as well.

## Why the backend job needs no database

Worth understanding rather than accepting, because it is the reason CI is fast.

`conftest.py` builds the whole test suite against **in-memory SQLite**, with two compiler shims registered so the Postgres-specific column types still work: `JSONB` compiles to `JSON`, and the pgvector `Vector` type compiles to `TEXT`. The embedding and chat providers are replaced with deterministic fakes. So the tests exercise the real routes, services, and repositories, but never touch Postgres or OpenAI.

The tradeoff is that these tests cannot catch anything genuinely Postgres-specific — a pgvector operator, an index that only exists on the real schema, a migration that fails on Postgres but not SQLite. That gap is real and gets wider in Phase 13, when Row-Level Security policies arrive: **RLS cannot be tested against SQLite at all**, so that phase will need a Postgres service in CI for at least part of the suite.

## What breaks first at real scale

**Cache keys.** Both jobs cache on the lockfile hash. Change one dependency and the whole cache is rebuilt. Fine now; on a larger dependency tree it becomes the dominant cost, and the answer is usually a warm base image rather than more caching.

**Job independence.** Backend and frontend run in parallel and share nothing, which is why the pipeline is quick. The moment something needs both — a contract test that checks the frontend's types match the API's OpenAPI schema, which would be a genuinely good addition — that structure has to change.

**The e2e's data trail.** Each run creates a user, a workspace, and a document, and never cleans up. In CI that does not matter because the database dies with the container. Pointed at a shared environment it would leak steadily, and there is no delete endpoint yet to clean up with (limitation #14, Phase 14).

## Something the workflow made visible

Writing `e2e.yml` forced me to set `APP_ENV: local` for the API, with a comment explaining why. That is limitation #1 showing its face: **CORS middleware only registers when the environment looks local**, so a truthfully-configured production API would have the browser block every request.

I had been treating that as a deployment task for Phase 18. Seeing it turn up as a lie I had to tell my own CI workflow is a better argument for fixing it than the entry in a limitations table was.

## What I understood versus what I executed

The split between the two pipelines, the reasoning about cost and trust, and the SQLite tradeoff are mine and I would defend them unprompted.

**Executed from convention rather than derived:** the specific GitHub Actions plumbing — `actions/setup-python` cache configuration, the `services:` health-check options block, `concurrency` groups, artifact upload. That is standard boilerplate I pattern-matched rather than reasoned about. If asked "why `--health-retries 10`", the honest answer is that it is a conventional value, not one I measured. Worth reading the Actions documentation on service containers properly before Phase 13 needs a Postgres service for the RLS tests.

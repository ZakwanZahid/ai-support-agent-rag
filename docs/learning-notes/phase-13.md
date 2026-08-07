# Phase 13 — Security and multi-tenancy hardening

## What problem this phase solved

Three separate holes, only one of which was really about "security" in the way the word usually gets used.

The chat endpoint was uncapped. Every message is an embedding call plus a completion, both billed, and nothing anywhere limited how many a single account could send. Not an attack scenario — a loop in a client, or a demo link on the internet, would have done it.

Tenant isolation rested entirely on the application remembering to filter. Every repository does filter by `organization_id`, but that is a property of the code being correct, not a property of the database refusing. One missing `WHERE` clause in a future query is a cross-tenant leak.

And the session design — token in `localStorage`, sixty-minute hard expiry — was a shortcut nobody had written down. The phase's actual instruction was to fix it *or* explain it, and explaining it was the right call for reasons in ADR-039.

## Rate limiting: the key matters more than the number

The thing I actually understood here is that choosing *what to count per* is the design decision, and the limit itself is a knob.

Auth is counted per client address. There is nothing else available — the whole point is that the caller has not authenticated yet, so there is no user or organization to attribute the attempt to.

Chat is counted per **organization**, not per user. That took a second to see. Per-user would mean an organization can multiply its spend by adding members, which is exactly backwards: the bill is per organization, so the budget should be too.

Two details I would not have predicted:

**Fixed window vs sliding.** A fixed window lets someone send the full limit at 11:59:59 and again at 12:00:00 — double the limit across the boundary. A sliding window fixes that, but needs a stored log of request timestamps per caller to trim on every request. At twenty requests a minute, the burst is harmless and the sorted set is not worth it. This is the first time I have knowingly chosen the less correct algorithm and been able to say why.

**Failing open.** If Redis is down, the limiter lets the request through and logs. My instinct was the opposite — refuse, be safe. But refusing means a Redis outage becomes a total login and chat outage, and the limiter is not what is keeping attackers out; authentication is. Deciding *which failure is worse* is the actual work, and it is why the ADR says explicitly that the limiter is a spend control and not a security boundary.

I also learned that `request.client.host` is the immediate peer. Behind a load balancer that is the load balancer, so every caller shares one bucket, and trusting `X-Forwarded-For` blindly is worse — the caller writes that header, so they can forge a fresh identity per request and opt out entirely. Correct handling needs to know the hop count, which is deployment configuration. I left it documented rather than guessed.

## Row-level security: the part that nearly shipped as decoration

This is the piece I would have got wrong on my own, and the failure was instructive enough to be worth the whole phase.

The mechanism: each tenant table gets a policy saying a row is visible only when its `organization_id` matches a session variable, and middleware sets that variable from the request. A query that forgets its filter returns nothing instead of someone else's rows.

I wrote the policies, wrote a test against a real Postgres, and **the test failed** — every tenant's rows came back. Not because the policies were wrong. Because the connection was `postgres`, and **Postgres exempts superusers from row-level security entirely**. `ENABLE` and even `FORCE` are both reported as on; `pg_class` says everything is protected; nothing is. The database will happily tell you the feature is enabled while ignoring it.

Two roles are the fix: migrations run as the owner, the application connects as a role that owns nothing and has no bypass. That is why the phase touched `DATABASE_URL`, `MIGRATION_DATABASE_URL`, and a role-creating migration, none of which was in my mental model when I started. I added a startup check that logs when the connected role bypasses the policies, because the failure is otherwise completely silent — every request works, every query succeeds, and nothing is isolated.

The second trap was subtler. I first set the session variable once, when the request opened its database session. It worked, then stopped working after a commit. **SQLAlchemy returns the connection to the pool on commit**, and the next statement gets a different connection with none of the previous one's settings. So the scope is applied on `after_begin` — every transaction, not once per session — and there is a test named for exactly that, because I would not have thought to write it if I had not hit it.

Where the scope comes from is worth stating precisely, because it looks wrong at first glance: it is read from the client-supplied path or header. That is fine because the scope **narrows and never grants**. Whether this user may touch that organization is still decided by the membership check. RLS is a second line against my own future bug, not against a forged header — the header was already an authenticated request's claim.

The design choice I am most pleased with is what I did *not* do. The stale-preparation sweep is genuinely cross-tenant, and the easy fix was a bypass flag the sweep could set. I made it walk the organizations and run the same scoped query inside each instead. One query per organization on a table that stays small, in exchange for an invariant with no exceptions: nothing in this system reads tenant data outside a tenant scope. An exception would have been the thing a reviewer found.

## What I executed from a spec versus actually designed

Worth being honest about, per the phase workflow.

**Designed:** the choice of key for each limit, fail-open, the decision to give the sweep no bypass, and the ADR reasoning on sessions.

**Understood after being surprised by it:** the superuser bypass, and the pooled-connection loss of session state. I did not know either before this phase. Both are now the two things I would check first on any RLS work.

**Executed from a spec:** the policy SQL itself (`USING` / `WITH CHECK`, `FORCE`), and the `GRANT` / `ALTER DEFAULT PRIVILEGES` set. I can read and explain these now, but I would not have written them from memory. The Postgres documentation on policy evaluation order, and what `WITH CHECK` does that `USING` does not, is the reading to do.

## What breaks first at real scale

**The rate limiter's identity, immediately on deploy.** Behind a load balancer every unauthenticated caller shares one bucket, so ten wrong passwords from anywhere locks out everyone. This has to be fixed in phase 18, not later.

**Chat's per-organization limit is a rate, not a budget.** Twenty messages a minute is still tens of thousands a day. The real control is a daily token cap, which is phase 17's cost cap, and this phase's limit is only the burst half of it.

**The sweep's per-organization loop** is linear in organizations. Fine at hundreds, wrong at hundreds of thousands — at which point the answer is a maintenance role with a genuine bypass and a single query, granted deliberately rather than by accident.

**RLS costs a planner check per row on every query**, and the policies compare against a `current_setting` call. It is cheap, but it is not free, and it applies to the vector search too. If retrieval latency becomes a problem in phase 15, this is one of the suspects.

**Sixty-minute sessions get worse as documents get bigger.** A long upload-and-prepare session is exactly when being logged out hurts most, and preparation time grows with document size.

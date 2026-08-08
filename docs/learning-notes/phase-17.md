# Phase 17 — Being able to see what the system did, and what it cost

## What problem this phase solved

Two things you only miss once something has gone wrong.

**Logs said things, but not about anything in particular.** Human-readable lines with no request id, no organization, no user. Fine while the only reader is me with the server in a terminal. Useless the moment logs are shipped somewhere and the question is "what happened to *that* request".

**Nothing knew what the app was spending.** Phase 13 put a per-minute rate limit on chat and I wrote at the time that it bounds a burst, not a day. That was true and it was the gap: twenty messages a minute is nearly thirty thousand messages a day. The rate limiter stops a runaway loop in seconds and does nothing about one that runs quietly overnight.

The CI half of this phase was already done back in 11b, so the work was logging, error reporting, and the cost cap.

## Structured logging: the decisions that were actually decisions

Switching to JSON is the obvious part. The parts I had to think about:

**Format at the root handler, not on my own loggers.** My first instinct was to configure `app.*` loggers and leave libraries alone. That produces a pipeline with two formats in it, and the practical result is that one of them never gets parsed. Uvicorn and SQLAlchemy get the same treatment as my own code.

**Silence uvicorn's access log rather than reformat it.** Once the middleware logs one line per request with method, path, status, duration and request id, uvicorn's access line is the same event with less in it. I only noticed after looking at real output and seeing every request twice.

**Context variable, not a parameter.** Threading a request id through every function that might log is explicit and invasive — it changes the signature of code with no interest in logging. A context variable keeps it out of the signatures and is invisible at the call site. That is a real cost and I took it knowingly; it is the same trade as the tenant scope from phase 13, which meant I already knew the trap (a context variable does not cross into a worker process, so jobs establish their own).

**Reuse an inbound `X-Request-Id`.** If a load balancer or another service already started a trace, generating a fresh id breaks the chain at my front door. Returning it on the response is what lets a user quote an id from an error.

**Redact by key, always.** Not "be careful what you log" — a rule enforced in the formatter, including nested dicts, whatever a caller passes. The reasoning that convinced me: a token in a log line is a token in every system the logs are shipped to, and log retention is usually longer than the token's life.

**Error reporting wired and off.** No DSN, no account, no dependency in `requirements.txt`. What I wanted from doing it now anyway is the `before_send` hook that strips `Authorization` and cookies — that decision belongs with the code that knows which fields are sensitive, not with whoever pastes in a DSN six months later and finds credentials in their error tracker.

## The cost cap: where the number comes from is the whole design

The thing I understand better after this phase is that **a spending control is only as good as its input**, and there were three plausible inputs.

**Count requests.** Simple, and wrong: one question against a full context costs many times another, so a request cap is a cap on something that is not the cost.

**Count tokens with a local tokenizer.** This was my first instinct, and it is the one I am most glad I rejected. A tokenizer gives you an *estimate* of the bill. You then have two numbers that both claim to be the spend — yours and the provider's — and they drift. Enforcing a limit against the one that is definitely wrong is the worst of the options.

**Count what the provider reported.** OpenAI returns `usage` on every response. It is the same number they bill from. So that is what gets stored and what the cap is enforced against.

Dollars are still computed, from a per-model price table, but they are labelled an estimate everywhere and the cap is deliberately **not** enforced on them — otherwise a price table going stale silently moves the limit.

### Postgres, not Redis — and why that is the opposite call from phase 13

This is the comparison I would want to be asked about. The rate limiter lives in Redis and **fails open**: if Redis is down the request goes through, because a limiter outage should not become a login outage.

The cost cap is the other way round. It counts money. A spending record that evaporates when a cache restarts is not a record — it is the row you would settle an invoice dispute from. It lives in the same database the request needs anyway, so there is no partial-availability case to trade against.

Same author, same week, opposite decision, and the difference is entirely about what the number is *for*.

### Two smaller things I got right by thinking about failure first

**The write is an upsert that adds in SQL.** My first version read the row, added to it, and wrote it back. Two requests finishing at the same moment both read the same starting figure and one overwrites the other's addition — spend silently lost. Losing spend is the one direction an accounting error must not go, so the addition happens in the database.

**Recording is in a `finally`.** A question that retrieved nothing still paid to embed itself. A completion the provider billed for before returning something unusable is still spend. A meter that only counts successful requests under-reports precisely when things are going wrong.

And it never raises into the caller. The user already has their answer; losing the meter must not turn a successful request into an error. It logs loudly instead — silently uncounted spend is how a cap stops working without anyone noticing.

## What I executed from a spec versus actually designed

**Designed:** metering on provider-reported tokens rather than a tokenizer or a request count; Postgres over Redis and the reasoning that makes it the opposite call from the rate limiter; the upsert; recording in `finally`; treating zero budget as "unconfigured" rather than "blocked"; and a `429` message that says when the limit clears, because "try again shortly" is wrong for a daily limit.

**Understood after being surprised:** that uvicorn duplicates the request log, and that logging configuration has to replace handlers rather than add to them. Both showed up only when I read real output, which is an argument for looking at the thing rather than trusting the code.

**Executed from a spec:** the `logging` module's `LogRecord` internals — knowing which attributes are standard so that `extra=` fields can be picked out — and Sentry's `before_send` hook shape. I looked both up.

**A mistake worth recording:** I patched the wrong `router.py` — there is an outer one and a `v1/` one — and my string replacement silently matched nothing, so the usage endpoint was never registered and the test failed with a confusing 404. A replacement that finds no match should be an error, not a no-op; the assertion I added afterwards is one line and would have saved the detour.

## What breaks first at real scale

**Logging every request at INFO.** At real traffic this is the largest thing the system produces, and log storage is billed by volume. Sampling successful requests while keeping every error is the usual answer, and it is a decision that needs traffic figures I do not have.

**The daily grain hides the spike.** A row per day tells you an organization spent a lot; it cannot tell you it spent it all in four minutes at 3am. Hourly buckets or a proper ledger answer that, at the cost of writes.

**The cap is per organization only.** A single user inside a workspace can spend the whole budget and lock out their colleagues. Per-user sub-budgets are the obvious next step and were not worth it for a product with no team management UI yet.

**Overshoot grows with concurrency.** The check reads committed usage, so N requests in flight together can all pass a check that only one of them should. At this scale that is a few thousand tokens; with heavy concurrency it would need a reservation, which means estimating, which is the thing this design avoids.

**The price table goes stale silently.** An unpriced model logs a warning and contributes zero cost, so spend gets under-reported rather than over-reported. That is the safer direction for the *cap* (which counts tokens anyway) and the wrong direction for a dashboard.

**No metrics or tracing.** Deliberately — the master prompt calls Prometheus/OpenTelemetry overkill here and I agree for a portfolio piece. What I would actually miss first is a latency histogram for the chat endpoint, since duration is currently only in the logs and nothing aggregates it.

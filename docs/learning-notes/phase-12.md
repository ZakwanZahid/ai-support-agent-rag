# Phase 12 — Durable background jobs

## What problem this phase solved

Preparation ran on FastAPI's `BackgroundTasks`, which means it ran *inside the API process*. Restart the API mid-preparation — a deploy, a crash, a machine reboot — and the work vanishes. Worse than vanishing: the document stays in `processing` forever, because that status was written before the work started and nothing is left alive to change it. The API refuses to start another job, because `processing` looks busy. The user watches a progress timeline that will never move, and there is no error anywhere, because nothing failed. It just stopped existing.

That is the failure this phase fixes, and it is worth stating precisely because "we added a job queue" is the boring version of it.

## What idempotent actually means here

This is the thing interviewers probe, so it is worth being exact rather than reciting the definition.

A queue that guarantees *at-least-once* delivery will eventually deliver twice. Network partitions, worker restarts, and retries all produce duplicate execution. So the job has to be safe to run more than once. In this pipeline that breaks into two separate properties, and I only understood they were separate while implementing them.

**Effect idempotency — running twice converges on the same state.** Extraction deletes a document's existing chunks before writing new ones, so a second run replaces rather than appends. Indexing only sends chunks whose embedding is still null, so a second run after a partial failure embeds only what is missing. This part was already true before this phase, which surprised me; the original design happened to get it right. The consequence is the one that matters commercially: **a repeated run does not pay OpenAI twice for the same chunks.** I verified this rather than assuming it — three documents from the same source file, one of which was interrupted and re-run, all ended with exactly one chunk and one embedding.

**Claim idempotency — two workers cannot run at once.** Effect idempotency is not enough if both workers are running *simultaneously*, because each is mid-transaction and neither can see the other's uncommitted writes. Both would embed the same chunks and both would be billed.

The fix is a single conditional UPDATE:

```sql
UPDATE documents SET status='processing', preparation_job_id=:job, ...
WHERE id=:id AND (unowned OR stale OR already mine)
```

and then checking how many rows it changed. The database resolves the race. The version I first reached for — read the status, decide, then write — has a window between the read and the write where both workers see an unclaimed document and both proceed. That window is small and would have worked in every test I ran. It would fail in production, occasionally, in a way that costs money and would be very hard to reproduce.

The third clause, "already mine", is what lets a retry of the same job reclaim its own document and continue.

## The retry policy, and why it is not just a number

Retrying everything is wrong, and I want to be able to say why rather than just assert it.

A corrupt PDF fails identically on attempt three as on attempt one. Retrying it spends wall-clock time, occupies a worker, and — once embeddings are involved — spends money, to arrive at the same answer. Meanwhile a provider timeout is a statement about the environment, not about the document, and the same input may well succeed a minute later.

So failures are classified. `TextExtractionError` and a document that produced no chunks are permanent: recorded as failed immediately. Timeouts, connection errors, and 5xx responses are transient: retried with backoff of 10s then 60s, capped at three attempts, after which the document is failed with the attempt count in its message so the user sees something true rather than a spinner.

Anything unrecognized is treated as **retryable**. That is a deliberate asymmetry: an unnecessary retry costs one more attempt, while wrongly classifying a transient error as permanent leaves a document failed that would have worked. The cheaper mistake is the one to make.

Backoff increases rather than staying flat, because constant retries against a provider that is down are just a faster way to exhaust the attempt budget.

## Why retries are not enough, and what a sweep is for

This is the part I did not appreciate until I had the queue running.

Retries handle jobs that *fail*. They do nothing for jobs that *disappear*. A worker killed between claiming a document and finishing it does not fail — it stops existing. There is no exception, no failed job in the registry, nothing for RQ to retry. The document sits in `processing` and no part of the system is aware.

So there has to be something that looks at the *data* rather than the queue and asks which documents have been claimed for implausibly long. That is the sweep. It runs periodically, finds documents processing past a threshold, and either requeues them or fails them depending on attempts already spent.

The threshold is deliberately generous — fifteen minutes by default — because the failure modes are asymmetric again: recovering a stuck document a few minutes late is fine, while failing a document that was merely slow destroys work that was about to succeed.

**And I got the sweep wrong on the first attempt.** I wrote it to look for a stale *claim timestamp*. Then I tested it against two documents that were genuinely stuck from a crashed worker — and it found neither, because those documents had no claim at all. The API marks a document `processing` when it enqueues, before any worker touches it, so a job lost before a worker claims it leaves a document processing with `preparation_started_at` still null. The sweep now compares against the claim time where one exists and the row's `updated_at` where one does not.

That bug is a good illustration of why testing against a real failure beats testing against an imagined one. I had a test for "worker died mid-job" and it passed. The case I had not imagined was "job died before the worker ever saw it."

## What breaks first at real scale

**One queue, one priority.** Every preparation waits behind every other. A user uploading fifty documents delays a user uploading one. The fix is separate queues or a per-tenant fairness scheme, and neither is worth building yet.

**The sweep is not coordinated.** Two sweeps running at once would both try to recover the same documents. The claim logic makes that harmless, but it is luck rather than design, and a real deployment wants a lock or a single scheduled runner.

**Redis is now a hard dependency for preparation.** If it is down, nothing prepares. The health endpoint reports the queue as unavailable so this is visible, but the API still accepts prepare requests and quietly queues nothing. Rejecting them with a clear error would be better.

**Attempts are never reset.** A document that fails three times, is fixed, and is retried by the user still carries three attempts, so it gets no fresh budget. The user-initiated path should reset the counter.

## What I understood versus what I executed

The claim design, the two kinds of idempotency, the retry classification, and the reasoning for the sweep are mine, and I would defend them unprompted.

**Executed rather than derived:** RQ's specific API surface — `Retry(max=, interval=)`, `result_ttl`, `failure_ttl`, the registries. I know what those do because I read the documentation this afternoon, not because I have operated RQ under load. If asked "what happens when the scheduler process dies", I would have to look it up.

Two things I had to work through on the way, both platform rather than design:

**RQ's default worker calls `os.fork`**, which Windows does not have, so the first worker crashed instantly. Then its timeout mechanism uses `SIGALRM`, which Windows also lacks. The worker now selects `SimpleWorker` with a thread-based timeout on platforms without fork. The tradeoff is documented in the code and is real: without a forked child, a job that hard-crashes the interpreter takes the worker with it, and a timeout raised from a thread cannot interrupt a blocking C call. Deployment targets Linux, so production gets the forking worker; this exists so the queue can be developed on Windows at all.

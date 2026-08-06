"""Durable background work.

Preparation runs on an RQ queue backed by Redis rather than FastAPI's
`BackgroundTasks`. The difference that matters: a `BackgroundTask` lives in the
API process, so a restart mid-preparation loses the work and strands the
document in `processing` with nothing left to finish it. A queued job survives
the process that enqueued it.
"""

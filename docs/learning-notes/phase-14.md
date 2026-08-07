# Phase 14 — Deletion, pagination, and server-side search

## What problem this phase solved

Two problems that look like features and are really the same problem: the app assumed collections were small enough to hold entirely.

Nothing could be deleted. Every document, knowledge space and workspace ever created was permanent, which the redesign report called the most visible gap in the product — and it is, because "I uploaded the wrong file" is the second thing anyone does.

And every list was fetched whole. The documents page loaded all of them and filtered in the browser, which worked perfectly at nine documents and would have fallen over at nine thousand. Same for a chat thread: opening it loaded every message that had ever been in it.

## Deletion: the cascade was already there, and using it correctly meant *not* using the ORM

This surprised me. Every tenant table already declared `ON DELETE CASCADE` on its foreign keys, so the database already knew how to delete a document's chunks and citations. The work was letting it.

My first version called `session.delete(document)` and it failed. SQLAlchemy's default behaviour on deleting a parent is to load every child row and set its foreign key to NULL — and those columns are `NOT NULL`, so it errors. Even where it works it is one query per collection to do what one statement does. The fix is a Core `DELETE`, which sends one statement and lets the database's own rules apply.

The thing I understand now that I did not before: **`ondelete="CASCADE"` and SQLAlchemy's `cascade="all, delete-orphan"` are two different mechanisms**, one in the database and one in the ORM, and having the first does not mean the second is configured. I had read both as "cascading is on".

A related discovery in the tests: **SQLite ignores foreign keys entirely unless you turn them on.** Without `PRAGMA foreign_keys=ON` the test suite would have happily asserted that deletion works while leaving every chunk behind. The tests were passing for the wrong reason until I checked what was actually in the table.

### The decisions that were mine rather than the database's

Three, and they are the ones I would expect to be asked about.

**A deleted document vanishes from past answers' sources.** Citations cascade with it. I went back and forth — losing the source under an old answer feels like damage. But the reason people delete a document is usually that it was wrong or should not have been there, and keeping a quoted passage from it would be exactly the wrong side to err on.

**A deleted knowledge space keeps its chat threads.** The foreign key was already `SET NULL`, which turned out to encode a decision someone had made earlier and I agreed with: history survives with nothing left to search. Deleting the conversations because their source went would be destroying a second thing nobody asked about.

**Deleting a document mid-preparation is refused, not queued.** This is the one I am most confident about. The delete cannot call back an embedding request that is already in flight and already billable. Accepting it would tell the user their money stopped being spent when it hasn't. A `409` saying "wait for it to finish" is a smaller lie than that — none, in fact — and the stale sweep from phase 12 bounds the wait.

## Pagination: choosing the *less* obvious algorithm and being able to say why

Offset pagination is what everyone reaches for and it is wrong here for two separate reasons.

The performance one is well known: `LIMIT 20 OFFSET 200` makes the database walk and throw away two hundred rows first, so deep pages cost more than shallow ones.

The correctness one is the reason I actually chose against it, and I had not thought about it before this phase. **Offset counts rows; it does not name them.** Both of these lists change while someone is reading them. Delete a document while a user sits on page two, and everything after it shifts up one — their next request starts one row too late, so they skip a row and nothing tells them. Upload one, and they see a row twice. There is a test named for exactly that case, because it is the difference the whole decision rests on.

A keyset cursor names a position in the sort order — "the rows after this one" — so an insert or delete elsewhere does not move it.

Three details I would not have got right first time:

**The sort key has to be a pair.** `created_at` alone is not unique, and an ambiguous cursor either repeats a row or skips one. `(created_at, id)` is deterministic. Comparing them as a row value, `(a, b) < (x, y)`, is standard SQL and does the right thing in one expression.

**The cursor should be opaque.** Base64, not two plain query parameters. A client that can read the sort key is a client that will build its own cursor, and then the ordering can never change.

**A bad cursor must be an error, not a fallback.** My instinct was to ignore a malformed cursor and return page one. That turns a paging client into an infinite loop: it never advances and never notices.

Fetching `limit + 1` rows to learn whether more exist is the small trick that avoids a second `COUNT` over the whole filtered set.

Direction turned out to matter too. Documents page forwards from newest. A thread pages *backwards* — you open a conversation at its end and walk towards the start — which meant querying descending, taking the newest page, then reversing it for display.

## The bug that pagination found

Worth writing down, because it is the kind of thing I would otherwise assume was a test-environment quirk and move past.

The cursor did nothing. Every page returned the same rows.

`created_at` was set only by `server_default=func.now()`, which renders as *the database's own* timestamp function. Postgres gives microseconds. SQLite's `CURRENT_TIMESTAMP` gives whole seconds and stores them as **text**. Two consequences, both fatal to a keyset: every row written in the same second ties, and a stored `2026-08-07 10:24:32` compared against a bound `2026-08-07 10:24:32.000000` is a *string* comparison where the shorter value sorts first — so every row looked "before" the cursor and nothing was excluded.

What I take from it: `server_default` is not a default value, it is a fragment of SQL whose meaning belongs to the backend, and a column you intend to sort by should not have a representation you do not control. Setting the timestamp application-side as well makes the stored and compared values the same one.

## Server-side search, and where the vocabulary rule paid off

Moving search into the query meant the request had to name raw API statuses — `indexed`, `processed` — which is exactly the vocabulary the whole redesign keeps out of the UI.

The mapping went into `terminology.ts`, which is already the one module permitted to know both languages. The page sends a filter key; the module turns it into statuses. It also handled a detail I would otherwise have scattered: the "Processing" chip covers *two* backend statuses, and no page should have to know that.

Two smaller things: search needs debouncing once it is a request rather than an array filter, and `%` and `_` have to be escaped or a title containing them turns into a wildcard.

## What I executed from a spec versus actually designed

**Designed:** the three deletion semantics, refusing a delete mid-preparation, keyset over offset and the reasoning for it, and putting the filter mapping in the vocabulary module.

**Understood after being surprised:** that database cascades and ORM cascades are separate mechanisms; that SQLite ignores foreign keys by default; and the `server_default` timestamp representation problem. None of these were in my model beforehand.

**Executed from a spec:** the row-value comparison syntax and TanStack Query's `useInfiniteQuery` shape. I can explain both now, but I looked them up.

## What breaks first at real scale

**The status counts.** They are a `GROUP BY` over every matching document on every page request. At a hundred thousand documents that is the expensive part of the page, not the twenty-five rows. The fix is caching them or accepting approximate counts, and either is a bigger conversation than the query.

**`ILIKE '%term%'` cannot use an index.** It is a sequential scan wearing a search box. Real search means Postgres full-text or a trigram index — which is phase 15's territory anyway, since that phase is about retrieval quality.

**Deleting a large workspace is one statement and one transaction.** Cascading through millions of chunks holds locks for as long as it takes. Production systems do this as a background job that marks the tenant deleted immediately and reclaims rows in batches.

**The chat thread keeps every loaded page in memory.** Load earlier enough times and the browser holds the whole conversation, which is what pagination was supposed to avoid. Virtualized rendering is the answer, and it is not worth it yet.

**Deletion is immediate and total.** There is no undo and no trash. For a support knowledge base that is defensible; for anything with a compliance story it would need soft deletes and a retention window.

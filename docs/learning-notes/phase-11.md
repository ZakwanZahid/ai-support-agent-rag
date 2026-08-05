# Phase 11 — Tests and architecture docs

## What problem this phase solved

Two, and they're related.

The repo had 49 backend tests and zero frontend tests. That asymmetry says something unflattering: the backend was treated as the part worth protecting, and the frontend as the part you eyeball. It also meant every bug found during the redesign — the hydration race, the detached query observer, the tab-blur polling freeze — was found by a human driving the browser, and nothing stops any of them coming back.

The second problem was that the repo couldn't explain itself. Someone landing on it had to read code to work out what it did and why it was built that way. For a project whose whole purpose is being evaluated by strangers, that's the actual failure.

## The key design decision: what to test, and what not to

The instinct with a coverage number is to raise it. I deliberately didn't, and the reasoning is the interesting part of this phase.

Coverage sits at **7% overall**, but at **100% for `terminology.ts`**, **91% for the API client**, and **100% for `StatusBadge`**. That distribution is the decision.

The argument: unit tests are worth writing where logic can be wrong in ways that aren't obvious on screen. `terminology.ts` decides what every status label says, what colour it renders, where it sits on the progress timeline, and *whether the UI keeps polling* — get the last one wrong and documents either spin forever or stop updating before they finish. The API client decides what error message a user reads when anything fails. Both are pure logic with many branches, and both are load-bearing for the entire product.

By contrast, a unit test asserting that a card component renders a heading proves almost nothing. It doesn't catch layout breaking, it doesn't catch a wrong prop being passed two levels up, and it costs real time to write and maintain. What catches those is the end-to-end test.

So: **unit-test the logic, end-to-end the flow, and don't pad the middle.**

The tradeoff is real. A refactor that breaks a component in a way the e2e doesn't traverse would go unnoticed. I'd rather have that gap knowingly than a 60% coverage number made of tests that assert nothing.

## The test I'd actually point at in an interview

The terminology tests don't just check that `indexed` maps to `Ready`. They assert that **no forbidden API term appears in any user-facing string** — iterating every status and checking the label and description against a list of words the redesign exists to hide (`ingest`, `embedding`, `chunk`, `organization`, `knowledge base`, `citation`).

That's a test of the *rule*, not of the current data. If someone adds a status next year and writes "Ingesting…" as its label, the test fails and tells them why. A test asserting `expect(label).toBe("Ready")` would have passed.

The Playwright spec does the same thing at the other end: after completing the whole flow it reads the page text and asserts that no API vocabulary and **no UUID** ever reached the screen. The negative assertion is doing more work than the positive ones.

One nice property of writing it that way: the e2e also asserts there is no "Ingest" or "Index" button anywhere in the flow. If someone reintroduced the two-step interaction, that test fails even though the app would still work perfectly.

## What breaks first at real scale

**The e2e costs real money and real time.** It signs up a new user, uploads a document, and makes actual OpenAI embedding and chat calls — about 15 seconds and a fraction of a cent per run. At one flow that's fine. At thirty flows running on every pull request it's neither. The fix when it becomes a problem is to run the full path once and mock the model provider for the rest, or seed a prepared workspace and start most specs from there.

**It also writes to the real database.** Every run leaves an orphaned user, workspace, and document behind. Locally that's clutter; against a shared environment it's a slow leak. A proper setup gets a disposable database per run, or a teardown step — which the app can't currently do because **nothing is deletable** (limitation #14, Phase 14). That's a nice illustration of how a missing product feature turns into a testing problem.

**And the polling assumption is baked into the test.** The spec waits up to 90 seconds for a document to become Ready. When Phase 12 moves preparation into a real job queue, that wait becomes a queue wait, and the timeout will need revisiting.

## What I understood versus what I executed

Most of this I designed. The one part I'd flag as executed-from-spec rather than reasoned-from-first-principles is the **Vitest and Playwright configuration** — the `jsdom` environment, the coverage provider, the `webServer` block that reuses a running dev server. That's conventional setup I'd want to read properly rather than trust.

Two things I did have to reason about and would explain unprompted:

**The module identity failure.** Two API client tests failed with "expected APIError to be an instance of APIError", which reads like nonsense until you see why: `vi.resetModules()` plus a dynamic `import()` creates a *second copy* of the module with a *different class object*. `instanceof` compares identity, not shape. The fix was to take `APIError` from the same dynamic import as the client under test. Worth remembering because it applies to any module-level singleton — the same trap catches people mocking singletons in Jest.

**Why the coverage number is allowed to be bad.** Covered above, but it's the thing I'd most expect to be challenged on, and "we test where being wrong is invisible, and cover the rest by walking the real flow" is the answer.

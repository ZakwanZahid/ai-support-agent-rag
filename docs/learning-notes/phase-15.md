# Phase 15 — Measuring retrieval instead of guessing at it

## What problem this phase solved

Up to now every retrieval decision in this project was a guess with a good story attached. Chunk size 1200 with 200 overlap? Sounded reasonable. Vector-only search? Standard. Nothing anywhere could tell me whether any of it was working, or whether a change made it worse.

That is the actual gap. "I built a RAG app" and "I understand retrieval" differ by exactly this: whether you can answer *how do you know?*

## The harness came first, and that ordering was the point

The instruction was to build the eval before touching retrieval, and I now understand why it is stated so firmly. If I had made the chunking change first, it would have looked like an obvious win — the reasoning for it is genuinely good. I would have shipped it, and I would have shipped a regression with it, because two questions broke and nothing would have told me.

### Design decisions that turned out to matter

**Score documents, not chunks.** Chunk size is one of the things being tuned. If I counted chunk hits, halving the chunk size would double the chances of a "hit" and look like better retrieval while nothing improved.

**Grade sources, not answer text.** My first instinct was to store expected answers and compare. That needs a model to judge the comparison, and then the score moves when the *chat* model changes — which is not what I am measuring. Scoring "did the right document come back" isolates retrieval. I kept a crude substring check for expected facts as an optional pass, and I am deliberately not calling it answer quality.

**Tag questions by kind.** This is the decision I would defend hardest. Averages hide the interesting case. Direct lookups are easy and flatter any retriever; paraphrases and inference are where retrieval actually earns its keep. Splitting recall by kind is what let me see that structured chunking helped inference (0.857 → 0.929) while breaking literal lookups (1.000 → 0.667) — a change that looked flat-to-positive in the headline number.

**Score unanswerable questions separately.** Recall is undefined when no document is correct. Returning 0 punishes correct behaviour; returning 1 rewards retrieving anything. So they are excluded from the averages and their top scores are recorded instead, which is the evidence I would need to later choose a "nothing relevant" threshold.

**Cache the embeddings.** Not a nicety. The first run cost real money; every run since has cost nothing. An eval you avoid running because it is expensive is an eval that stops being run, and then you are back to guessing.

### The harness's first version was useless and I nearly missed it

The first run scored **recall@k = 1.0000**. My honest first reaction was that this was good news.

It was not. Six documents, chunk size larger than any of them, so each document was one chunk — and retrieving the top 5 of 6 documents means almost any expected document is in the results. The metric could not fail, so it could not measure anything.

**A metric that cannot go down is not a measurement.** I rebuilt the corpus to sixteen documents with deliberately confusable neighbours — refunds versus returns versus cancellations, all of which are "how do I get my money back" — before doing any retrieval work.

## What the measurements said, versus what I expected

I expected both changes to help. Here is what actually happened.

| | recall@k | MRR | precision@k | hit rate |
|---|---|---|---|---|
| Baseline (window chunks, vector only) | 0.9528 | 0.8899 | 0.2189 | 0.9623 |
| Structure-aware chunking | 0.9340 | 0.8553 | 0.3434 | 0.9434 |
| + hybrid retrieval | **0.9811** | 0.8805 | **0.3283** | **0.9811** |

**Structured chunking made overall recall worse.** Precision jumped (0.219 → 0.343, because chunks stopped being whole documents) and inference questions improved, but two literal-token questions broke outright — "kerbside drop point" and "pallet delivery" stopped finding their document. The reason is clear in hindsight and was not obvious to me beforehand: a rare word used to sit in a chunk that *was* the whole document, so the document's vector carried it. Split into sections, that word now sits in a small chunk whose embedding is dominated by whatever else the section is about.

**Hybrid retrieval, measured alone, did nothing.** On the original question set it moved recall and precision by exactly zero and cost MRR. If I had tested it on its own and stopped there, the correct conclusion would have been "not worth the migration".

That null result is what sent me back to the question set. Hybrid search claims to win on rare literal tokens — and my questions were all natural-language paraphrases, which is vector search's home ground. So I added six `literal` questions. With those in the set, the picture inverted: hybrid repaired both chunking regressions and took recall past the baseline.

**Neither change is right on its own.** That is the finding I did not expect and the one I would lead with in an interview. The eval did not confirm my plan; it corrected it twice.

## The thing I keep coming back to

I chose to *add* the literal questions rather than quietly rewrite the ones that made hybrid look useless. Editing the dataset until the change looks good is the obvious failure mode of having an eval at all, and it is invisible afterwards — the numbers still look rigorous. Adding a category, re-running every configuration against the new set, and reporting that hybrid did nothing on the old one is the difference between measurement and decoration.

## What I executed from a spec versus actually designed

**Designed:** the whole harness — document-level scoring, per-kind tagging, separate handling of unanswerable questions, embedding cache, and the decision to add rather than edit questions. Also the choice to measure chunking and hybrid separately instead of together, which is the only reason I know hybrid alone does nothing.

**Understood after being surprised:** that a fixed window larger than the document collapses to one chunk per document, and what that does to rare tokens. That was the mechanism behind both the precision gain and the literal regression, and I worked it out from the failures rather than predicting it.

**Executed from a spec:** reciprocal rank fusion — the `1/(k+rank)` formula and `k=60` are from the literature, not from me. I can explain why rank fusion avoids the unit-mismatch problem, but I did not derive the constant and nothing here is tuned to it. Also `websearch_to_tsquery`, `ts_rank`, and the GIN index: I can explain each choice now, and I looked all three up.

## What breaks first at real scale

**The corpus is sixteen short documents.** Every number here has a small denominator, so a single question is worth about two points of recall. It is enough to catch a regression and not enough to distinguish 0.97 from 0.98. A real eval needs hundreds of questions before those differences mean anything.

**The questions are mine, so they share my blind spots.** I wrote both the corpus and the questions about it, which is the friendliest possible test. Real questions come from real support logs and are messier, more ambiguous, and more often unanswerable.

**`ts_rank` does not use the GIN index for ordering.** The index finds matching rows; ranking them is a sequential pass over the matches. Fine at this size, a problem at millions of chunks, where the answer is a materialised rank or a different search backend.

**RRF's `k` and the vector/keyword weighting are untuned.** I now have the apparatus to tune them and did not, because with 57 questions I would be fitting the constant to the noise.

**No re-ranking.** A cross-encoder over the fused candidates is the obvious next lever, and the harness now exists to prove whether it earns its latency. That is the right order, and it is the order I got wrong instinctively at the start of this phase.

**Nothing measures the answer, only the retrieval.** A perfect retriever feeding a model that ignores the context still produces a wrong answer. Answer-level evaluation needs an LLM judge and a whole separate argument about trusting it.

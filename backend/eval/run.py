"""Run the retrieval eval and write a result file.

    python -m eval.run --label baseline
    python -m eval.run --compare eval/results/baseline.json

Needs a real Postgres (pgvector, for the vector search being measured) and an
OpenAI key. Embeddings are cached on disk, so the first run pays and later ones
are free unless the chunking changed.

Not part of `pytest`. The scoring arithmetic is unit-tested there; this makes
paid API calls and is run deliberately, for the same reason `e2e.yml` is
manual — an eval on every push becomes a bill and then gets switched off.
"""

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.db.session import SessionLocal
from app.embeddings.factory import get_embedding_provider
from app.llm.factory import get_chat_provider
from app.rag.context_builder import build_context
from app.rag.prompts import (
    GROUNDED_SUPPORT_SYSTEM_PROMPT,
    build_grounded_user_prompt,
)
from app.ingestion.chunking import chunk_document, chunk_text
from app.repositories.document_chunk_repository import DocumentChunkRepository
from eval.cache import CachingEmbeddingProvider
from eval.harness import (
    index_corpus,
    load_corpus,
    load_questions,
    run_questions,
    teardown,
)
from eval.scoring import compare, score


RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _git_revision() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Retrieval evaluation harness")
    parser.add_argument(
        "--label",
        default="run",
        help="Name for the result file, e.g. 'baseline' or 'hybrid'.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=settings.rag_top_k,
        help="Chunks retrieved per question.",
    )
    parser.add_argument(
        "--with-answers",
        action="store_true",
        help="Also generate answers and check for expected phrases. Costs chat calls.",
    )
    parser.add_argument(
        "--chunker",
        choices=("window", "structured"),
        default="structured",
        help="Which chunking strategy to index with. 'window' is the original.",
    )
    parser.add_argument(
        "--retrieval",
        choices=("vector", "hybrid"),
        default="vector",
        help="Vector-only search, or vector fused with keyword search.",
    )
    parser.add_argument(
        "--compare",
        type=Path,
        default=None,
        help="A previous result file to print deltas against.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Print the report without saving it.",
    )
    args = parser.parse_args(argv)

    if not settings.database_url.startswith("postgresql"):
        print(
            "This harness measures pgvector search and needs Postgres. "
            f"DATABASE_URL is {settings.database_url!r}.",
            file=sys.stderr,
        )
        return 2

    provider = CachingEmbeddingProvider(
        get_embedding_provider(),
        model=settings.embedding_model,
    )
    questions = load_questions()
    corpus = load_corpus()

    answerer = None
    if args.with_answers:
        chat = get_chat_provider()

        def answerer(question: str, matches: list) -> str:
            context = build_context(matches, max_chars=settings.rag_max_context_chars)
            if not context.context:
                return ""
            return chat.generate_answer(
                GROUNDED_SUPPORT_SYSTEM_PROMPT,
                build_grounded_user_prompt(question=question, context=context.context),
            )

    db = SessionLocal()
    indexed = None
    try:
        indexed = index_corpus(
            db,
            embed_texts=provider.embed_texts,
            corpus=corpus,
            chunker=chunk_text if args.chunker == "window" else chunk_document,
        )
        repository = DocumentChunkRepository(db)
        search = None
        if args.retrieval == "hybrid":
            def search(*, organization_id, knowledge_base_id, query_embedding, top_k, query_text):
                return repository.hybrid_search(
                    organization_id=organization_id,
                    knowledge_base_id=knowledge_base_id,
                    query_text=query_text,
                    query_embedding=query_embedding,
                    top_k=top_k,
                )

        results = run_questions(
            db,
            indexed,
            questions,
            embed_query=provider.embed_query,
            top_k=args.top_k,
            search=search,
            answerer=answerer,
        )
    finally:
        provider.save()
        if indexed is not None:
            teardown(db, indexed.organization_id)
        db.close()

    report = score(results)
    payload = {
        "label": args.label,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "git_revision": _git_revision(),
        "config": {
            "embedding_model": settings.embedding_model,
            "chat_model": settings.chat_model if args.with_answers else None,
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "top_k": args.top_k,
            "retrieval": args.retrieval,
            "chunker": args.chunker,
            "python": platform.python_version(),
        },
        "corpus": {
            "documents": len(corpus),
            "chunks": indexed.chunk_count,
            "chunks_per_document": indexed.chunks_per_document,
        },
        "summary": report.as_dict(),
        "per_question": [
            {
                "id": result.question_id,
                "kind": result.kind,
                "expected": result.expected_documents,
                "retrieved": result.retrieved_documents,
                "top_score": (
                    round(result.top_score, 4) if result.top_score is not None else None
                ),
                "missing_phrases": result.missing_phrases,
            }
            for result in results
        ],
    }

    _print(payload, provider)

    if args.compare is not None:
        previous = json.loads(args.compare.read_text(encoding="utf-8"))
        print(f"\nAgainst {previous.get('label', args.compare.name)}:")
        for line in compare(previous["summary"], payload["summary"]):
            print(f"  {line}")

    if not args.no_write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        destination = RESULTS_DIR / f"{args.label}.json"
        destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote {destination}")

    return 0


def _print(payload: dict, provider: CachingEmbeddingProvider) -> None:
    summary = payload["summary"]
    corpus = payload["corpus"]
    print(f"\n{payload['label']}  ({payload['config']['retrieval']}, "
          f"top_k={payload['config']['top_k']}, "
          f"chunk_size={payload['config']['chunk_size']})")
    print(f"  corpus            {corpus['documents']} documents, {corpus['chunks']} chunks")
    print(f"  embeddings        {provider.hits} cached, {provider.misses} fetched")
    print(f"  questions         {summary['answerable']} answerable, "
          f"{summary['unanswerable']} unanswerable")
    print(f"  recall@k          {summary['recall_at_k']:.4f}")
    print(f"  MRR               {summary['mrr']:.4f}")
    print(f"  precision@k       {summary['precision_at_k']:.4f}")
    print(f"  hit rate          {summary['hit_rate']:.4f}")
    print("  recall by kind")
    for kind, value in summary["by_kind"].items():
        print(f"    {kind:<16} {value:.4f}")
    if summary["failures"]:
        print(f"  retrieved nothing relevant: {', '.join(summary['failures'])}")
    if summary["phrase_failures"]:
        print(f"  answer missing a fact:      {', '.join(summary['phrase_failures'])}")
    scores = summary["unanswerable_top_scores"]
    if scores:
        print(f"  unanswerable top scores     {scores}")


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Create a traceable automatic relevance review from a research plan and raw signals."""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


STOP_WORDS = {"a", "an", "and", "app", "for", "in", "of", "on", "the", "through", "to", "with", "without"}


def tokens(value: str) -> set[str]:
    return {word.lower() for word in re.findall(r"[a-zA-Z0-9]{3,}", value) if word.lower() not in STOP_WORDS}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--minimum", type=int, default=30)
    args = parser.parse_args()
    plan = json.loads((args.case_dir / "research-plan.json").read_text(encoding="utf-8"))
    queries = {row["query"]: row for row in plan["queries"]}
    raw_path = args.case_dir / "evidence" / "public-signals" / "raw-signals.jsonl"
    rows = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    candidates = []
    for row in rows:
        query = queries.get(row.get("query"), {})
        parent_terms = tokens(str(row.get("query", "")))
        variant = str(row.get("query_variant", row.get("query", "")))
        variant_terms = tokens(variant)
        text = f"{row.get('title', '')} {row.get('body', '')}"
        text_terms = tokens(text)
        parent_overlap = len(parent_terms & text_terms)
        variant_overlap = len(variant_terms & text_terms)
        exact_variant = variant.lower() in text.lower()
        # A row must match at least two words from its declared task phrase.  This filters
        # broad search-engine collisions while retaining a repeatable rationale.
        if parent_overlap < 2 or variant_overlap < 1:
            continue
        score = parent_overlap * 3 + variant_overlap * 2 + (3 if exact_variant else 0)
        if row.get("source") == "seed_page":
            score += 1
        candidates.append({
            "url": row.get("url"),
            "task_link": f"{query.get('dimension', 'unknown')}: {query.get('why', 'No rationale saved.')}",
            "signal": query.get("dimension", "unknown"),
            "source": row.get("source"),
            "community": row.get("community"),
            "query": row.get("query"),
            "query_variant": variant,
            "title": row.get("title"),
            "relevance_score": score,
            "summary": re.sub(r"\s+", " ", text).strip()[:300],
        })
    candidates.sort(key=lambda row: (-row["relevance_score"], row["url"]))
    # Avoid letting one query dominate the whole evidence set before each dimension has
    # been represented.  The remaining slots are filled by score.
    selected, per_dimension = [], defaultdict(int)
    for row in candidates:
        if len(selected) >= args.minimum:
            break
        dimension = row["signal"]
        if per_dimension[dimension] >= max(3, args.minimum // 3):
            continue
        selected.append(row)
        per_dimension[dimension] += 1
    review = {
        "method": "Automatic Codex relevance audit: retain records with at least two task-phrase token matches and one executed-variant match; rank by overlap and preserve the original query, executed variant, source, URL, and short summary.",
        "input_records": len(rows),
        "candidate_records": len(candidates),
        "accepted_records": selected,
        "limitations": "Lexical relevance is not proof of demand. Rankings are suitable for evidence triage; claims about payment, adoption, or clinical benefit still require direct evidence.",
    }
    output = args.case_dir / "evidence" / "relevance-review.json"
    output.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(selected)} accepted records from {len(candidates)} candidates to {output}")


if __name__ == "__main__":
    main()

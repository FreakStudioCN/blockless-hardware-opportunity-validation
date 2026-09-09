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


def core_term_hits(core_terms: list[str], text: str) -> list[str]:
    """Core terms must appear as whole words; 'meds' must not be satisfied by 'immediately'."""
    lowered = text.lower()
    return [term for term in core_terms if re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", lowered)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--minimum", type=int, default=30)
    parser.add_argument("--maximum", type=int, default=40, help="Cap on accepted records so writers read every record in full")
    args = parser.parse_args()
    plan = json.loads((args.case_dir / "research-plan.json").read_text(encoding="utf-8"))
    queries = {row["query"]: row for row in plan["queries"]}
    # Task-phrase token overlap alone keeps "sleep after" / "processing equipment" style
    # collisions.  Every accepted record must additionally contain one of the plan's core
    # terms (the nouns the idea cannot be described without) in its title or body.
    core_terms = [str(term).strip().lower() for term in plan.get("core_terms", []) if str(term).strip()]
    if not core_terms:
        raise SystemExit("research-plan.json must list core_terms (the words the idea cannot be described without)")
    raw_path = args.case_dir / "evidence" / "public-signals" / "raw-signals.jsonl"
    rows = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    candidates, rejected_no_core_term = [], 0
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
        hits = core_term_hits(core_terms, text)
        if not hits:
            rejected_no_core_term += 1
            continue
        score = parent_overlap * 3 + variant_overlap * 2 + (3 if exact_variant else 0) + 2 * len(hits)
        if row.get("source") == "seed_page":
            score += 1
        body = re.sub(r"\s+", " ", text).strip()
        candidates.append({
            "url": row.get("url"),
            "task_link": f"{query.get('dimension', 'unknown')}: {query.get('why', 'No rationale saved.')}",
            "signal": query.get("dimension", "unknown"),
            "source": row.get("source"),
            "community": row.get("community"),
            "query": row.get("query"),
            "query_variant": variant,
            "title": row.get("title"),
            "published_at": row.get("published_at", ""),
            "relevance_score": score,
            "core_term_hits": hits,
            "summary": body[:300],
            # Writers and citation reviewers must work from the full collected text, not the
            # 300-character summary: paraphrases written from summaries invent details.
            "body": body,
        })
    candidates.sort(key=lambda row: (-row["relevance_score"], row["url"]))
    # Avoid letting one query dominate the whole evidence set before each dimension has
    # been represented.  The remaining slots are filled by score.  One URL appears once.
    selected, per_dimension, seen_urls = [], defaultdict(int), set()
    for row in candidates:
        if len(selected) >= args.maximum:
            break
        if row["url"] in seen_urls:
            continue
        dimension = row["signal"]
        if per_dimension[dimension] >= max(3, args.maximum // 3):
            continue
        selected.append(row)
        seen_urls.add(row["url"])
        per_dimension[dimension] += 1
    review = {
        "method": "Automatic Codex relevance audit: retain records with at least two task-phrase token matches, one executed-variant match and at least one whole-word core term from research-plan.json; rank by overlap (+2 per core-term hit); one record per URL; preserve the original query, executed variant, source, URL, publish date, short summary and full collected body.",
        "core_terms": core_terms,
        "input_records": len(rows),
        "rejected_no_core_term": rejected_no_core_term,
        "candidate_records": len(candidates),
        "accepted_records": selected,
        "limitations": "Lexical relevance is not proof of demand. Rankings are suitable for evidence triage; claims about payment, adoption, or clinical benefit still require direct evidence.",
    }
    output = args.case_dir / "evidence" / "relevance-review.json"
    output.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(selected)} accepted records from {len(candidates)} candidates ({rejected_no_core_term} lexical matches rejected for missing core terms) to {output}")
    if len(selected) < args.minimum:
        raise SystemExit(f"Only {len(selected)} accepted records; the research gate requires {args.minimum}")


if __name__ == "__main__":
    main()

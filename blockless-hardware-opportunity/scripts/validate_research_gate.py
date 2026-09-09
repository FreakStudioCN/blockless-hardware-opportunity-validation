#!/usr/bin/env python3
"""Block client deliverables unless the problem-space research gate has passed."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


STOP_WORDS = {"a", "an", "and", "app", "for", "in", "of", "on", "the", "through", "to", "with", "without"}
MAX_QUERY_WORDS = 5
MIN_CORE_TERMS = 3


def content_words(query: str) -> list[str]:
    return [word.lower() for word in re.findall(r"[a-zA-Z0-9]+", query) if word.lower() not in STOP_WORDS]


DIMENSIONS = {
    "user_scenarios",
    "desired_outcomes",
    "current_alternatives",
    "product_form",
    "engineering_constraints",
    "commercial_constraints",
}


def read_json(path: Path, errors: list[str]) -> object | None:
    if not path.is_file():
        errors.append(f"Missing required artifact: {path.name}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"Cannot read {path.name}: {error}")
        return None


def nonempty_list(value: object) -> bool:
    return isinstance(value, list) and any(isinstance(item, str) and item.strip() for item in value)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", type=Path, required=True)
    args = parser.parse_args()
    case_dir = args.case_dir
    errors: list[str] = []

    plan = read_json(case_dir / "research-plan.json", errors)
    if isinstance(plan, dict):
        product = plan.get("product")
        if not isinstance(product, dict) or not str(product.get("name", "")).strip() or not str(product.get("description", "")).strip():
            errors.append("research-plan.json must retain non-empty product.name and product.description")
        space = plan.get("problem_space")
        if not isinstance(space, dict):
            errors.append("research-plan.json must contain problem_space")
        else:
            for dimension in DIMENSIONS:
                if not nonempty_list(space.get(dimension)):
                    errors.append(f"problem_space.{dimension} must be a non-empty list")
        queries = plan.get("queries")
        if not isinstance(queries, list) or len(queries) < 8:
            errors.append("research-plan.json must contain at least 8 targeted queries")
        elif len({str(item.get("dimension", "")) for item in queries if isinstance(item, dict)}) < 4:
            errors.append("Targeted queries must cover at least 4 problem-space dimensions")
        elif any(not isinstance(item, dict) or not str(item.get("query", "")).strip() or not str(item.get("why", "")).strip() for item in queries):
            errors.append("Every query needs non-empty query and why fields")
        else:
            # Public search APIs match the phrase; sentences of six or more content words
            # return nothing and the bigram fallback then searches something else entirely.
            for item in queries:
                if len(content_words(str(item.get("query", "")))) > MAX_QUERY_WORDS:
                    errors.append(f"Query too long ({MAX_QUERY_WORDS} content words max, 2-3 is best): {item.get('query')}")
        core_terms = plan.get("core_terms")
        if not nonempty_list(core_terms) or len([term for term in core_terms if isinstance(term, str) and term.strip()]) < MIN_CORE_TERMS:
            errors.append(f"research-plan.json must list at least {MIN_CORE_TERMS} core_terms (words the idea cannot be described without) for the relevance review")

    log = read_json(case_dir / "evidence" / "public-signals" / "collection-log.json", errors)
    if isinstance(log, dict):
        result_rows = log.get("results")
        if not int(log.get("records", 0) or 0):
            errors.append("Collection log contains no records")

    raw = case_dir / "evidence" / "public-signals" / "raw-signals.jsonl"
    if not raw.is_file() or not raw.read_text(encoding="utf-8").strip():
        errors.append("Missing or empty raw-signals.jsonl")
    else:
        try:
            raw_rows = [json.loads(line) for line in raw.read_text(encoding="utf-8").splitlines() if line.strip()]
            non_reddit_communities = {str(row.get("community", "")).strip() for row in raw_rows if str(row.get("source", "")) != "reddit" and str(row.get("community", "")).strip()}
            if len(non_reddit_communities) < 3:
                errors.append("Collection needs records from at least 3 independent non-Reddit communities or domains; log blocked sources and use permitted replacements")
        except json.JSONDecodeError as error:
            errors.append(f"Cannot parse raw-signals.jsonl: {error}")
    read_json(case_dir / "evidence" / "clusters" / "summary.json", errors)

    review = read_json(case_dir / "evidence" / "relevance-review.json", errors)
    if isinstance(review, dict):
        accepted = review.get("accepted_records")
        if not isinstance(accepted, list) or len(accepted) < 30:
            errors.append("relevance-review.json must document at least 30 accepted, task-relevant records")
        elif any(not isinstance(row, dict) or not str(row.get("url", "")).strip() or not str(row.get("task_link", "")).strip() or not str(row.get("signal", "")).strip() for row in accepted):
            errors.append("Each accepted record needs url, task_link, and signal")
        elif any(not str(row.get("body", "")).strip() for row in accepted):
            errors.append("Each accepted record needs the full collected body; re-run review_relevance.py")
        elif len({str(row.get("url")) for row in accepted}) != len(accepted):
            errors.append("relevance-review.json repeats a URL; each record must be cited once")
        if not nonempty_list(review.get("core_terms")):
            errors.append("relevance-review.json was produced without core_terms; re-run review_relevance.py")

    if errors:
        print("RESEARCH GATE: BLOCKED", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        raise SystemExit(1)
    print("RESEARCH GATE: PASSED")


if __name__ == "__main__":
    main()

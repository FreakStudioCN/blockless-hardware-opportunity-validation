#!/usr/bin/env python3
"""Find traceable startup-opportunity evidence matching a supplied keyword set."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

DEFAULT_ROOT = Path(r"E:\startup-opportunity-validation")


def contains_terms(values: list[str], terms: list[str]) -> bool:
    haystack = " ".join(values).lower()
    return any(term in haystack for term in terms)


def read_matches(path: Path, terms: list[str], fields: list[str], limit: int) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            if contains_terms([row.get(field, "") for field in fields], terms):
                matches.append(row)
                if len(matches) >= limit:
                    break
    return matches


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keywords", required=True, help="Comma-separated words or phrases")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    terms = [term.strip().lower() for term in args.keywords.split(",") if term.strip()]
    if not terms:
        raise SystemExit("Provide at least one keyword")
    cluster_file = args.root / "knowledge-pack" / "evidence-clusters.csv"
    evidence_file = args.root / "research" / "data" / "01_deduplicated_evidence.csv"
    result = {
        "keywords": terms,
        "source_root": str(args.root),
        "cluster_matches": read_matches(cluster_file, terms, ["terms", "representative_titles"], args.limit),
        "evidence_matches": read_matches(evidence_file, terms, ["title", "domain", "matched_queries"], args.limit),
        "limitation": "Keyword candidates from a cross-category, HN-heavy corpus are not hardware demand proof.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}; clusters={len(result['cluster_matches'])}; evidence={len(result['evidence_matches'])}")


if __name__ == "__main__":
    main()

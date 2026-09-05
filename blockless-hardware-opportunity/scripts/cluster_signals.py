#!/usr/bin/env python3
"""Deduplicate and cluster collected public-signal records without downloading a model."""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import TfidfVectorizer


def normalized(value: str) -> str:
    return re.sub(r"\W+", " ", value.lower()).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    records = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    unique, seen = [], set()
    for row in records:
        key = row.get("url") or normalized(row.get("title", ""))
        if key and key not in seen:
            seen.add(key)
            unique.append(row)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if not unique:
        (args.output_dir / "summary.json").write_text(json.dumps({"raw_records": len(records), "unique_records": 0}, indent=2), encoding="utf-8")
        return
    documents = [f"{row.get('title', '')} {row.get('body', '')}" for row in unique]
    clusters = 1 if len(unique) < 4 else max(3, min(12, round(math.sqrt(len(unique)))))
    matrix = TfidfVectorizer(stop_words="english", max_features=6000, ngram_range=(1, 2)).fit_transform(documents)
    labels = [0] * len(unique) if clusters == 1 else MiniBatchKMeans(n_clusters=clusters, random_state=42, n_init=10).fit_predict(matrix).tolist()
    grouped: dict[int, list[dict]] = defaultdict(list)
    for row, label in zip(unique, labels):
        grouped[label].append(row)
    with (args.output_dir / "clusters.csv").open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=["cluster_id", "record_count", "communities", "sources", "representative_titles", "representative_urls"])
        writer.writeheader()
        for label, rows in sorted(grouped.items(), key=lambda item: -len(item[1])):
            writer.writerow({"cluster_id": f"cluster-{label:02d}", "record_count": len(rows), "communities": "; ".join(Counter(row["community"] for row in rows).most_common(5)[i][0] for i in range(min(5, len(Counter(row["community"] for row in rows))))), "sources": "; ".join(sorted({row["source"] for row in rows})), "representative_titles": " | ".join(row["title"][:160] for row in rows[:5]), "representative_urls": " | ".join(row["url"] for row in rows[:5])})
    summary = {"raw_records": len(records), "unique_records": len(unique), "dedupe_rate": round(1 - len(unique) / len(records), 4) if records else 0, "cluster_count": clusters, "source_counts": dict(Counter(row["source"] for row in unique)), "community_counts": dict(Counter(row["community"] for row in unique).most_common(25)), "limitations": "Clusters group similar language; human review is required before assigning a user problem or paid demand."}
    (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()

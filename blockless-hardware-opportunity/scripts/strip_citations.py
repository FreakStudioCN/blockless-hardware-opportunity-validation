#!/usr/bin/env python3
"""Produce client deliverables from the citation-reviewed internal versions by removing [n] markers."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


INTERNAL_DIR = Path("evidence") / "internal-with-citations"
CITATION = re.compile(r"[ 　]*(?:\[\d+\])+")
SPACE_BEFORE_PUNCTUATION = re.compile(r"[ 　]+([。，；：！？）」])")
# Research-internal vocabulary that must never reach a creator.
CLIENT_BANNED = ["词法", "误命中", "token", "429", "相关性审核", "候选记录", "聚类", "TF-IDF", "KMeans", "种子页", "门禁",
                 "评估结果", "通过/未通过", "审判", "暂不推进", "Kill", "楔子", "证伪", "skill", "簇", "=====", "CHANGELOG"]


def strip(text: str) -> str:
    text = CITATION.sub("", text)
    return SPACE_BEFORE_PUNCTUATION.sub(r"\1", text)


def banned_words(text: str) -> list[str]:
    """CJK terms match as substrings; ASCII terms match as whole, case-sensitive words so product
    names such as "Skills Manager" or "Kill Bill" are not caught by "skill" / "Kill"."""
    hits = []
    for word in CLIENT_BANNED:
        if word.isascii() and word.isalpha():
            if re.search(r"(?<![A-Za-z])" + re.escape(word) + r"(?![A-Za-z])", text):
                hits.append(word)
        elif word in text:
            hits.append(word)
    return hits


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", type=Path, required=True)
    args = parser.parse_args()
    internal = sorted((args.case_dir / INTERNAL_DIR).glob("*.md"))
    internal = [path for path in internal if path.name != "CHANGELOG.md"]
    if len(internal) != 4:
        raise SystemExit(f"Expected the four internal Markdown deliverables in {INTERNAL_DIR}; found {len(internal)}")
    errors = []
    for path in internal:
        text = strip(path.read_text(encoding="utf-8"))
        if re.search(r"\[\d+\]", text):
            errors.append(f"{path.name}: citation markers survived stripping")
        hits = banned_words(text)
        if hits:
            errors.append(f"{path.name}: research jargon must be rewritten for the creator: {hits}")
        (args.case_dir / path.name).write_text(text, encoding="utf-8")
    if errors:
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        raise SystemExit(1)
    print(f"Wrote {len(internal)} client files without citation markers to {args.case_dir}")


if __name__ == "__main__":
    main()

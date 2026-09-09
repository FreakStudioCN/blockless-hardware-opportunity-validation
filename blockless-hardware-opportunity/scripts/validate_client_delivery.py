#!/usr/bin/env python3
"""Verify that a passed research case has complete, citation-reviewed, renderable client deliverables."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from strip_citations import INTERNAL_DIR, banned_words, strip


PNG = b"\x89PNG\r\n\x1a\n"
CITATION = re.compile(r"\[(\d+)\]")
# Last line of evidence/citation-review.md, e.g. "复核结果：引用 87 处，OK 87，STRETCH 0，WRONG 0"
REVIEW_SUMMARY = re.compile(r"复核结果[:：]\s*引用\s*(\d+)\s*处[,，]\s*OK\s*(\d+)[,，]\s*STRETCH\s*(\d+)[,，]\s*WRONG\s*(\d+)")


def one(paths: list[Path], label: str, errors: list[str]) -> Path | None:
    if len(paths) != 1:
        errors.append(f"Expected exactly one {label}; found {len(paths)}")
        return None
    return paths[0]


def check_citations(root: Path, client_files: list[Path], errors: list[str]) -> None:
    """Every client file must be the stripped copy of a reviewed internal file whose [n] all resolve."""
    review_path = root / "evidence" / "relevance-review.json"
    if not review_path.is_file():
        errors.append("Missing evidence/relevance-review.json")
        return
    accepted = len(json.loads(review_path.read_text(encoding="utf-8")).get("accepted_records", []))
    internal_dir = root / INTERNAL_DIR
    newest_internal = 0.0
    for client in client_files:
        internal = internal_dir / client.name
        if not internal.is_file():
            errors.append(f"Missing internal version with citations: {INTERNAL_DIR / client.name}")
            continue
        newest_internal = max(newest_internal, internal.stat().st_mtime)
        text = internal.read_text(encoding="utf-8")
        numbers = [int(number) for number in CITATION.findall(text)]
        if not numbers and "共创路线图" not in internal.name:
            errors.append(f"{internal.name} cites no records; every 我们看见 claim must carry [n]")
        bad = sorted({number for number in numbers if number < 1 or number > accepted})
        if bad:
            errors.append(f"{internal.name} cites records that do not exist in relevance-review.json: {bad}")
        if strip(text) != client.read_text(encoding="utf-8"):
            errors.append(f"{client.name} differs from its internal version; regenerate with strip_citations.py after the citation review")
        hits = banned_words(client.read_text(encoding="utf-8"))
        if hits:
            errors.append(f"{client.name} contains research jargon: {hits}")
    review = root / "evidence" / "citation-review.md"
    if not review.is_file():
        errors.append("Missing evidence/citation-review.md: an independent citation review is mandatory before delivery")
        return
    summaries = REVIEW_SUMMARY.findall(review.read_text(encoding="utf-8"))
    if not summaries:
        errors.append("citation-review.md has no summary line of the form 复核结果：引用 N 处，OK a，STRETCH b，WRONG c")
        return
    total, ok, stretch, wrong = (int(value) for value in summaries[-1])
    if stretch or wrong or ok != total:
        errors.append(f"Latest citation review still reports STRETCH {stretch} / WRONG {wrong}; fix the text and review again")
    if review.stat().st_mtime + 1 < newest_internal:
        errors.append("Internal deliverables changed after the latest citation review; review again")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", type=Path, required=True)
    args = parser.parse_args()
    root, errors = args.case_dir, []
    email = one(list(root.glob("*_客户邮件草稿_研究门禁版.md")), "client email Markdown", errors)
    human_email = one(list(root.glob("*_客户邮件草稿_人味版.md")), "human-tone client email Markdown", errors)
    roadmap = one(list(root.glob("*_共创路线图.md")), "co-creation roadmap", errors)
    report = one(list(root.glob("*_机会验证报告*.md")), "client report Markdown", errors)
    pdf = one(list(root.glob("*_机会验证报告*.pdf")), "client report PDF", errors)
    preview = root / "evidence" / "pdf-render-preview.png"
    for path, label in ((email, "email"), (human_email, "human-tone email"), (roadmap, "roadmap"), (report, "report")):
        if path and (not path.read_text(encoding="utf-8").strip()):
            errors.append(f"Client {label} is empty")
    if report and len(report.read_text(encoding="utf-8")) < 1500:
        errors.append("Client report is too short; require a full opportunity report, not a research summary")
    client_files = [path for path in (email, human_email, roadmap, report) if path]
    if len(client_files) == 4:
        check_citations(root, client_files, errors)
    if pdf:
        data = pdf.read_bytes()
        if not data.startswith(b"%PDF-") or len(data) < 1000:
            errors.append("PDF is missing a valid header or is unexpectedly small")
        if b"/Type /Page" not in data:
            errors.append("PDF does not contain a page object")
        if data.count(b"/Type /Page") < 2:
            errors.append("PDF must contain at least two rendered pages")
        if report and report.stat().st_mtime > pdf.stat().st_mtime + 1:
            errors.append("Client report Markdown is newer than the PDF; render again")
    if not preview.is_file() or preview.stat().st_size < 1000 or not preview.read_bytes().startswith(PNG):
        errors.append("Missing valid PNG render preview at evidence/pdf-render-preview.png")
    if errors:
        print("CLIENT DELIVERY: BLOCKED", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        raise SystemExit(1)
    print("CLIENT DELIVERY: PASSED")


if __name__ == "__main__":
    main()

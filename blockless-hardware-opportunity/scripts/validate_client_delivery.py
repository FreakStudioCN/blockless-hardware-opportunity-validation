#!/usr/bin/env python3
"""Verify that a passed research case has complete, renderable client deliverables."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


PNG = b"\x89PNG\r\n\x1a\n"


def one(paths: list[Path], label: str, errors: list[str]) -> Path | None:
    if len(paths) != 1:
        errors.append(f"Expected exactly one {label}; found {len(paths)}")
        return None
    return paths[0]


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
    if pdf:
        data = pdf.read_bytes()
        if not data.startswith(b"%PDF-") or len(data) < 1000:
            errors.append("PDF is missing a valid header or is unexpectedly small")
        if b"/Type /Page" not in data:
            errors.append("PDF does not contain a page object")
        if data.count(b"/Type /Page") < 2:
            errors.append("PDF must contain at least two rendered pages")
    if not preview.is_file() or preview.stat().st_size < 1000 or not preview.read_bytes().startswith(PNG):
        errors.append("Missing valid PNG render preview at evidence/pdf-render-preview.png")
    if errors:
        print("CLIENT DELIVERY: BLOCKED", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        raise SystemExit(1)
    print("CLIENT DELIVERY: PASSED")


if __name__ == "__main__":
    main()

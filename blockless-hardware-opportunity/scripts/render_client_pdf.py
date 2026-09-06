#!/usr/bin/env python3
"""Render a Markdown client deliverable as a printable PDF using local Edge."""
from __future__ import annotations

import argparse
import html
import re
import subprocess
import tempfile
from pathlib import Path


EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


def markdown_html(markdown: str) -> str:
    parts, in_list, in_table = [], False, False
    def close_blocks() -> None:
        nonlocal in_list, in_table
        if in_list:
            parts.append("</ul>")
            in_list = False
        if in_table:
            parts.append("</tbody></table>")
            in_table = False
    for line in markdown.splitlines():
        if line.startswith("# "):
            close_blocks()
            parts.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            close_blocks()
            parts.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                continue
            if not in_table:
                close_blocks()
                parts.append("<table><thead><tr>" + "".join(f"<th>{html.escape(cell)}</th>" for cell in cells) + "</tr></thead><tbody>")
                in_table = True
            else:
                parts.append("<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in cells) + "</tr>")
        elif re.match(r"^- ", line):
            if in_table: close_blocks()
            if not in_list: parts.append("<ul>"); in_list = True
            parts.append(f"<li>{html.escape(line[2:])}</li>")
        elif not line.strip():
            close_blocks()
        else:
            close_blocks()
            parts.append(f"<p>{html.escape(line)}</p>")
    close_blocks()
    return """<!doctype html><html><meta charset=\"utf-8\"><style>
      @page { size: A4; margin: 18mm 16mm; }
      body { font-family: 'Microsoft YaHei', 'SimSun', sans-serif; color:#1b2638; font-size:10.5pt; line-height:1.65; }
      h1 { font-size:23pt; line-height:1.25; color:#12375b; margin:0 0 18px; }
      h2 { font-size:14pt; color:#0c6b75; margin:23px 0 8px; border-bottom:1px solid #d5e3e7; padding-bottom:4px; }
      p { margin:0 0 10px; } li { margin:0 0 6px; } ul { padding-left:22px; }
      table { border-collapse:collapse; width:100%; margin:8px 0 14px; } th,td { border:1px solid #cbd9df; padding:6px; text-align:left; vertical-align:top; } th { background:#edf5f6; color:#12375b; }
    </style><body>""" + "\n".join(parts) + "</body></html>"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preview", type=Path, help="PNG render preview saved for delivery validation")
    args = parser.parse_args()
    if not EDGE.is_file():
        raise SystemExit(f"Microsoft Edge not found at {EDGE}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="blockless-pdf-") as temp:
        temp_path = Path(temp)
        source = temp_path / "document.html"
        source.write_text(markdown_html(args.input.read_text(encoding="utf-8")), encoding="utf-8")
        if args.preview:
            args.preview.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run([str(EDGE), "--headless", "--disable-gpu", f"--user-data-dir={temp_path / 'preview-profile'}", "--window-size=1240,1754", f"--screenshot={args.preview.resolve()}", source.resolve().as_uri()], check=True, capture_output=True, timeout=60)
        subprocess.run([str(EDGE), "--headless", "--disable-gpu", f"--user-data-dir={temp_path / 'profile'}", f"--print-to-pdf={args.output.resolve()}", source.resolve().as_uri()], check=True, capture_output=True, timeout=60)
    if not args.output.is_file() or args.output.stat().st_size < 1000:
        raise SystemExit("PDF was not created or is unexpectedly small")
    if args.preview and (not args.preview.is_file() or args.preview.stat().st_size < 1000):
        raise SystemExit("PDF preview was not created or is unexpectedly small")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()

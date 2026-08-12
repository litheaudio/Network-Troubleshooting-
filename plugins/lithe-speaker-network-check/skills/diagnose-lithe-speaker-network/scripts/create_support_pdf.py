#!/usr/bin/env python3
"""Render the redacted Markdown support report as a dependency-free PDF."""

from __future__ import annotations

import argparse
import re
import sys
import textwrap
from pathlib import Path


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
LEFT = 54
RIGHT = 54
TOP = 100
BOTTOM = 52
BODY_SIZE = 9.5
LINE_HEIGHT = 13
MAX_BYTES = 2 * 1024 * 1024


def plain(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    text = re.sub(r"\\([`*\[\]()<>])", r"\1", text)
    text = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u2011", "-")
    return text.encode("latin-1", errors="replace").decode("latin-1")


def pdf_escape(text: str) -> str:
    return plain(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def text_cmd(text: str, x: float, y: float, size: float = BODY_SIZE, bold: bool = False,
             colour: tuple[float, float, float] = (0.12, 0.12, 0.12)) -> str:
    font = "F2" if bold else "F1"
    r, g, b = colour
    return f"BT /{font} {size:g} Tf {r:g} {g:g} {b:g} rg 1 0 0 1 {x:g} {y:g} Tm ({pdf_escape(text)}) Tj ET"


def wrapped(text: str, width: int = 94) -> list[str]:
    return textwrap.wrap(plain(text), width=width, break_long_words=False, break_on_hyphens=False) or [""]


def render_pages(markdown: str) -> list[str]:
    pages: list[list[str]] = []
    current: list[str] = []
    y = PAGE_HEIGHT - TOP

    def start_page() -> None:
        nonlocal current, y
        current = [
            "q 0.91 0.46 0.13 rg 0 782 595 60 re f Q",
            text_cmd("LITHE AUDIO", LEFT, 810, 18, True, (1, 1, 1)),
            text_cmd("Network Diagnostic Support Report", LEFT, 791, 10, False, (1, 1, 1)),
        ]
        pages.append(current)
        y = PAGE_HEIGHT - TOP

    def ensure(lines: int = 1) -> None:
        nonlocal y
        if y - lines * LINE_HEIGHT < BOTTOM:
            start_page()

    start_page()
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line or line.startswith("# "):
            continue
        if line.startswith("## "):
            ensure(3)
            y -= 8
            current.append("q 0.91 0.46 0.13 RG 0.8 w 54 %g m 541 %g l S Q" % (y + 5, y + 5))
            current.append(text_cmd(line[3:], LEFT, y - 9, 12.5, True, (0.18, 0.18, 0.18)))
            y -= 28
            continue
        is_bullet = line.startswith("- ")
        body = line[2:] if is_bullet else line
        lines = wrapped(body, 88 if is_bullet else 94)
        ensure(len(lines) + 1)
        for index, part in enumerate(lines):
            prefix = "- " if is_bullet and index == 0 else "  " if is_bullet else ""
            current.append(text_cmd(prefix + part, LEFT + (8 if is_bullet else 0), y))
            y -= LINE_HEIGHT
        y -= 3

    total = len(pages)
    for number, commands in enumerate(pages, start=1):
        commands.append("q 0.75 0.75 0.75 RG 0.5 w 54 42 m 541 42 l S Q")
        commands.append(text_cmd("Copyright Lithe Audio 2026", LEFT, 27, 8, False, (0.4, 0.4, 0.4)))
        commands.append(text_cmd(f"Page {number} of {total}", 485, 27, 8, False, (0.4, 0.4, 0.4)))
    return ["\n".join(page) + "\n" for page in pages]


def build_pdf(markdown: str) -> bytes:
    streams = render_pages(markdown)
    page_count = len(streams)
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    page_ids = [5 + index * 2 for index in range(page_count)]
    kids = " ".join(f"{item} 0 R" for item in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode("ascii"))
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    for index, stream in enumerate(streams):
        page_id = page_ids[index]
        content_id = page_id + 1
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_id} 0 R >>".encode("ascii")
        )
        payload = stream.encode("latin-1", errors="replace")
        objects.append(f"<< /Length {len(payload)} >>\nstream\n".encode("ascii") + payload + b"endstream")

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_id, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{object_id} 0 obj\n".encode("ascii"))
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    return bytes(output)


def run_self_test() -> int:
    sample = """# Lithe Audio Network Support Report

## Probable root cause

- **Smoking gun:** Yes
- **Finding:** DHCP renewal aligned with gateway loss and Cast reconnect.

## Fix and outcome

- **Fix:** Router-side reservation created.
- **Expected improvement:** Stable addressing across renewals.
"""
    payload = build_pdf(sample)
    checks = [
        payload.startswith(b"%PDF-1.4"),
        b"Smoking gun" in payload,
        b"Copyright Lithe Audio 2026" in payload,
        payload.rstrip().endswith(b"%%EOF"),
    ]
    print("Self-test passed." if all(checks) else "Self-test failed.")
    return 0 if all(checks) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a redacted Lithe Audio support PDF from the generated Markdown report.")
    parser.add_argument("report", nargs="?", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return run_self_test()
    if args.report is None or args.output is None:
        parser.error("report and --output are required unless --self-test is used")
    if args.output.exists():
        print(f"Refusing to overwrite existing PDF: {args.output}", file=sys.stderr)
        return 3
    if args.report.stat().st_size > MAX_BYTES:
        print("Report exceeds the 2 MB limit.", file=sys.stderr)
        return 2
    markdown = args.report.read_text(encoding="utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(build_pdf(markdown))
    print(f"Saved redacted support PDF: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

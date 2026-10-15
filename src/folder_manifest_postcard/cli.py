from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import compare_manifests, render_html, render_json, render_markdown, scan_folder


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a compact, read-only folder manifest.")
    parser.add_argument("root", type=Path)
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--largest", type=int, default=8)
    parser.add_argument("--format", choices=("markdown", "html", "json"), default="markdown")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compare", type=Path, help="prior version 2 JSON postcard")
    args = parser.parse_args(argv)
    try:
        report = scan_folder(args.root, args.exclude, args.largest)
        if args.compare:
            previous = json.loads(args.compare.read_text(encoding="utf-8"))
            report["comparison"] = compare_manifests(previous, report)
        rendered = {"markdown": render_markdown, "html": render_html, "json": render_json}[
            args.format
        ](report)
        if args.output:
            if args.output.exists():
                raise ValueError(f"output already exists: {args.output}")
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (OSError, UnicodeError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0

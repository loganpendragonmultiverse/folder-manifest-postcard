from __future__ import annotations

import fnmatch
import html
import json
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_EXCLUDES = (
    ".git/**",
    "**/.git/**",
    "node_modules/**",
    "**/node_modules/**",
    ".venv/**",
    "**/.venv/**",
)


def _excluded(relative: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(relative, pattern) for pattern in patterns)


def scan_folder(root: Path, excludes: list[str] | None = None, largest: int = 8) -> dict[str, Any]:
    if not root.is_dir():
        raise ValueError("root must be a directory")
    if largest < 0:
        raise ValueError("largest must be non-negative")
    patterns = [*DEFAULT_EXCLUDES, *(excludes or [])]
    files = []
    directories: set[str] = set()
    skipped_symlinks = 0
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            skipped_symlinks += 1
            continue
        if _excluded(relative, patterns):
            continue
        if path.is_dir():
            directories.add(relative)
        elif path.is_file():
            files.append(
                {
                    "path": relative,
                    "bytes": path.stat().st_size,
                    "extension": path.suffix.casefold() or "[none]",
                }
            )
    extensions = Counter(item["extension"] for item in files)
    notable = sorted(files, key=lambda item: (-item["bytes"], item["path"]))[:largest]
    return {
        "version": 1,
        "name": root.resolve().name,
        "files": len(files),
        "folders": len(directories),
        "bytes": sum(item["bytes"] for item in files),
        "skipped_symlinks": skipped_symlinks,
        "extensions": dict(sorted(extensions.items(), key=lambda item: (-item[1], item[0]))),
        "largest": notable,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# {report['name']} Folder Postcard",
        "",
        f"**{report['files']} files · {report['folders']} folders · {report['bytes']:,} bytes**",
        "",
        "## File types",
        "",
    ]
    lines.extend(f"- `{extension}`: {count}" for extension, count in report["extensions"].items())
    lines.extend(["", "## Largest files", "", "| File | Bytes |", "|---|---:|"])
    lines.extend(f"| `{item['path']}` | {item['bytes']:,} |" for item in report["largest"])
    if report["skipped_symlinks"]:
        lines.extend(["", f"Skipped symlinks: {report['skipped_symlinks']}"])
    return "\n".join(lines).rstrip() + "\n"


def render_html(report: dict[str, Any]) -> str:
    extensions = "".join(
        f"<li><strong>{html.escape(extension)}</strong><span>{count}</span></li>"
        for extension, count in report["extensions"].items()
    )
    files = "".join(
        f"<tr><td>{html.escape(item['path'])}</td><td>{item['bytes']:,}</td></tr>"
        for item in report["largest"]
    )
    name = html.escape(report["name"])
    return f"""<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>{name} folder postcard</title><style>body{{font:16px system-ui;margin:0;padding:24px;background:#eef0ea;color:#19211d}}main{{max-width:820px;margin:auto;background:white;border:2px solid;padding:28px}}.totals{{font-size:1.35rem}}ul{{padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;list-style:none}}li{{display:flex;justify-content:space-between;border:1px solid;padding:10px}}table{{width:100%;border-collapse:collapse}}td,th{{padding:9px;border:1px solid;text-align:left}}td:last-child,th:last-child{{text-align:right}}</style><main><h1>{name}</h1><p class=totals>{report["files"]} files · {report["folders"]} folders · {report["bytes"]:,} bytes</p><h2>File types</h2><ul>{extensions}</ul><h2>Largest files</h2><table><tr><th>File</th><th>Bytes</th></tr>{files}</table></main></html>\n"""


def render_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False) + "\n"

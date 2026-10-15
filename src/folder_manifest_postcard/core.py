from __future__ import annotations

import fnmatch
import html
import json
import os
import stat
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
    incomplete: set[str] = set()

    def walk(directory: Path) -> None:
        nonlocal skipped_symlinks
        try:
            with os.scandir(directory) as iterator:
                entries = sorted(iterator, key=lambda entry: entry.name)
        except OSError:
            incomplete.add(directory.relative_to(root).as_posix())
            return
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            if _excluded(relative, patterns) or _excluded(relative + "/", patterns):
                continue
            try:
                metadata = entry.stat(follow_symlinks=False)
            except OSError:
                incomplete.add(relative)
                continue
            if stat.S_ISLNK(metadata.st_mode):
                skipped_symlinks += 1
                incomplete.add(relative)
            elif stat.S_ISDIR(metadata.st_mode):
                directories.add(relative)
                walk(path)
            elif stat.S_ISREG(metadata.st_mode):
                files.append(
                    {
                        "path": relative,
                        "bytes": metadata.st_size,
                        "extension": path.suffix.casefold() or "[none]",
                    }
                )
            else:
                incomplete.add(relative)

    if root.is_symlink():
        raise ValueError("root must not be a symlink")
    walk(root)
    files.sort(key=lambda item: item["path"])
    extensions = Counter(item["extension"] for item in files)
    notable = sorted(files, key=lambda item: (-item["bytes"], item["path"]))[:largest]
    return {
        "version": 2,
        "entries": files,
        "scan": {
            "excludes": patterns,
            "incomplete_paths": sorted(incomplete),
            "complete": not incomplete,
        },
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
    if "comparison" in report:
        lines.extend(
            [
                "",
                "## Comparison",
                "",
                "```json",
                json.dumps(report["comparison"], indent=2, ensure_ascii=False),
                "```",
            ]
        )
    if not report["scan"]["complete"]:
        lines.extend(["", "Scan incomplete; absent paths may be unknown."])
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
    comparison = ""
    if "comparison" in report:
        comparison = (
            "<h2>Comparison</h2><pre>"
            + html.escape(json.dumps(report["comparison"], indent=2, ensure_ascii=False))
            + "</pre>"
        )
    if not report["scan"]["complete"]:
        comparison += "<p>Scan incomplete; absent paths may be unknown.</p>"
    name = html.escape(report["name"])
    return f"""<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>{name} folder postcard</title><style>body{{font:16px system-ui;margin:0;padding:24px;background:#eef0ea;color:#19211d}}main{{max-width:820px;margin:auto;background:white;border:2px solid;padding:28px}}.totals{{font-size:1.35rem}}ul{{padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;list-style:none}}li{{display:flex;justify-content:space-between;border:1px solid;padding:10px}}table{{width:100%;border-collapse:collapse}}td,th{{padding:9px;border:1px solid;text-align:left}}td:last-child,th:last-child{{text-align:right}}</style><main><h1>{name}</h1><p class=totals>{report["files"]} files · {report["folders"]} folders · {report["bytes"]:,} bytes</p><h2>File types</h2><ul>{extensions}</ul><h2>Largest files</h2><table><tr><th>File</th><th>Bytes</th></tr>{files}</table>{comparison}</main></html>\n"""


def render_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False) + "\n"


def validate_manifest(value: Any) -> dict[str, Any]:
    """Validate the complete inventory needed for a meaningful metadata comparison."""
    if (
        not isinstance(value, dict)
        or type(value.get("version")) is not int
        or value["version"] != 2
    ):
        raise ValueError(
            "comparison requires a version 2 JSON postcard; version 1 only stored largest files"
        )
    scan = value.get("scan")
    entries = value.get("entries")
    if not isinstance(scan, dict) or not isinstance(entries, list):
        raise TypeError("manifest needs entries and scan metadata")
    for key in ("excludes", "incomplete_paths"):
        if not isinstance(scan.get(key), list) or not all(isinstance(s, str) for s in scan[key]):
            raise ValueError("invalid scan " + key)
    if type(scan.get("complete")) is not bool or scan["complete"] != (not scan["incomplete_paths"]):
        raise ValueError("scan completeness contradicts incomplete paths")
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict) or not _valid_path(entry.get("path")):
            raise ValueError("manifest entries need safe relative paths")
        if entry["path"] in seen or type(entry.get("bytes")) is not int or entry["bytes"] < 0:
            raise ValueError("duplicate path or invalid byte count")
        seen.add(entry["path"])
    if not all(path == "." or _valid_path(path) for path in scan["incomplete_paths"]):
        raise ValueError("invalid incomplete path")
    return value


def _valid_path(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and not value.startswith("/")
        and "\\" not in value
        and "\x00" not in value
        and all(part not in {"", ".", ".."} for part in value.split("/"))
    )


def compare_manifests(previous: Any, current: Any) -> dict[str, Any]:
    previous = validate_manifest(previous)
    current = validate_manifest(current)

    def known_absent(report: dict[str, Any], path: str) -> bool:
        scan = report["scan"]
        parts = path.split("/")
        prefixes = ["/".join(parts[:i]) for i in range(1, len(parts) + 1)]
        if any(
            _excluded(p, scan["excludes"]) or _excluded(p + "/", scan["excludes"]) for p in prefixes
        ):
            return False
        return not any(
            p == "." or path == p or path.startswith(p + "/") for p in scan["incomplete_paths"]
        )

    old = {entry["path"]: entry["bytes"] for entry in previous["entries"]}
    new = {entry["path"]: entry["bytes"] for entry in current["entries"]}
    added = sorted(path for path in new.keys() - old.keys() if known_absent(previous, path))
    removed = sorted(path for path in old.keys() - new.keys() if known_absent(current, path))
    uncertain = sorted(
        (new.keys() - old.keys() - set(added)) | (old.keys() - new.keys() - set(removed))
    )
    return {
        "added": added,
        "removed": removed,
        "size_changed": [
            {"path": path, "before_bytes": old[path], "after_bytes": new[path]}
            for path in sorted(old.keys() & new.keys())
            if old[path] != new[path]
        ],
        "uncertain_paths": uncertain,
        "complete": previous["scan"]["complete"]
        and current["scan"]["complete"]
        and previous["scan"]["excludes"] == current["scan"]["excludes"],
        "limitation": "Metadata only: equal sizes do not prove unchanged content. Compare scans of the same logical folder; the folder name is not an identity check.",
    }

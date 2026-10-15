# Changelog

## 1.1.0 - 2026-10-15

- Preserve literal POSIX backslashes in serialized path identities while rejecting absolute paths and traversal components.
- Include a complete metadata inventory in version 2 JSON postcards and compare it with `--compare`.
- Report added, removed and size-changed paths with explicit uncertainty for inaccessible, excluded and symlink paths.
- Keep version 1 comparison unsupported because its largest-file summary is incomplete.

## 1.0.0 - 2026-07-26

- Added read-only directory metadata scanning with exclusions and symlink skipping.
- Added compact Markdown, self-contained HTML, and JSON postcards.
- Added extension summaries and largest-file evidence.

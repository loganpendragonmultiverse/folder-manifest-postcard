# Testing

Requires Python 3.10+. From a clean checkout:

```bash
python -m pip install -e ".[dev]"
ruff format --check .
ruff check .
pytest
python -m build
```

The existing 90% branch-aware coverage floor is retained. CI runs Python 3.10 and
3.14 on Linux, Windows and macOS. Keep CodeQL and all protected checks required.
Exercise README examples, malformed inputs, existing files, dangling report
symlinks, closed stdout, and preservation of source fixtures. Install both the
tag-built wheel and source distribution in isolation and run the suite plus real
entrypoint flows away from the source tree. Run pip check. Reports and documents
must match tagged sources. Tests use synthetic data only.

- Protect report destinations with exclusive creation and handle closed output pipes cleanly.
- Keep unusual filenames literal in Markdown, wrap long HTML evidence on narrow screens, and document development and release tests.

Manual screen-reader and physical-device acceptance are not implied by automated
tests. Folder HTML needs desktop and narrow-viewport browser checks. No full WCAG
certification or guarantee against concurrent filesystem mutations is claimed.

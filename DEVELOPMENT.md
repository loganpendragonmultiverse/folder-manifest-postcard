# Development

Keep this a local, bounded tool for its README purpose. Do not add network lookup,
telemetry, implicit source modification or unrelated catalog work. Preserve the
documented legacy report shapes and interpretation limits.

Run the exact checks in TESTING.md. Changes go through a branch and protected pull
request with the existing cross-platform CI and CodeQL checks. Review the final
diff and actual installed distributions before publishing an annotated version tag.
Use that tag workflow's wheel and source distribution, verify asset SHA-256
digests, then reconcile the Forge catalog, Gold scope, source-backed information
page and canonical portfolio record. No release is complete after a push alone.

## This patch

- Protect report destinations with exclusive creation and handle closed output pipes cleanly.
- Keep unusual filenames literal in Markdown, wrap long HTML evidence on narrow screens, and document development and release tests.

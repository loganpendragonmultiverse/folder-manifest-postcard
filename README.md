# Folder Manifest Postcard

[![CI](https://github.com/loganpendragonmultiverse/folder-manifest-postcard/actions/workflows/ci.yml/badge.svg)](https://github.com/loganpendragonmultiverse/folder-manifest-postcard/actions/workflows/ci.yml)

Folder Manifest Postcard creates a compact Markdown, HTML, or JSON summary of a directory's file count, folder count, total size, extension mix, and largest files. It reads metadata only and never reorganizes the folder.

## Three-minute start

```bash
python -m pip install .
folder-postcard ~/Documents --output postcard.md
folder-postcard . --format html --output postcard.html
```

Common repository, dependency, and virtual-environment directories are excluded by default. Additional glob exclusions are explicit. Symlinks are skipped rather than followed, user-supplied names are escaped in HTML, and existing output files are refused.

The postcard is a compact inventory, not a backup, duplicate detector, malware scan, or proof of file integrity. Requires Python 3.10 or newer.

Part of the [Logan Pendragon Forge open-source collection](https://www.loganpendragonforge.com/open-source/). Licensed under the [MIT License](LICENSE).

## Compare metadata postcards

```bash
folder-postcard ~/Documents --format json --output before.json
folder-postcard ~/Documents --compare before.json --format json --output after.json
```

Version 2 JSON postcards include every scanned file's relative path and size, plus exclusion and incomplete-path metadata. Comparison lists added, removed and size-changed files in path order. Inaccessible directories, symlinks and special files are recorded as uncertain scan regions; absence in those regions or in excluded paths never proves removal. A missing root fails the command. HTML and Markdown reports include the comparison too. Existing output files are refused.

Version 1 postcards cannot be compared because they contain only the largest files; create a new JSON baseline first. Compare the same logical folder yourself: its display name does not establish identity. Equal sizes do not prove equal contents; no source file content is opened, hashed or executed. Scans are observations rather than filesystem snapshots, so concurrent changes can make a scan incomplete. JSON postcards reveal filenames and sizes and should be shared deliberately.

Manifest paths always use `/` as the directory separator, regardless of the reading platform. Backslashes in POSIX filenames remain literal characters in JSON and comparison identities; manifest paths are never opened or interpreted as native filesystem paths. Absolute POSIX paths, NUL characters and empty, `.` or `..` path components are rejected.

## Report and release behavior

Install the wheel from the GitHub release with python -m pip install ./PACKAGE.whl,
using the actual downloaded filename. The source distribution can also be installed
with pip. The wheel includes these handoff documents and supplied examples under
share/folder-manifest-postcard/ in the installation prefix. A repository checkout is the easiest
way to run the README examples as written.

Invalid inputs or failed output writes return exit status 2. A successful command
returns 0. Report files must be new: existing files, directories and symlinks are
refused. Keep reports outside scanned folders to avoid counting prior reports.
A failed write may leave a partial newly created report; no power-loss transaction
is promised. Closed stdout pipes return 2. Filenames, story data and paths in
reports can be sensitive; review before sharing.

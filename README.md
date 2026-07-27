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

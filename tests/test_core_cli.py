import json

import pytest

from folder_manifest_postcard.cli import main
from folder_manifest_postcard.core import render_html, render_markdown, scan_folder


def test_scan_and_render(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "readme.md").write_text("hello", encoding="utf-8")
    (tmp_path / "image.png").write_bytes(b"123456789")
    (tmp_path / "ignore.tmp").write_text("x", encoding="utf-8")
    report = scan_folder(tmp_path, ["*.tmp"], largest=1)
    assert report["files"] == 2
    assert report["largest"][0]["path"] == "image.png"
    assert "readme.md" in render_markdown(scan_folder(tmp_path, ["*.tmp"]))
    assert "image.png" in render_html(report)


def test_validation(tmp_path):
    with pytest.raises(ValueError, match="directory"):
        scan_folder(tmp_path / "missing")
    with pytest.raises(ValueError, match="non-negative"):
        scan_folder(tmp_path, largest=-1)


def test_cli_json_and_safe_output(tmp_path, capsys):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    assert main([str(tmp_path), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["files"] == 1
    output = tmp_path / "postcard.md"
    output.write_text("keep", encoding="utf-8")
    assert main([str(tmp_path), "--output", str(output)]) == 2

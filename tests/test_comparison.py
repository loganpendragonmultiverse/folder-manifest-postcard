import json
import os
from pathlib import Path

import pytest

from folder_manifest_postcard.cli import main
from folder_manifest_postcard.core import (
    compare_manifests,
    render_html,
    render_json,
    render_markdown,
    scan_folder,
    validate_manifest,
)


def test_compare_metadata_unicode_zero_and_no_content_reads(tmp_path, monkeypatch):
    (tmp_path / "é.txt").write_bytes(b"")
    (tmp_path / "gone").write_bytes(b"old")
    before = scan_folder(tmp_path, largest=0)
    (tmp_path / "gone").unlink()
    (tmp_path / "é.txt").write_bytes(b"new")
    (tmp_path / "added").write_bytes(b"")
    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", lambda *a, **k: pytest.fail("source content was opened"))
        after = scan_folder(tmp_path)
    result = compare_manifests(before, after)
    assert result["added"] == ["added"] and result["removed"] == ["gone"]
    assert result["size_changed"] == [{"path": "é.txt", "before_bytes": 0, "after_bytes": 3}]
    assert result["complete"] and result["uncertain_paths"] == []
    assert compare_manifests(after, after)["size_changed"] == []
    after["comparison"] = result
    assert "Comparison" in render_markdown(after) and "Comparison" in render_html(after)


def test_exclusions_and_symlinks_never_prove_removal(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "keep").write_bytes(b"")
    old = scan_folder(tmp_path)
    excluded = scan_folder(tmp_path, ["sub/**"])
    assert excluded["entries"] == []
    result = compare_manifests(old, excluded)
    assert result["removed"] == [] and result["uncertain_paths"] == ["sub/keep"]
    assert not result["complete"]
    assert compare_manifests(excluded, old)["added"] == []
    (sub / "keep").unlink()
    sub.rmdir()
    target = tmp_path / "elsewhere"
    target.mkdir()
    try:
        sub.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")
    current = scan_folder(tmp_path)
    assert current["skipped_symlinks"] == 1
    assert compare_manifests(old, current)["removed"] == []
    assert "incomplete" in render_markdown(current) and "incomplete" in render_html(current)
    with pytest.raises(ValueError, match="symlink"):
        scan_folder(sub)


def test_unreadable_directories_and_stat_errors_are_uncertain(tmp_path, monkeypatch):
    sub = tmp_path / "private"
    sub.mkdir()
    (sub / "keep").write_bytes(b"")
    old = scan_folder(tmp_path)
    original = os.scandir

    def denied(path):
        if Path(path) == sub:
            raise PermissionError("fixture denial")
        return original(path)

    monkeypatch.setattr(os, "scandir", denied)
    current = scan_folder(tmp_path)
    assert current["scan"]["incomplete_paths"] == ["private"]
    result = compare_manifests(old, current)
    assert not result["removed"] and result["uncertain_paths"] == ["private/keep"]
    monkeypatch.setattr(os, "scandir", lambda path: (_ for _ in ()).throw(PermissionError()))
    current = scan_folder(tmp_path)
    assert current["scan"]["incomplete_paths"] == ["."]
    assert not compare_manifests(old, current)["removed"]


def test_file_stat_failure_and_special_files(tmp_path, monkeypatch):
    (tmp_path / "unreadable").write_bytes(b"x")
    before = scan_folder(tmp_path)

    class Entry:
        name = "unreadable"
        path = str(tmp_path / "unreadable")

        def stat(self, **kwargs):
            raise PermissionError("fixture")

    class Scan:
        def __enter__(self):
            return iter([Entry()])

        def __exit__(self, *args):
            return False

    with monkeypatch.context() as patch:
        patch.setattr(os, "scandir", lambda path: Scan())
        current = scan_folder(tmp_path)
    assert compare_manifests(before, current)["uncertain_paths"] == ["unreadable"]
    if hasattr(os, "mkfifo"):
        os.mkfifo(tmp_path / "pipe")
        assert "pipe" in scan_folder(tmp_path)["scan"]["incomplete_paths"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r.update(version=1),
        lambda r: r.update(version=True),
        lambda r: r.update(scan=[]),
        lambda r: r.update(entries={}),
        lambda r: r["scan"].update(excludes=42),
        lambda r: r["scan"].update(complete=False),
        lambda r: r["scan"].update(incomplete_paths=["../bad"], complete=False),
        lambda r: r["entries"].append({"path": "../bad", "bytes": 0}),
        lambda r: r["entries"].append({"path": "x", "bytes": True}),
        lambda r: r["entries"].extend([{"path": "x", "bytes": 0}] * 2),
    ],
)
def test_manifest_validation(tmp_path, mutation):
    report = scan_folder(tmp_path)
    mutation(report)
    with pytest.raises((ValueError, TypeError)):
        validate_manifest(report)
    with pytest.raises((ValueError, TypeError)):
        validate_manifest([])


def test_comparison_cli_and_safe_reports(tmp_path, capsys):
    root = tmp_path / "files"
    root.mkdir()
    (root / "a").write_bytes(b"x")
    before = tmp_path / "before.json"
    before.write_text(json.dumps(scan_folder(root)), encoding="utf-8")
    assert main([str(root), "--compare", str(before), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["comparison"]["removed"] == []
    assert main([str(root), "--compare", str(before), "--output", str(before)]) == 2
    assert main([str(root / "missing"), "--compare", str(before)]) == 2
    before.write_text('{"version": 1}', encoding="utf-8")
    assert main([str(root), "--compare", str(before)]) == 2
    assert "version 2" in capsys.readouterr().err
    before.write_bytes(b"\xff")
    assert main([str(root), "--compare", str(before)]) == 2
    before.write_text("broken", encoding="utf-8")
    assert main([str(root), "--compare", str(before)]) == 2
    out = tmp_path / "out.html"
    assert main([str(root), "--output", str(out), "--format", "html"]) == 0
    assert out.read_text(encoding="utf-8").startswith("<!doctype")


@pytest.mark.skipif(os.name != "posix", reason="literal backslash filenames require POSIX")
def test_posix_backslash_scan_json_and_cli_round_trip(tmp_path, capsys):
    root = tmp_path / "files"
    root.mkdir()
    source = root / r"a\b"
    source.write_bytes(b"old")
    directory = root / r"sub\dir"
    directory.mkdir()
    (directory / "é.txt").write_bytes(b"")
    baseline = tmp_path / "baseline.json"
    baseline.write_text(render_json(scan_folder(root)), encoding="utf-8")
    previous = json.loads(baseline.read_text(encoding="utf-8"))
    assert [entry["path"] for entry in previous["entries"]] == [r"a\b", "sub\\dir/é.txt"]
    unchanged = compare_manifests(previous, scan_folder(root))
    assert unchanged["added"] == unchanged["removed"] == unchanged["size_changed"] == []
    assert main([str(root), "--compare", str(baseline), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["comparison"]["complete"]
    source.write_bytes(b"changed")
    changed = compare_manifests(previous, scan_folder(root))
    assert changed["size_changed"] == [{"path": r"a\b", "before_bytes": 3, "after_bytes": 7}]


@pytest.mark.parametrize(
    "path",
    [
        "/absolute",
        "//server/file",
        "../escape",
        "a/../../escape",
        "a/../b",
        "./a",
        "a/./b",
        "a//b",
        "a/",
        "",
        ".",
        "..",
        "a\x00b",
    ],
)
def test_manifest_paths_reject_absolute_and_traversal_components(tmp_path, path):
    report = scan_folder(tmp_path)
    report["entries"] = [{"path": path, "bytes": 0}]
    with pytest.raises(ValueError, match="safe relative paths"):
        validate_manifest(report)
    report["entries"] = []
    if path != ".":
        report["scan"].update(incomplete_paths=[path], complete=False)
        with pytest.raises(ValueError, match="invalid incomplete path"):
            validate_manifest(report)


def test_backslash_identity_is_not_normalized_as_native_traversal(tmp_path):
    # These are literal components in the manifest's POSIX grammar, not paths to open.
    previous = scan_folder(tmp_path)
    previous["entries"] = [{"path": r"..\literal", "bytes": 0}, {"path": r"a\b", "bytes": 1}]
    current = json.loads(render_json(previous))
    current["scan"].update(incomplete_paths=[r"a\b"], complete=False)
    current["entries"] = current["entries"][:1]
    result = compare_manifests(previous, current)
    assert result["removed"] == [] and result["uncertain_paths"] == [r"a\b"]

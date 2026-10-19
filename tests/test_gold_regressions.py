import copy
from pathlib import Path
from unittest.mock import patch

import pytest

from folder_manifest_postcard.core import (
    compare_manifests,
    render_html,
    render_markdown,
    scan_folder,
)


def test_metadata_never_reads_file_contents_and_escapes_names(tmp_path):
    name = "a" + chr(96) * 5 + "|<x>.txt"
    (tmp_path / "ordinary.txt").write_bytes(b"12345")
    with patch.object(Path, "read_bytes", side_effect=AssertionError("content read")):
        report = scan_folder(tmp_path)
    report["largest"][0]["path"] = name
    text = render_markdown(report)
    assert "&#96;" in text and "\\|" in text
    assert "&lt;x&gt;" in text
    assert "overflow-wrap:anywhere" in render_html(report)
    assert report["bytes"] == 5
    other = copy.deepcopy(report)
    other["entries"] = []
    other["scan"]["incomplete_paths"] = ["."]
    other["scan"]["complete"] = False
    result = compare_manifests(report, other)
    assert result["removed"] == []
    assert result["uncertain_paths"] == [name]
    report["comparison"] = result
    assert chr(96) * 6 + "json" in render_markdown(report)


@pytest.mark.parametrize("largest", [True, 1.5, -1])
def test_largest_must_be_nonnegative_integer(tmp_path, largest):
    with pytest.raises(ValueError):
        scan_folder(tmp_path, largest=largest)

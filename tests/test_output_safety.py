import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from folder_manifest_postcard.cli import main
from folder_manifest_postcard.output import write_report, write_stdout


def _symlink(link, target):
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this platform")


def test_output_preserves_existing_and_dangling_targets(tmp_path):
    existing = tmp_path / "existing"
    existing.write_bytes(b"keep")
    with pytest.raises(OSError):
        write_report(existing, "replace")
    assert existing.read_bytes() == b"keep"
    target = tmp_path / "absent"
    link = tmp_path / "link"
    _symlink(link, target)
    with pytest.raises(OSError):
        write_report(link, "unexpected")
    assert not target.exists()
    assert link.is_symlink()


def test_exclusive_creation_refuses_racing_destination(tmp_path):
    output = tmp_path / "raced"
    original = Path.open

    def raced(path, *args, **kwargs):
        if path == output and args and args[0] == "x":
            with original(path, "w") as stream:
                stream.write("racing writer")
        return original(path, *args, **kwargs)

    with patch.object(Path, "open", raced), pytest.raises(OSError):
        write_report(output, "replace")
    assert output.read_text() == "racing writer"


def test_stdout_and_new_utf8_report(tmp_path, capsys):
    write_report(None, "café\n")
    assert capsys.readouterr().out == "café\n"
    output = tmp_path / "new"
    write_report(output, "café\r\n")
    assert output.read_bytes() == "café\r\n".encode()


@pytest.mark.parametrize("failure", [BrokenPipeError("closed"), OSError(22, "invalid argument")])
def test_broken_stream_without_descriptor(failure):
    class Broken:
        def write(self, text):
            raise failure

        def fileno(self):
            raise ValueError("no descriptor")

    with patch.object(sys, "stdout", Broken()), pytest.raises(OSError):
        write_stdout("small")


def test_real_closed_stdout_exits_cleanly(tmp_path):
    source = tmp_path / "source.json"
    fixture = None
    if fixture is not None:
        source.write_text(json.dumps(fixture), encoding="utf-8")
    args = [str(tmp_path)]
    read_fd, write_fd = os.pipe()
    os.close(read_fd)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "folder_manifest_postcard", *args],
            stdout=write_fd,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    finally:
        os.close(write_fd)
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert "Exception ignored" not in result.stderr


def test_cli_output_error_does_not_modify_input(tmp_path, capsys):
    source = tmp_path / "source.json"
    fixture = None
    if fixture is not None:
        source.write_text(json.dumps(fixture), encoding="utf-8")
    args = [str(tmp_path)]
    output = tmp_path / "existing"
    output.write_bytes(b"keep")
    before = source.read_bytes() if source.exists() else None
    assert main([*args, "--output", str(output)]) == 2
    assert output.read_bytes() == b"keep"
    if before is not None:
        assert source.read_bytes() == before

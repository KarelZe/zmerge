from __future__ import annotations

import json
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from zmerge import __version__
from zmerge.cli import main

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert capsys.readouterr().out.strip() == f"zmerge {__version__}"


def test_module_entry_point() -> None:
    result = subprocess.run([sys.executable, "-m", "zmerge", "--version"], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == f"zmerge {__version__}"


def test_no_arguments_prints_help_and_lists_commands(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "usage: zmerge" in out
    assert "assemble" in out
    assert "build" in out


def test_assemble_prints_generated_config(
    make_project: Callable[..., Path], capsys: pytest.CaptureFixture[str]
) -> None:
    make_project("lev")
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}]})

    assert main(["assemble", "-f", str(umbrella)]) == 0
    assert capsys.readouterr().out.strip() == str(umbrella.parent / ".zmerge.toml")


def test_invalid_config_reports_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["build", "-f", str(tmp_path / "zensical.toml")]) == 1
    assert "zmerge: error:" in capsys.readouterr().err


def test_build_merged_site(make_project: Callable[..., Path]) -> None:
    make_project("lev", {"nav": [{"Home": "index.md"}]}, files={"index.md": "# lev\n\nSee [dame](../dame/index.md).\n"})
    make_project("dame", files={"index.md": "# dame\n\n## Rules\n", "rules.md": "# Rules\n\n[Home](index.md#rules)\n"})
    umbrella = make_project(
        "umbrella",
        {"nav": [{"Home": "index.md"}, {"lev": "!include ../lev"}, {"dame": "!include ../dame"}]},
        files={"index.md": "# Projects\n\n- [lev](lev/index.md)\n- [dame](dame/rules.md)\n"},
    )

    assert main(["build", "--strict", "-f", str(umbrella)]) == 0

    site = umbrella.parent / "site"
    assert (site / "lev" / "index.html").is_file()
    assert (site / "dame" / "rules" / "index.html").is_file()
    search = json.loads((site / "search.json").read_text(encoding="utf-8"))
    locations = {item["location"].split("/")[0] for item in search["items"]}
    assert {"lev", "dame"} <= locations


def test_build_strict_fails_on_broken_links(make_project: Callable[..., Path]) -> None:
    make_project("lev", files={"index.md": "# lev\n\n[missing](missing.md)\n"})
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}]})

    assert main(["build", "--strict", "-f", str(umbrella)]) != 0


def test_build_strict_aborts_on_zmerge_warnings(
    make_project: Callable[..., Path], capsys: pytest.CaptureFixture[str]
) -> None:
    make_project("lev", {"plugins": {"tags": {"listings": True}}})
    make_project("dame", {"plugins": {"tags": {"listings": False}}})
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}, {"dame": "!include ../dame"}]})

    assert main(["build", "--strict", "-f", str(umbrella)]) == 1
    err = capsys.readouterr().err
    assert "zmerge: warning:" in err
    assert "aborted because --strict is set" in err

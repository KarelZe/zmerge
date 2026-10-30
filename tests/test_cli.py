from __future__ import annotations

import json
import subprocess
import sys
from importlib.metadata import entry_points
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from click.testing import CliRunner

from zmerge import __version__
from zmerge.cli import main

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def test_version() -> None:
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == f"zmerge {__version__}"


def test_module_entry_point() -> None:
    result = subprocess.run([sys.executable, "-m", "zmerge", "--version"], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == f"zmerge {__version__}"


@pytest.mark.parametrize("name", ["zmerge", "zm"])
def test_console_scripts(name: str) -> None:
    (script,) = entry_points(group="console_scripts", name=name)
    assert script.value == "zmerge.cli:main"


def test_no_arguments_prints_help_and_lists_commands() -> None:
    out = CliRunner().invoke(main, []).output
    assert "Usage: zmerge" in out
    assert "assemble" in out
    assert "build" in out


def test_assemble_prints_generated_config(make_project: Callable[..., Path]) -> None:
    make_project("lev")
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}]})

    result = CliRunner().invoke(main, ["assemble", "-f", str(umbrella)])
    assert result.exit_code == 0
    assert result.stdout.strip() == str(umbrella.parent / ".zmerge.toml")


def test_assemble_rejects_zensical_options() -> None:
    result = CliRunner().invoke(main, ["assemble", "--clean"])
    assert result.exit_code == 2
    assert "No such option '--clean'" in result.stderr


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["-c", "--future=1", "-x", "y"], ["-c", "--future=1", "-x", "y"]),
        (["-sc"], ["--strict", "-c"]),
        (["--", "-c"], ["-c"]),
    ],
)
def test_build_passes_options_to_zensical(
    make_project: Callable[..., Path], argv: list[str], expected: list[str]
) -> None:
    make_project("lev")
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}]})

    with mock.patch("zmerge.cli.subprocess.run") as run:
        run.return_value.returncode = 0
        assert CliRunner().invoke(main, ["build", "-f", str(umbrella), *argv]).exit_code == 0

    command = run.call_args.args[0]
    assert command[3:6] == ["build", "--config-file", str(umbrella.parent / ".zmerge.toml")]
    assert command[6:] == expected


def test_invalid_config_reports_error(tmp_path: Path) -> None:
    result = CliRunner().invoke(main, ["build", "-f", str(tmp_path / "zensical.toml")])
    assert result.exit_code == 1
    assert "zmerge: error:" in result.stderr


def test_build_merged_site(make_project: Callable[..., Path]) -> None:
    make_project("lev", {"nav": [{"Home": "index.md"}]}, files={"index.md": "# lev\n\nSee [dame](../dame/index.md).\n"})
    make_project("dame", files={"index.md": "# dame\n\n## Rules\n", "rules.md": "# Rules\n\n[Home](index.md#rules)\n"})
    umbrella = make_project(
        "umbrella",
        {"nav": [{"Home": "index.md"}, {"lev": "!include ../lev"}, {"dame": "!include ../dame"}]},
        files={"index.md": "# Projects\n\n- [lev](lev/index.md)\n- [dame](dame/rules.md)\n"},
    )

    assert CliRunner().invoke(main, ["build", "--strict", "-f", str(umbrella)]).exit_code == 0

    site = umbrella.parent / "site"
    assert (site / "lev" / "index.html").is_file()
    assert (site / "dame" / "rules" / "index.html").is_file()
    search = json.loads((site / "search.json").read_text(encoding="utf-8"))
    locations = {item["location"].split("/")[0] for item in search["items"]}
    assert {"lev", "dame"} <= locations


def test_build_restores_structured_mkdocstrings_defaults(make_project: Callable[..., Path]) -> None:
    pytest.importorskip("mkdocstrings_handlers.python")
    for name, options in (("lev", {"filters": [], "summary": True}), ("dame", {})):
        plugins = {"mkdocstrings": {"handlers": {"python": {"options": options}}}}
        config = make_project(name, {"plugins": plugins}, files={"index.md": f"# {name}\n\n::: {name}_api\n"})
        (config.parent / f"{name}_api.py").write_text(f'def _{name}_private():\n    """Private."""\n', encoding="utf-8")
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}, {"dame": "!include ../dame"}]})

    assert CliRunner().invoke(main, ["build", "--strict", "-f", str(umbrella)]).exit_code == 0

    site = umbrella.parent / "site"
    assert "_lev_private" in (site / "lev" / "index.html").read_text(encoding="utf-8")
    # dame doesn't set `filters`, so it keeps mkdocstrings-python's default, which hides private members.
    assert "_dame_private" not in (site / "dame" / "index.html").read_text(encoding="utf-8")


def test_build_strict_fails_on_broken_links(make_project: Callable[..., Path]) -> None:
    make_project("lev", files={"index.md": "# lev\n\n[missing](missing.md)\n"})
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}]})

    assert CliRunner().invoke(main, ["build", "--strict", "-f", str(umbrella)]).exit_code != 0


def test_build_strict_aborts_on_zmerge_warnings(make_project: Callable[..., Path]) -> None:
    make_project("lev", {"plugins": {"tags": {"listings": True}}})
    make_project("dame", {"plugins": {"tags": {"listings": False}}})
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}, {"dame": "!include ../dame"}]})

    result = CliRunner().invoke(main, ["build", "--strict", "-f", str(umbrella)])
    assert result.exit_code == 1
    err = result.stderr
    assert "zmerge: warning:" in err
    assert "aborted because --strict is set" in err

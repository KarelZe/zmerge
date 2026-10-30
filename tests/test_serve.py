from __future__ import annotations

import signal
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from click.testing import CliRunner

from zmerge.cli import main
from zmerge.config import load_site
from zmerge.serve import serve, snapshot, watched_paths

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


class FakeProcess:
    """Stands in for `zensical serve`, running for a given number of polls."""

    def __init__(self, polls: int) -> None:
        self.polls = polls
        self.returncode: int | None = None
        self.terminated = False

    def poll(self) -> int | None:
        if self.polls == 0 and self.returncode is None:
            self.returncode = 0
        self.polls -= 1
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = -15

    def wait(self, timeout: float | None = None) -> int:
        return self.returncode or 0


@pytest.fixture
def site_files(make_project: Callable[..., Path]) -> tuple[Path, Path]:
    lev = make_project("lev", files={"index.md": "# v1\n"})
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}]})
    return umbrella, lev.parent / "docs" / "index.md"


def test_watched_paths_and_snapshot(site_files: tuple[Path, Path]) -> None:
    umbrella, page = site_files
    site = load_site(umbrella)

    paths = watched_paths(site)
    state = snapshot(paths)

    assert paths == [umbrella, site.docs_dir, page.parents[1] / "zensical.toml", page.parent]
    assert umbrella in state
    assert page in state
    page.write_text("# changed, and longer\n", encoding="utf-8")
    assert snapshot(paths) != state


def test_serve_reassembles_on_changes(site_files: tuple[Path, Path], capsys: pytest.CaptureFixture[str]) -> None:
    umbrella, page = site_files
    staged = umbrella.parent / ".zmerge" / "docs" / "lev" / "index.md"
    steps = iter([
        lambda: None,
        lambda: page.write_text("# v2, edited\n", encoding="utf-8"),
        lambda: umbrella.write_text("[project]\n", encoding="utf-8"),  # invalid: no site_name
        lambda: None,
    ])

    def sleep(_: float) -> None:
        next(steps)()

    process = FakeProcess(polls=4)
    with mock.patch("subprocess.Popen", return_value=process) as popen:
        assert serve(umbrella, ["--open"], sleep=sleep) == 0

    command = popen.call_args.args[0]
    assert command[-4:] == ["serve", "--config-file", str(umbrella.parent / ".zmerge.toml"), "--open"]
    assert staged.read_text(encoding="utf-8") == "# v2, edited\n"
    err = capsys.readouterr().err
    assert "re-assembled" in err
    assert "zmerge: error:" in err


def test_serve_stops_zensical_on_sigterm(site_files: tuple[Path, Path]) -> None:
    umbrella, _ = site_files

    def sleep(_: float) -> None:
        signal.raise_signal(signal.SIGTERM)

    process = FakeProcess(polls=10)
    with mock.patch("subprocess.Popen", return_value=process):
        serve(umbrella, sleep=sleep)

    assert process.terminated
    assert signal.getsignal(signal.SIGTERM) is signal.SIG_DFL


def test_cli_serve_passes_options(site_files: tuple[Path, Path]) -> None:
    umbrella, _ = site_files

    with mock.patch("zmerge.cli.serve", return_value=0) as serve_mock:
        assert (
            CliRunner()
            .invoke(main, ["serve", "-a", "localhost:9000", "-f", str(umbrella), "--open", "--strict"])
            .exit_code
            == 0
        )

    serve_mock.assert_called_once_with(umbrella, ["-a", "localhost:9000", "--open", "--strict"], update=True)


def test_cli_serve_reports_errors(tmp_path: Path) -> None:
    result = CliRunner().invoke(main, ["serve", "-f", str(tmp_path / "zensical.toml")])
    assert result.exit_code == 1
    assert "zmerge: error:" in result.stderr

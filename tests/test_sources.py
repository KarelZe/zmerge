from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from click.testing import CliRunner

from zmerge.cli import main
from zmerge.config import ZmergeError, load_site
from zmerge.sources import GitSource, fetch

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def git(*args: str, cwd: Path) -> str:
    command = ["git", "-c", "user.name=t", "-c", "user.email=t@example.org", "-c", "init.defaultBranch=main", *args]
    # Ignore the global configuration, e.g. commit signing.
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True, env=env).stdout.strip()


@pytest.fixture
def repo(make_project: Callable[..., Path]) -> Path:
    """A git repository with a project at its root and one in `sub/`, tagged `v1`."""
    config_file = make_project("repo", {"nav": [{"Home": "index.md"}]}, files={"index.md": "# v1\n"})
    root = config_file.parent
    (root / "sub" / "docs").mkdir(parents=True)
    (root / "sub" / "zensical.toml").write_text('[project]\nsite_name = "sub"\n', encoding="utf-8")
    (root / "sub" / "docs" / "index.md").write_text("# Sub\n", encoding="utf-8")
    git("init", "--quiet", cwd=root)
    git("add", ".", cwd=root)
    git("commit", "--quiet", "-m", "v1", cwd=root)
    git("tag", "v1", cwd=root)
    return root


def commit(repo: Path, text: str) -> None:
    (repo / "docs" / "index.md").write_text(text, encoding="utf-8")
    git("commit", "--quiet", "-am", text, cwd=repo)


@pytest.mark.parametrize(
    "spec",
    [
        "git+https://github.com/me/lev.git#egg=lev",
        "git+https://github.com/me/lev.git#subdirectory=",
        "git+lev.git",
        "git+-oProxyCommand=x://h/p",
        "git+https://github.com/me/lev.git@-x",
        "git+https://github.com/me/lev.git@a b",
        "git+https://github.com/me/lev.git#subdirectory=../x",
    ],
)
def test_parse_rejects_invalid_specs(spec: str) -> None:
    with pytest.raises(ZmergeError):
        GitSource.parse(spec)


def test_cache_name_depends_on_url_and_ref() -> None:
    a = GitSource.parse("git+https://github.com/me/lev.git")
    b = GitSource.parse("git+https://github.com/me/lev.git@v1")

    assert a.cache_name.startswith("github.com-me-lev-")
    assert a.cache_name != b.cache_name


def test_fetch_ref_and_subdirectory(repo: Path, tmp_path: Path) -> None:
    commit(repo, "# v2\n")
    cache = tmp_path / "cache"

    head = fetch(GitSource.parse(f"git+{repo.as_uri()}"), cache)
    tagged = fetch(GitSource.parse(f"git+{repo.as_uri()}@v1"), cache)
    sub = fetch(GitSource.parse(f"git+{repo.as_uri()}@main#subdirectory=sub"), cache)

    assert (head / "docs" / "index.md").read_text(encoding="utf-8") == "# v2\n"
    assert (tagged / "docs" / "index.md").read_text(encoding="utf-8") == "# v1\n"
    assert (sub / "docs" / "index.md").read_text(encoding="utf-8") == "# Sub\n"


def test_fetch_updates_unless_disabled(repo: Path, tmp_path: Path) -> None:
    source = GitSource.parse(f"git+{repo.as_uri()}")
    cache = tmp_path / "cache"
    checkout = fetch(source, cache)
    (checkout / "docs" / "untracked.md").write_text("x", encoding="utf-8")
    commit(repo, "# v2\n")

    assert (fetch(source, cache, update=False) / "docs" / "index.md").read_text(encoding="utf-8") == "# v1\n"
    assert (fetch(source, cache) / "docs" / "index.md").read_text(encoding="utf-8") == "# v2\n"
    assert not (checkout / "docs" / "untracked.md").exists()


def test_fetch_reports_git_errors(tmp_path: Path) -> None:
    source = GitSource.parse(f"git+{(tmp_path / 'missing').as_uri()}")

    with pytest.raises(ZmergeError, match="`git fetch"):
        fetch(source, tmp_path / "cache")


def test_missing_git(repo: Path, tmp_path: Path) -> None:
    with (
        mock.patch("subprocess.run", side_effect=FileNotFoundError),
        pytest.raises(ZmergeError, match="git is required"),
    ):
        fetch(GitSource.parse(f"git+{repo.as_uri()}"), tmp_path / "cache")


def test_build_with_git_include(repo: Path, make_project: Callable[..., Path]) -> None:
    umbrella = make_project(
        "umbrella",
        {"nav": [{"lev": f"!include git+{repo.as_uri()}"}, {"sub": f"!include git+{repo.as_uri()}#subdirectory=sub"}]},
    )

    assert CliRunner().invoke(main, ["build", "--strict", "-f", str(umbrella)]).exit_code == 0
    (lev, sub) = load_site(umbrella, update=False).projects
    assert lev.config_file.is_relative_to(umbrella.parent / ".zmerge" / "repos")
    assert sub.docs_dir.name == "docs"
    assert "v1" in (umbrella.parent / "site" / "lev" / "index.html").read_text(encoding="utf-8")

    commit(repo, "# v2\n")
    assert CliRunner().invoke(main, ["build", "--no-fetch", "-f", str(umbrella)]).exit_code == 0
    assert "v1" in (umbrella.parent / "site" / "lev" / "index.html").read_text(encoding="utf-8")
    assert CliRunner().invoke(main, ["build", "-f", str(umbrella)]).exit_code == 0
    assert "v2" in (umbrella.parent / "site" / "lev" / "index.html").read_text(encoding="utf-8")


def test_git_errors_name_the_config(make_project: Callable[..., Path], tmp_path: Path) -> None:
    umbrella = make_project("umbrella", {"nav": [{"lev": f"!include git+{(tmp_path / 'missing').as_uri()}"}]})

    with pytest.raises(ZmergeError, match=r"umbrella[/\\]zensical\.toml: `git fetch"):
        load_site(umbrella)

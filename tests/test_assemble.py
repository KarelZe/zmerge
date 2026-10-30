from __future__ import annotations

import shutil
import tomllib
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from zmerge.assemble import GENERATED_CONFIG, STAGING_DIR, _write_if_changed, assemble, collect_files
from zmerge.config import ZmergeError, load_site

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def read_generated(umbrella: Path) -> dict[str, object]:
    with (umbrella.parent / GENERATED_CONFIG).open("rb") as f:
        return tomllib.load(f)["project"]


def test_assemble_merges_docs_and_nav(make_project: Callable[..., Path]) -> None:
    lev = make_project(
        "lev",
        {"nav": [{"Home": "index.md"}, {"API": "./api.md"}, {"PyPI": "https://pypi.org"}]},
        files={"index.md": "# lev\n", "api.md": "# API\n", "assets/plot.svg": "<svg/>"},
    )
    umbrella = make_project(
        "umbrella",
        {"site_url": "https://example.org/", "nav": [{"Home": "index.md"}, {"lev": "!include ../lev"}]},
    )

    assembly = assemble(load_site(umbrella))

    root = umbrella.parent
    assert assembly.config_file == root / GENERATED_CONFIG
    assert assembly.docs_dir == root / STAGING_DIR / "docs"
    assert sorted(assembly.files) == ["index.md", "lev/api.md", "lev/assets/plot.svg", "lev/index.md"]
    staged = assembly.docs_dir / "lev" / "index.md"
    assert staged.read_text(encoding="utf-8") == "# lev\n"
    assert staged.samefile(lev.parent / "docs" / "index.md")
    config = read_generated(umbrella)
    assert config["site_url"] == "https://example.org/"
    assert config["docs_dir"] == ".zmerge/docs"
    assert config["nav"] == [
        {"Home": "index.md"},
        {"lev": [{"Home": "lev/index.md"}, {"API": "lev/api.md"}, {"PyPI": "https://pypi.org"}]},
    ]


def test_assemble_falls_back_to_copies(make_project: Callable[..., Path]) -> None:
    make_project("lev")
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}]})

    with mock.patch("os.link", side_effect=OSError("cross-device link")):
        assembly = assemble(load_site(umbrella))

    staged = assembly.docs_dir / "lev" / "index.md"
    assert staged.read_text(encoding="utf-8") == "# lev\n"
    assert not staged.samefile(umbrella.parents[1] / "lev" / "docs" / "index.md")


def test_assemble_removes_stale_files(make_project: Callable[..., Path]) -> None:
    lev = make_project("lev", files={"index.md": "# lev\n", "old.md": "# Old\n"})
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}]})
    assemble(load_site(umbrella))
    (lev.parent / "docs" / "old.md").unlink()

    assembly = assemble(load_site(umbrella))

    assert not (assembly.docs_dir / "lev" / "old.md").exists()


def test_auto_nav_for_project_without_nav(make_project: Callable[..., Path]) -> None:
    make_project(
        "lev",
        files={
            "zeta.md": "# Zeta\n",
            "index.md": "# lev\n",
            "getting_started/index.md": "# Start\n",
            "getting_started/install.md": "# Install\n",
            "Alpha.md": "# Alpha\n",
            "img/logo.png": "png",
        },
    )
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}]})

    assemble(load_site(umbrella))

    assert read_generated(umbrella)["nav"] == [
        {
            "lev": [
                "lev/index.md",
                "lev/Alpha.md",
                {"Getting started": ["lev/getting_started/index.md", "lev/getting_started/install.md"]},
                "lev/zeta.md",
            ]
        }
    ]


def test_untitled_section_takes_title_of_index_page(make_project: Callable[..., Path]) -> None:
    # Like Typer, which relies on `navigation.indexes` to show the index page title for untitled sections.
    nav = [
        "index.md",
        {"": ["tutorial/index.md", "tutorial/install.md", {"": ["tutorial/arguments/index.md"]}]},
        {"": ["guide/README.md"]},
        {"": [{"Custom": "faq/index.md"}]},
        {"": ["misc/page.md"]},
    ]
    files = {
        "index.md": "# lev\n",
        "tutorial/index.md": "# Learn\n",
        "tutorial/install.md": "# Install\n",
        "tutorial/arguments/index.md": "```\n# not a title\n```\n# CLI Arguments\n",
        "guide/README.md": "---\ntitle: Guide\n---\n# Heading\n",
        "faq/index.md": "# FAQ\n",
        "misc/page.md": "# Page\n",
    }
    make_project("lev", {"nav": nav}, files=files)
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}]})

    assemble(load_site(umbrella))

    assert read_generated(umbrella)["nav"] == [
        {
            "lev": [
                "lev/index.md",
                {
                    "Learn": [
                        "lev/tutorial/index.md",
                        "lev/tutorial/install.md",
                        {"CLI Arguments": ["lev/tutorial/arguments/index.md"]},
                    ]
                },
                {"Guide": ["lev/guide/README.md"]},
                {"Custom": [{"Custom": "lev/faq/index.md"}]},
                {"": ["lev/misc/page.md"]},
            ]
        }
    ]


def test_auto_nav_ignores_files_of_other_projects(make_project: Callable[..., Path]) -> None:
    make_project("lev")
    make_project("extra", files={"page.md": "# Extra\n"})
    umbrella = make_project(
        "umbrella",
        {"nav": [{"lev": "!include ../lev"}, {"extra": "!include ../extra"}]},
        zmerge={"projects": {"extra": {"prefix": "lev/extra"}}},
    )

    assemble(load_site(umbrella))

    assert read_generated(umbrella)["nav"] == [{"lev": ["lev/index.md"]}, {"extra": ["lev/extra/page.md"]}]


def test_nested_include(make_project: Callable[..., Path]) -> None:
    make_project("core", {"nav": [{"Core": "index.md"}]})
    make_project("lev", {"nav": [{"Home": "index.md"}, {"Core": "!include ../core"}]})
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}]})

    assemble(load_site(umbrella))

    assert read_generated(umbrella)["nav"] == [
        {"lev": [{"Home": "lev/index.md"}, {"Core": [{"Core": "lev/core/index.md"}]}]}
    ]


def test_skips_hidden_files_and_custom_dir(make_project: Callable[..., Path]) -> None:
    make_project(
        "lev",
        {"theme": {"custom_dir": "docs/overrides"}},
        files={"index.md": "# lev\n", ".hidden.md": "x", ".git/x": "x", "overrides/main.html": "<html/>"},
    )
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}]})

    assert sorted(assemble(load_site(umbrella)).files) == ["index.md", "lev/index.md"]


def test_collision(make_project: Callable[..., Path]) -> None:
    make_project("lev")
    umbrella = make_project(
        "umbrella", {"nav": [{"lev": "!include ../lev"}]}, files={"index.md": "# Home\n", "lev/index.md": "# Clash\n"}
    )

    with pytest.raises(ZmergeError, match=r"would both be merged to 'lev/index\.md'"):
        assemble(load_site(umbrella))


@pytest.mark.parametrize("nav", [[{"Missing": "missing.md"}], ["missing.md"]])
def test_missing_nav_target(make_project: Callable[..., Path], nav: list[object]) -> None:
    make_project("lev", {"nav": nav})
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}]})

    with pytest.raises(ZmergeError, match=r"'missing\.md' points to a missing page"):
        assemble(load_site(umbrella))


def test_project_without_pages(make_project: Callable[..., Path]) -> None:
    make_project("lev", files={"logo.png": "png"})
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}]})

    with pytest.raises(ZmergeError, match="has no pages"):
        assemble(load_site(umbrella))


def test_umbrella_nav_may_point_into_projects(make_project: Callable[..., Path]) -> None:
    make_project("lev")
    umbrella = make_project("umbrella", {"nav": [{"Start": "lev/index.md"}, {"Sec": [{"lev": "!include ../lev"}]}]})

    assemble(load_site(umbrella))

    assert read_generated(umbrella)["nav"] == [{"Start": "lev/index.md"}, {"Sec": [{"lev": ["lev/index.md"]}]}]


def test_assemble_is_incremental(make_project: Callable[..., Path]) -> None:
    files = {
        "index.md": "# lev\n",
        "link.md": "[d](https://example.org/dame/)\n",
        "old/page.md": "# Old\n",
        "edited.md": "# v1\n",
    }
    nav = ["index.md", "link.md", "edited.md"]
    lev = make_project("lev", {"site_url": "https://example.org/lev/", "nav": nav}, files=files)
    make_project("dame", {"site_url": "https://example.org/dame/"})
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}, {"dame": "!include ../dame"}]})
    first = assemble(load_site(umbrella))
    docs = first.docs_dir
    before = {p: (docs / p).stat().st_ino for p in ("lev/index.md", "lev/link.md")}
    config_mtime = first.config_file.stat().st_mtime_ns

    # Editors often save by replacing the file, which breaks the hardlink.
    source = lev.parent / "docs"
    (source / "edited.new").write_text("# v2\n", encoding="utf-8")
    (source / "edited.new").replace(source / "edited.md")
    shutil.rmtree(source / "old")
    second = assemble(load_site(umbrella))

    assert {p: (docs / p).stat().st_ino for p in before} == before
    assert second.config_file.stat().st_mtime_ns == config_mtime
    assert (docs / "lev" / "edited.md").read_text(encoding="utf-8") == "# v2\n"
    assert (docs / "lev" / "edited.md").samefile(source / "edited.md")
    assert not (docs / "lev" / "old").exists()
    assert (docs / "lev" / "link.md").read_text(encoding="utf-8") == "[d](../dame/index.md)\n"


def test_excluded_pages_are_not_rewritten(make_project: Callable[..., Path]) -> None:
    dead = "[gone](https://example.org/dame/gone/)\n"
    files = {"index.md": dead, "notes.md": dead, "old/a.md": dead}
    make_project("dame", {"site_url": "https://example.org/dame/", "exclude_docs": "notes.md\n"}, files=files)
    umbrella = make_project(
        "umbrella",
        {"site_url": "https://example.org/", "exclude_docs": "/dame/old/\n", "nav": [{"dame": "!include ../dame"}]},
    )

    assembly = assemble(load_site(umbrella))

    # Only the page Zensical builds is checked.
    (warning,) = assembly.warnings
    assert warning.startswith("dame/index.md:")
    for page in ("notes.md", "old/a.md"):
        assert (assembly.docs_dir / "dame" / page).read_text(encoding="utf-8") == dead


def test_assemble_replaces_files_and_directories(make_project: Callable[..., Path]) -> None:
    lev = make_project("lev", files={"index.md": "# lev\n", "a.md": "# A\n", "b/index.md": "# B\n"})
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}]})
    assemble(load_site(umbrella))
    source = lev.parent / "docs"
    (source / "a.md").unlink()
    (source / "a.md").mkdir()
    (source / "a.md" / "index.md").write_text("# A dir\n", encoding="utf-8")
    shutil.rmtree(source / "b")
    (source / "b").write_text("b", encoding="utf-8")

    assembly = assemble(load_site(umbrella))

    assert (assembly.docs_dir / "lev" / "a.md" / "index.md").read_text(encoding="utf-8") == "# A dir\n"
    assert (assembly.docs_dir / "lev" / "b").read_text(encoding="utf-8") == "b"


def test_copies_are_refreshed_when_the_source_changes(make_project: Callable[..., Path]) -> None:
    lev = make_project("lev")
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}]})
    with mock.patch("os.link", side_effect=OSError("no links")):
        assemble(load_site(umbrella))
        (lev.parent / "docs" / "index.md").write_text("# lev, longer\n", encoding="utf-8")
        assembly = assemble(load_site(umbrella))

    assert (assembly.docs_dir / "lev" / "index.md").read_text(encoding="utf-8") == "# lev, longer\n"


def test_collect_files_basic(make_project: Callable[..., Path]) -> None:
    make_project("p0", files={"index.md": "# P0\n"})
    umbrella_path = make_project("umbrella", {"nav": [{"p0": "!include ../p0"}]}, files={"index.md": "# Home\n"})
    site = load_site(umbrella_path)

    files = collect_files(site)

    assert set(files.keys()) == {"index.md", "p0/index.md"}
    assert files["index.md"].owner == ""
    assert files["index.md"].path == site.docs_dir / "index.md"


def test_collect_files_with_prefixes(make_project: Callable[..., Path]) -> None:
    make_project("p1", files={"index.md": "# P1\n", "p1_specific.md": "content"})
    make_project("p2", files={"index.md": "# P2\n", "p2_specific.md": "content"})
    umbrella_path = make_project(
        "umbrella2",
        {"nav": [{"p1": "!include ../p1"}, {"p2": "!include ../p2"}]},
        zmerge={"projects": {"p1": {"prefix": "nested/path"}, "p2": {"prefix": "p2_pref"}}},
        files={"umbrella.md": "# Umbrella\n"},
    )
    site = load_site(umbrella_path)

    files = collect_files(site)

    assert set(files.keys()) == {
        "umbrella.md",
        "nested/path/index.md",
        "nested/path/p1_specific.md",
        "p2_pref/index.md",
        "p2_pref/p2_specific.md",
    }
    assert files["umbrella.md"].owner == ""
    assert files["nested/path/index.md"].owner == "nested/path"
    assert files["p2_pref/p2_specific.md"].owner == "p2_pref"


def test_write_if_changed_overwrites_non_utf8_file(tmp_path: Path) -> None:
    target = tmp_path / "page.md"
    target.write_bytes(b"\xff")

    _write_if_changed(target, "new text")

    assert target.read_text(encoding="utf-8") == "new text"

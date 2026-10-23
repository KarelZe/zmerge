from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from zmerge.config import Include, Link, Section, ZmergeError, load_site

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def test_load_site_resolves_includes(make_project: Callable[..., Path]) -> None:
    lev = make_project("lev", {"nav": [{"Home": "index.md"}, {"API": "api.md"}]})
    datamodel = make_project("datamodel-code-generator", {"docs_dir": "documentation"}, docs_dir="documentation")
    umbrella = make_project(
        "umbrella",
        {
            "nav": [
                {"Home": "index.md"},
                {"lev": "!include ../lev/zensical.toml"},
                {"Projects": ["!include ../datamodel-code-generator", {"GitHub": "https://github.com"}]},
            ]
        },
    )

    site = load_site(umbrella)

    assert site.root == umbrella.parent
    assert site.docs_dir == umbrella.parent / "docs"
    home, lev_include, projects = site.nav
    assert home == Link(title="Home", target="index.md")
    assert isinstance(lev_include, Include)
    assert lev_include.title == "lev"
    assert lev_include.project.prefix == "lev"
    assert lev_include.project.config_file == lev
    assert lev_include.project.nav == (Link("Home", "index.md"), Link("API", "api.md"))
    assert isinstance(projects, Section)
    datamodel_include, github = projects.items
    assert isinstance(datamodel_include, Include)
    # Without a nav title, the child's site name is used.
    assert datamodel_include.title == "datamodel-code-generator"
    assert datamodel_include.project.docs_dir == datamodel.parent / "documentation"
    assert datamodel_include.project.nav is None
    assert github == Link("GitHub", "https://github.com")
    assert [p.prefix for p in site.projects] == ["lev", "datamodel-code-generator"]


def test_prefix_override(make_project: Callable[..., Path]) -> None:
    make_project("lev")
    umbrella = make_project(
        "umbrella",
        {"nav": [{"Levenshtein distance": "!include ../lev/zensical.toml"}]},
        zmerge={"projects": {"levenshtein-distance": {"prefix": "libs/lev"}}},
    )

    (project,) = load_site(umbrella).projects

    assert project.id == "levenshtein-distance"
    assert project.prefix == "libs/lev"


def test_nested_includes_are_prefixed(make_project: Callable[..., Path]) -> None:
    make_project("core")
    make_project("lev", {"nav": [{"Home": "index.md"}, {"Core": "!include ../core/zensical.toml"}]})
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev/zensical.toml"}]})

    assert [p.prefix for p in load_site(umbrella).projects] == ["lev", "lev/core"]


@pytest.mark.parametrize(
    ("nav", "zmerge", "message"),
    [
        ([{"Home": "index.md"}], None, "contains no `!include`"),
        ([{"a": "!include ../missing/zensical.toml"}], None, "configuration file not found"),
        ([{"a": "!include ../lev/mkdocs.yml"}], None, "must point to a `zensical.toml`"),
        ([{"a": "!include"}], None, "needs a path"),
        ([{"lev": "!include ../lev"}, {"Lev": "!include ../lev"}], None, "duplicate project id"),
        ([{"lev": "!include ../lev"}], {"projects": {"lev": {"prefx": "x"}}}, "unknown option"),
        ([{"lev": "!include ../lev"}], {"projects": {"other": {}}}, "unknown project"),
        ([{"lev": "!include ../lev"}], {"projects": {"lev": {"prefix": "../x"}}}, "invalid prefix"),
        ([{"lev": "!include ../lev"}], {"projects": {"lev": {"prefix": "templates"}}}, "invalid prefix"),
        (
            [{"a": "!include ../lev"}, {"b": "!include ../lev"}],
            {"projects": {"b": {"prefix": "a"}}},
            "already used",
        ),
        ([{"???": "!include ../lev"}], None, "cannot derive a project id"),
        ([{"a": "b", "c": "d"}], None, "invalid nav entry"),
        ([{"a": 1}], None, "invalid nav entry"),
    ],
)
def test_invalid_umbrella(
    make_project: Callable[..., Path], nav: list[object], zmerge: dict[str, object] | None, message: str
) -> None:
    make_project("lev")
    umbrella = make_project("umbrella", {"nav": nav}, zmerge=zmerge)

    with pytest.raises(ZmergeError, match=message):
        load_site(umbrella)


def test_umbrella_without_nav(make_project: Callable[..., Path]) -> None:
    with pytest.raises(ZmergeError, match="needs a `nav`"):
        load_site(make_project("umbrella"))


def test_nav_must_be_a_list(make_project: Callable[..., Path]) -> None:
    with pytest.raises(ZmergeError, match="must be a list"):
        load_site(make_project("umbrella", {"nav": "index.md"}))


def test_missing_docs_dir(make_project: Callable[..., Path]) -> None:
    make_project("lev", {"docs_dir": "nope"})
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}]})

    with pytest.raises(ZmergeError, match="does not exist"):
        load_site(umbrella)


def test_missing_site_name(make_project: Callable[..., Path], tmp_path: Path) -> None:
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}]})
    (tmp_path / "lev").mkdir()
    (tmp_path / "lev" / "zensical.toml").write_text("[project]\n", encoding="utf-8")

    with pytest.raises(ZmergeError, match="`site_name` is required"):
        load_site(umbrella)


def test_invalid_toml(tmp_path: Path) -> None:
    config_file = tmp_path / "zensical.toml"
    config_file.write_text("[project\n", encoding="utf-8")

    with pytest.raises(ZmergeError, match="invalid TOML"):
        load_site(config_file)


def test_circular_include(make_project: Callable[..., Path]) -> None:
    make_project("a", {"nav": [{"b": "!include ../b"}]})
    make_project("b", {"nav": [{"a": "!include ../a"}]})
    umbrella = make_project("umbrella", {"nav": [{"a": "!include ../a"}]})

    with pytest.raises(ZmergeError, match="circular"):
        load_site(umbrella)


def test_top_level_table_without_project(tmp_path: Path, make_project: Callable[..., Path]) -> None:
    make_project("lev")
    (tmp_path / "umbrella" / "docs").mkdir(parents=True)
    config_file = tmp_path / "umbrella" / "zensical.toml"
    config_file.write_text('site_name = "u"\nnav = [{ lev = "!include ../lev" }]\n', encoding="utf-8")

    assert [p.prefix for p in load_site(config_file).projects] == ["lev"]

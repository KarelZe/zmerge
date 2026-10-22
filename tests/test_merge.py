from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from zmerge.config import ZmergeError, load_site
from zmerge.merge import merge_config, normalize_extensions

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from zmerge.config import Site


@pytest.fixture
def two_projects(make_project: Callable[..., Path]) -> Callable[..., Site]:
    def factory(umbrella: dict[str, object], lev: dict[str, object], dame: dict[str, object] | None = None) -> Site:
        make_project("lev", lev)
        make_project("dame", dame or {})
        config_file = make_project(
            "umbrella", {**umbrella, "nav": [{"lev": "!include ../lev"}, {"dame": "!include ../dame"}]}
        )
        return load_site(config_file)

    return factory


def test_umbrella_owns_site_settings(two_projects: Callable[..., Site]) -> None:
    site = two_projects(
        {"site_url": "https://example.org/", "theme": {"variant": "modern"}},
        {"site_url": "https://lev.example.org/", "theme": {"variant": "classic"}, "extra": {"x": 1}},
    )

    config, warnings = merge_config(site)

    assert config["site_url"] == "https://example.org/"
    assert config["theme"] == {"variant": "modern"}
    assert "extra" not in config
    assert "nav" not in config
    assert warnings == []


def test_no_extensions_anywhere_keeps_zensical_defaults(two_projects: Callable[..., Site]) -> None:
    config, warnings = merge_config(two_projects({}, {}))

    assert "markdown_extensions" not in config
    assert "plugins" not in config
    assert warnings == []


def test_markdown_extensions_are_combined(two_projects: Callable[..., Site]) -> None:
    site = two_projects(
        {"markdown_extensions": {"toc": {"permalink": True}, "pymdownx": {"superfences": {}}}},
        {"markdown_extensions": ["admonition", {"pymdownx.arithmatex": {"generic": True}}]},
        {"markdown_extensions": {"toc": {"permalink": False}, "pymdownx": {"blocks": {"admonition": {}}}}},
    )

    config, warnings = merge_config(site)

    assert config["markdown_extensions"] == {
        "toc": {"permalink": True},
        "pymdownx.superfences": {},
        "admonition": {},
        "pymdownx.arithmatex": {"generic": True},
        "pymdownx.blocks.admonition": {},
    }
    (warning,) = warnings
    assert "options of markdown extension 'toc' differ" in warning


def test_warns_when_defaults_are_replaced(two_projects: Callable[..., Site]) -> None:
    site = two_projects({"markdown_extensions": {"toc": {}}}, {})

    _, warnings = merge_config(site)

    assert len(warnings) == 2
    assert all("relies on Zensical's default markdown extensions" in w for w in warnings)


def test_plugins_are_combined(two_projects: Callable[..., Site]) -> None:
    site = two_projects(
        {"plugins": {"search": {}}},
        {"plugins": ["search", {"tags": {"listings": True}}]},
        {"plugins": {"tags": {"listings": False}}},
    )

    config, warnings = merge_config(site)

    assert config["plugins"] == {"search": {}, "tags": {"listings": True}}
    (warning,) = warnings
    assert "options of plugin 'tags' differ" in warning


def test_mkdocstrings_paths_are_rebased(two_projects: Callable[..., Site], tmp_path: Path) -> None:
    options = {"docstring_style": "google"}
    site = two_projects(
        {"plugins": {"mkdocstrings": {"handlers": {"python": {"paths": ["src"]}}}}},
        {"plugins": {"mkdocstrings": {"handlers": {"python": {"options": options}}}}},
        {
            "plugins": {
                "mkdocstrings": {
                    "default_handler": "python",
                    "handlers": {"python": {"paths": ["python", "/abs"], "options": {"show_source": True}}},
                }
            }
        },
    )

    config, warnings = merge_config(site)

    python = config["plugins"]["mkdocstrings"]["handlers"]["python"]
    assert python["paths"] == ["src", (tmp_path / "lev").as_posix(), (tmp_path / "dame" / "python").as_posix(), "/abs"]
    assert python["options"] == options
    assert config["plugins"]["mkdocstrings"]["default_handler"] == "python"
    (warning,) = warnings
    assert "`handlers.python.options` differs" in warning


def test_mkdocstrings_global_option_conflict(two_projects: Callable[..., Site]) -> None:
    site = two_projects(
        {"plugins": {"mkdocstrings": {"locale": "en"}}}, {"plugins": {"mkdocstrings": {"locale": "de"}}}
    )

    _, warnings = merge_config(site)

    assert ["mkdocstrings option 'locale' differs" in w for w in warnings] == [True]


def test_extra_assets_are_prefixed_and_deduplicated(two_projects: Callable[..., Site]) -> None:
    mathjax = {"path": "https://unpkg.com/mathjax@3/es5/tex-mml-chtml.js", "async": True}
    site = two_projects(
        {"extra_css": ["css/site.css"]},
        {"extra_javascript": ["./js/mathjax.js", mathjax], "extra_css": ["https://cdn.example.org/x.css"]},
        {"extra_javascript": [{"path": "js/mathjax.js"}, mathjax, "/absolute.js"]},
    )

    config, _ = merge_config(site)

    assert config["extra_css"] == ["css/site.css", "https://cdn.example.org/x.css"]
    assert config["extra_javascript"] == [
        "lev/js/mathjax.js",
        mathjax,
        {"path": "dame/js/mathjax.js"},
        "/absolute.js",
    ]


def test_patterns_are_prefixed(two_projects: Callable[..., Site]) -> None:
    site = two_projects({"exclude_docs": "drafts/\n"}, {"exclude_docs": "*.tmp\n", "not_in_nav": "/hidden.md"})

    config, _ = merge_config(site)

    assert config["exclude_docs"] == "drafts/\n/lev/**/*.tmp\n"
    assert config["not_in_nav"] == "/lev/hidden.md\n"
    assert "draft_docs" not in config


@pytest.mark.parametrize(
    ("value", "message"),
    [("toc", "must be a list or a table"), ([1], "invalid markdown extension")],
)
def test_invalid_extensions(value: object, message: str, tmp_path: Path) -> None:
    with pytest.raises(ZmergeError, match=message):
        normalize_extensions(value, config_file=tmp_path)


@pytest.mark.parametrize(("value", "message"), [("search", "must be a list or a table"), ([1], "invalid plugin")])
def test_invalid_plugins(two_projects: Callable[..., Site], value: object, message: str) -> None:
    site = two_projects({}, {"plugins": value})

    with pytest.raises(ZmergeError, match=message):
        merge_config(site)

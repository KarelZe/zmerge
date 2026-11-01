from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from zmerge.config import ZmergeError, load_site
from zmerge.merge import MergedConfig, merge_config, normalize_extensions

if TYPE_CHECKING:
    from collections.abc import Callable

    from zmerge.config import Site


def unpack(merged: MergedConfig) -> tuple[dict[str, Any], list[str]]:
    return merged.config, merged.warnings


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

    config, warnings = unpack(merge_config(site))

    assert config["site_url"] == "https://example.org/"
    assert config["theme"] == {"variant": "modern"}
    assert "extra" not in config
    assert "nav" not in config
    assert warnings == []


def test_no_extensions_anywhere_keeps_zensical_defaults(two_projects: Callable[..., Site]) -> None:
    config, warnings = unpack(merge_config(two_projects({}, {})))

    assert "markdown_extensions" not in config
    assert "plugins" not in config
    assert warnings == []


def test_markdown_extensions_are_combined(two_projects: Callable[..., Site]) -> None:
    site = two_projects(
        {"markdown_extensions": {"toc": {"permalink": True}, "pymdownx": {"superfences": {}}}},
        {"markdown_extensions": ["admonition", {"pymdownx.arithmatex": {"generic": True}}]},
        {"markdown_extensions": {"toc": {"permalink": False}, "pymdownx": {"blocks": {"admonition": {}}}}},
    )

    config, warnings = unpack(merge_config(site))

    assert config["markdown_extensions"] == {
        "toc": {"permalink": True},
        "pymdownx.superfences": {},
        "admonition": {},
        "pymdownx.arithmatex": {"generic": True},
        "pymdownx.blocks.admonition": {},
    }
    (warning,) = warnings
    assert "options ['permalink'] of markdown extension 'toc' differ" in warning


def test_warns_when_defaults_are_replaced(two_projects: Callable[..., Site]) -> None:
    site = two_projects({"markdown_extensions": {"toc": {}}}, {})

    _, warnings = unpack(merge_config(site))

    assert len(warnings) == 2
    assert all("relies on Zensical's default markdown extensions" in w for w in warnings)


def test_warns_about_untitled_sections_without_navigation_indexes(two_projects: Callable[..., Site]) -> None:
    lev = {"nav": [{"Guide": [{"": ["index.md"]}]}]}

    _, warnings = unpack(merge_config(two_projects({}, lev)))
    (warning,) = warnings
    assert f"{Path('lev') / 'zensical.toml'}: nav has untitled sections" in warning

    _, warnings = unpack(merge_config(two_projects({"theme": {"features": ["navigation.indexes"]}}, lev)))
    assert warnings == []


def test_plugins_are_combined(two_projects: Callable[..., Site]) -> None:
    site = two_projects(
        {"plugins": {"search": {}}},
        {"plugins": ["search", {"tags": {"listings": True}}]},
        {"plugins": {"tags": {"listings": False}}},
    )

    config, warnings = unpack(merge_config(site))

    assert config["plugins"] == {"search": {}, "tags": {"listings": True}}
    (warning,) = warnings
    assert "options ['listings'] of plugin 'tags' differ" in warning


def test_mkdocstrings_paths_are_rebased(two_projects: Callable[..., Site], tmp_path: Path) -> None:
    site = two_projects(
        {"plugins": {"mkdocstrings": {"handlers": {"python": {"paths": ["src"]}}}}},
        {"plugins": {"mkdocstrings": {"handlers": {"python": {"options": {"docstring_style": "google"}}}}}},
        {
            "plugins": {
                "mkdocstrings": {"default_handler": "python", "handlers": {"python": {"paths": ["python", "/abs"]}}}
            }
        },
    )

    merged = merge_config(site)

    mkdocstrings = merged.config["plugins"]["mkdocstrings"]
    python = mkdocstrings["handlers"]["python"]
    absolute = (tmp_path / "/abs").resolve().as_posix()  # on the drive of the project on Windows
    assert python["paths"] == [
        "src",
        (tmp_path / "lev").as_posix(),
        (tmp_path / "dame" / "python").as_posix(),
        absolute,
    ]
    assert mkdocstrings["default_handler"] == merged.default_handler == "python"
    assert merged.warnings == []


def test_mkdocstrings_options_per_project(two_projects: Callable[..., Site]) -> None:
    site = two_projects(
        {},
        {"plugins": {"mkdocstrings": {"handlers": {"python": {"options": {"show_source": False, "x": 1}}}}}},
        {"plugins": {"mkdocstrings": {"handlers": {"python": {"options": {"show_source": True, "heading_level": 3}}}}}},
    )

    merged = merge_config(site)

    # The projects share no option, so each project sets its own and keeps the handler's defaults for the rest.
    assert "options" not in merged.config["plugins"]["mkdocstrings"]["handlers"]["python"]
    assert merged.directive_options == {
        "lev": {"python": {"show_source": False, "x": 1}},
        "dame": {"python": {"show_source": True, "heading_level": 3}},
    }
    assert merged.warnings == []


def test_mkdocstrings_common_options_stay_global(two_projects: Callable[..., Site]) -> None:
    site = two_projects(
        {"plugins": {"mkdocstrings": {"handlers": {"python": {"options": {"heading_level": 2}}}}}},
        {
            "plugins": {
                "mkdocstrings": {"handlers": {"python": {"options": {"show_source": False, "heading_level": 3}}}}
            }
        },
        {"plugins": {"mkdocstrings": {"handlers": {"python": {"options": {"show_source": False, "summary": True}}}}}},
    )

    merged = merge_config(site)

    # Options of the umbrella project apply to all projects that don't set them differently.
    assert merged.config["plugins"]["mkdocstrings"]["handlers"]["python"]["options"] == {
        "show_source": False,
        "heading_level": 2,
    }
    assert merged.directive_options == {"lev": {"python": {"heading_level": 3}}, "dame": {"python": {"summary": True}}}


def test_mkdocstrings_project_without_options(two_projects: Callable[..., Site]) -> None:
    site = two_projects(
        {},
        {"plugins": {"mkdocstrings": {"handlers": {"rust": {"options": {"a": 1}}}}}},
        {"plugins": {"mkdocstrings": {}}},
    )

    merged = merge_config(site)

    # dame keeps the handler's defaults, which zmerge doesn't need to know.
    assert "options" not in merged.config["plugins"]["mkdocstrings"]["handlers"]["rust"]
    assert merged.directive_options == {"lev": {"rust": {"a": 1}}}
    assert merged.warnings == []


def test_snippet_base_paths_are_combined(two_projects: Callable[..., Site], tmp_path: Path) -> None:
    snippets = {"pymdownx": {"snippets": {"check_paths": True}}}
    site = two_projects(
        {"markdown_extensions": snippets},
        {"markdown_extensions": {"pymdownx.snippets": {"check_paths": True, "base_path": ["docs", "."]}}},
        {"markdown_extensions": {"pymdownx.snippets": {"base_path": "."}}},
    )

    config, warnings = unpack(merge_config(site))

    assert config["markdown_extensions"]["pymdownx.snippets"] == {
        "check_paths": True,
        "base_path": [
            ".",
            (tmp_path / "lev" / "docs").as_posix(),
            (tmp_path / "lev").as_posix(),
            (tmp_path / "dame").as_posix(),
        ],
    }
    assert warnings == []


def test_mkdocstrings_global_option_conflict(two_projects: Callable[..., Site]) -> None:
    site = two_projects(
        {"plugins": {"mkdocstrings": {"locale": "en"}}}, {"plugins": {"mkdocstrings": {"locale": "de"}}}
    )

    _, warnings = unpack(merge_config(site))

    assert ["mkdocstrings option 'locale' differs" in w for w in warnings] == [True]


def test_extra_assets_are_prefixed_and_deduplicated(two_projects: Callable[..., Site]) -> None:
    mathjax = {"path": "https://unpkg.com/mathjax@3/es5/tex-mml-chtml.js", "async": True}
    site = two_projects(
        {"extra_css": ["css/site.css"]},
        {"extra_javascript": ["./js/mathjax.js", mathjax], "extra_css": ["https://cdn.example.org/x.css"]},
        {"extra_javascript": [{"path": "js/mathjax.js"}, mathjax, "/absolute.js"]},
    )

    config, _ = unpack(merge_config(site))

    assert config["extra_css"] == ["css/site.css", "https://cdn.example.org/x.css"]
    assert config["extra_javascript"] == [
        "lev/js/mathjax.js",
        mathjax,
        {"path": "dame/js/mathjax.js"},
        "/absolute.js",
    ]


MATHJAX = "https://unpkg.com/mathjax@3/es5/tex-mml-chtml.js"
KATEX = "https://unpkg.com/katex@0.16.9/dist/katex.min.js"


def test_extra_assets_without_conflicts_do_not_warn(two_projects: Callable[..., Site]) -> None:
    site = two_projects(
        {},
        {"extra_javascript": ["javascripts/mathjax.js", MATHJAX]},
        {"extra_javascript": ["javascripts/mathjax.js", {"path": MATHJAX, "async": True}]},
    )

    _, warnings = unpack(merge_config(site))

    assert warnings == []


def test_conflicting_math_renderers_warn(two_projects: Callable[..., Site]) -> None:
    site = two_projects(
        {},
        {"extra_javascript": ["javascripts/mathjax.js", MATHJAX]},
        {
            "extra_javascript": ["javascripts/katex.js", KATEX],
            "extra_css": ["https://unpkg.com/katex@0.16.9/dist/katex.min.css"],
        },
    )

    _, warnings = unpack(merge_config(site))

    assert len(warnings) == 1
    assert warnings[0].startswith("conflicting math renderers: MathJax in ")
    assert "lev" in warnings[0]
    assert "; KaTeX in " in warnings[0]
    assert "dame" in warnings[0]


@pytest.mark.parametrize(
    ("lev", "dame", "versions"),
    [
        (MATHJAX, "https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-mml-chtml.js", ("3 (", "3.2.2 (")),
        (KATEX, "https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.8/katex.min.js", ("0.16.9 (", "0.16.8 (")),
        (KATEX, "https://example.org/katex.min.js", ("0.16.9 (", "unversioned (")),
    ],
)
def test_library_versions_warn(
    two_projects: Callable[..., Site], lev: str, dame: str, versions: tuple[str, str]
) -> None:
    site = two_projects({}, {"extra_javascript": [lev]}, {"extra_javascript": [dame]})

    _, warnings = unpack(merge_config(site))

    assert len(warnings) == 1
    assert "is loaded in several versions" in warnings[0]
    assert all(version in warnings[0] for version in versions)


def test_library_from_several_urls_warns(two_projects: Callable[..., Site]) -> None:
    jsdelivr = "https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"
    site = two_projects({}, {"extra_javascript": [KATEX]}, {"extra_javascript": [jsdelivr]})

    _, warnings = unpack(merge_config(site))

    assert len(warnings) == 1
    assert warnings[0].startswith("KaTeX 'katex.min.js' is loaded from several URLs: ")
    assert KATEX in warnings[0]
    assert jsdelivr in warnings[0]


def test_patterns_are_prefixed(two_projects: Callable[..., Site]) -> None:
    site = two_projects({"exclude_docs": "drafts/\n"}, {"exclude_docs": "*.tmp\n", "not_in_nav": "/hidden.md"})

    config, _ = unpack(merge_config(site))

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


def test_extension_options_are_merged_per_key(two_projects: Callable[..., Site]) -> None:
    fences = [{"name": "mermaid", "class": "mermaid"}]
    site = two_projects(
        {"markdown_extensions": {"pymdownx": {"superfences": {}}}},
        {"markdown_extensions": {"pymdownx": {"superfences": {"custom_fences": fences}}}},
        {"markdown_extensions": {}},
    )

    config, warnings = unpack(merge_config(site))

    assert config["markdown_extensions"]["pymdownx.superfences"] == {"custom_fences": fences}
    assert warnings == []

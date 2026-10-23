from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

import pytest

from zmerge.cli import main
from zmerge.config import ZmergeError, load_site
from zmerge.mkdocs import load_mkdocs_config

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text), encoding="utf-8")
    return path


def test_inherit_merges_mappings_and_appends_lists(tmp_path: Path) -> None:
    write(
        tmp_path / "base.yml",
        """
        site_name: base
        markdown_extensions:
          - toc:
              permalink: true
        theme:
          name: material
          features: [a]
        """,
    )
    config_file = write(
        tmp_path / "mkdocs.yml",
        """
        INHERIT: base.yml
        site_name: lev
        markdown_extensions:
          - admonition
        theme:
          features: [b]
        """,
    )

    assert load_mkdocs_config(config_file) == {
        "site_name": "lev",
        "markdown_extensions": [{"toc": {"permalink": True}}, "admonition"],
        "theme": {"name": "material", "features": ["a", "b"]},
    }


def test_tags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LINENUMS", "true")
    monkeypatch.delenv("UNSET", raising=False)
    config_file = write(
        tmp_path / "mkdocs.yml",
        """
        site_name: lev
        nav:
          - lev: !include ../lev
        markdown_extensions:
          material.extensions.preview:
          pymdownx.highlight:
            linenums: !ENV [LINENUMS, false]
            anchor_linenums: !ENV [UNSET, false]
            title: !ENV UNSET
          pymdownx.superfences:
            custom_fences:
              - name: mermaid
                format: !!python/name:pymdownx.superfences.fence_code_format
          toc:
            slugify: !!python/object/apply:pymdownx.slugs.slugify
              kwds:
                case: lower
        """,
    )

    assert load_mkdocs_config(config_file) == {
        "site_name": "lev",
        "nav": [{"lev": "!include ../lev"}],
        "markdown_extensions": {
            "zensical.extensions.preview": {},
            "pymdownx.highlight": {"linenums": True, "anchor_linenums": False},
            "pymdownx.superfences": {
                "custom_fences": [{"name": "mermaid", "format": "pymdownx.superfences.fence_code_format"}]
            },
            "toc": {"slugify": {"object": "pymdownx.slugs.slugify", "kwds": {"case": "lower"}}},
        },
    }


@pytest.mark.parametrize(
    ("files", "message"),
    [
        ({"mkdocs.yml": "a: [b"}, "invalid YAML"),
        ({"mkdocs.yml": "- a"}, "must be a mapping"),
        ({"mkdocs.yml": "a: !!python/object:os.system {}"}, "unsupported tag"),
        ({"mkdocs.yml": "a: !ENV {b: c}"}, "expected a scalar or sequence node"),
        ({"mkdocs.yml": "INHERIT: missing.yml"}, "doesn't exist"),
        ({"mkdocs.yml": "INHERIT: base.yml", "base.yml": "INHERIT: mkdocs.yml"}, "circular `INHERIT`"),
    ],
)
def test_invalid(tmp_path: Path, files: dict[str, str], message: str) -> None:
    for name, text in files.items():
        write(tmp_path / name, text)

    with pytest.raises(ZmergeError, match=message):
        load_mkdocs_config(tmp_path / "mkdocs.yml")


def test_empty_and_missing(tmp_path: Path) -> None:
    assert load_mkdocs_config(write(tmp_path / "mkdocs.yml", "")) == {}
    with pytest.raises(ZmergeError, match="not found"):
        load_mkdocs_config(tmp_path / "missing.yml")


def test_include_mkdocs_project(make_project: Callable[..., Path], tmp_path: Path) -> None:
    write(tmp_path / "typer" / "docs" / "index.md", "# Typer\n")
    write(
        tmp_path / "typer" / "mkdocs.yml",
        """
        site_name: Typer
        nav: [index.md]
        zmerge:
          projects: {}
        """,
    )
    write(tmp_path / "typer-yaml" / "docs" / "index.md", "# Typer\n")
    write(tmp_path / "typer-yaml" / "mkdocs.yaml", "site_name: Typer YAML\n")
    umbrella = make_project("umbrella", {"nav": ["!include ../typer", "!include ../typer-yaml/mkdocs.yaml"]})

    typer, typer_yaml = load_site(umbrella).projects

    assert typer.config_file == tmp_path / "typer" / "mkdocs.yml"
    assert typer.config == {"site_name": "Typer", "nav": ["index.md"]}
    assert typer_yaml.prefix == "typer-yaml"


def test_include_mkdocs_project_needs_site_name(make_project: Callable[..., Path], tmp_path: Path) -> None:
    write(tmp_path / "typer" / "mkdocs.yml", "docs_dir: docs\n")
    umbrella = make_project("umbrella", {"nav": ["!include ../typer"]})

    with pytest.raises(ZmergeError, match="`site_name` is required"):
        load_site(umbrella)


def test_build_with_mkdocs_project(make_project: Callable[..., Path], tmp_path: Path) -> None:
    write(tmp_path / "typer" / "docs" / "index.md", "# Typer\n\n```mermaid\ngraph LR\n```\n\n[lev](../lev/index.md)\n")
    write(tmp_path / "typer" / "base.yml", "markdown_extensions:\n  - toc:\n      permalink: true\n")
    write(
        tmp_path / "typer" / "mkdocs.yml",
        """
        INHERIT: base.yml
        site_name: Typer
        markdown_extensions:
          - pymdownx.superfences:
              custom_fences:
                - name: mermaid
                  class: mermaid
                  format: !!python/name:pymdownx.superfences.fence_code_format
        """,
    )
    make_project("lev", {"markdown_extensions": {"toc": {"permalink": True}}})
    umbrella = make_project(
        "umbrella",
        {"markdown_extensions": {"toc": {"permalink": True}}, "nav": ["!include ../lev", "!include ../typer"]},
    )

    assert main(["build", "--strict", "-f", str(umbrella)]) == 0

    html = (umbrella.parent / "site" / "typer" / "index.html").read_text(encoding="utf-8")
    assert '<pre class="mermaid">' in html

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from zmerge.assemble import assemble
from zmerge.cli import main
from zmerge.config import load_site
from zmerge.directives import inject_options, rewrite_includes, rewrite_snippets

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

OPTIONS = {"python": {"show_source": True}}


def test_inject_options_into_directive_variants() -> None:
    text = (
        "## ::: pkg.a\n"
        "\n"
        '!!! note\n\n    ::: pkg.b\n        options:\n          show_source: false\n          members: ["x"]\n\n'
        "::: pkg.c\n    handler: rust\n\n"
        "```md\n::: pkg.d\n```\n"
        "::: pkg.e"
    )

    assert inject_options(text, OPTIONS, default_handler="python") == (
        "## ::: pkg.a\n"
        "    options:\n"
        "      show_source: true\n"
        "\n"
        "!!! note\n\n    ::: pkg.b\n        options:\n          show_source: false\n          members:\n          - x\n\n"
        "::: pkg.c\n    handler: rust\n\n"
        "```md\n::: pkg.d\n```\n"
        "::: pkg.e\n    options:\n      show_source: true"
    )


def test_inject_options_keeps_unrelated_text() -> None:
    text = "# Title\n\n::: pkg\nnot indented\n"

    assert inject_options(text, OPTIONS, default_handler="python") == (
        "# Title\n\n::: pkg\n    options:\n      show_source: true\nnot indented\n"
    )


def test_rewrite_snippets(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text("readme", encoding="utf-8")
    (tmp_path / "docs" / "part.md").write_text("part", encoding="utf-8")
    root, docs = tmp_path.as_posix(), (tmp_path / "docs").as_posix()
    text = (
        '--8<-- "README.md"\n'
        "--8<-- 'part.md:intro'\n"
        '    -8<- "README.md:1:3"\n'
        ';--8<-- "README.md"\n'
        '--8<-- "missing.md"\n'
        "--8<--\n"
        "part.md\n"
        "; README.md\n"
        "https://example.org/x.md\n"
        "  README.md\n"
        "--8<--\n"
        "README.md\n"
    )

    assert rewrite_snippets(text, [tmp_path / "docs", tmp_path]) == (
        f'--8<-- "{root}/README.md"\n'
        f"--8<-- '{docs}/part.md:intro'\n"
        f'    -8<- "{root}/README.md:1:3"\n'
        ';--8<-- "README.md"\n'
        '--8<-- "missing.md"\n'
        "--8<--\n"
        f"{docs}/part.md\n"
        "; README.md\n"
        "https://example.org/x.md\n"
        f"  {root}/README.md\n"
        "--8<--\n"
        "README.md\n"
    )


def test_snippets_resolve_per_project(make_project: Callable[..., Path], tmp_path: Path) -> None:
    snippets = {"markdown_extensions": {"pymdownx": {"snippets": {"check_paths": True}}}}
    for name in ("lev", "dame"):
        make_project(name, snippets, files={"index.md": '# Readme\n\n--8<-- "README.md"\n'})
        (tmp_path / name / "README.md").write_text(f"The {name} README.\n", encoding="utf-8")
    umbrella = make_project("umbrella", {**snippets, "nav": [{"lev": "!include ../lev"}, {"dame": "!include ../dame"}]})

    assert main(["build", "--strict", "-f", str(umbrella)]) == 0

    site = umbrella.parent / "site"
    assert "The lev README." in (site / "lev" / "index.html").read_text(encoding="utf-8")
    assert "The dame README." in (site / "dame" / "index.html").read_text(encoding="utf-8")


def test_mkdocstrings_options_per_project(make_project: Callable[..., Path], tmp_path: Path) -> None:
    for name, show_source in (("lev", False), ("dame", True)):
        make_project(
            name,
            {
                "markdown_extensions": {"toc": {"permalink": True}},
                "plugins": {
                    "mkdocstrings": {
                        "handlers": {"python": {"paths": ["src"], "options": {"show_source": show_source}}}
                    }
                },
            },
            files={"index.md": f"# API\n\n::: {name}_pkg\n"},
        )
        package = tmp_path / name / "src" / f"{name}_pkg"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text(
            '"""Package."""\n\n\ndef secret_body() -> int:\n    """Return 42."""\n    return 42\n', encoding="utf-8"
        )
    umbrella = make_project(
        "umbrella",
        {
            "markdown_extensions": {"toc": {"permalink": True}},
            "nav": [{"lev": "!include ../lev"}, {"dame": "!include ../dame"}],
        },
    )

    assembly = assemble(load_site(umbrella))
    assert assembly.warnings == []
    assert "show_source: true" in (assembly.docs_dir / "dame" / "index.md").read_text(encoding="utf-8")
    assert main(["build", "--strict", "-f", str(umbrella)]) == 0

    site = umbrella.parent / "site"
    assert "Source code in" not in (site / "lev" / "index.html").read_text(encoding="utf-8")
    assert "Source code in" in (site / "dame" / "index.html").read_text(encoding="utf-8")


def test_rewrite_includes(tmp_path: Path) -> None:
    (tmp_path / "docs_src").mkdir()
    (tmp_path / "docs_src" / "a.py").write_text("a = 1\n", encoding="utf-8")
    a = (tmp_path / "docs_src" / "a.py").as_posix()
    text = (
        "{* docs_src/a.py hl[1] *}\n"
        "{* docs_src/missing.py *}\n"
        "Inline {!docs_src/a.py!} and {!+> docs_src/a.py [ln:1-2] | utf-8 !}.\n"
        "\\{!docs_src/a.py!} {!https://example.org/a.py!}\n"
    )

    assert rewrite_includes(text, mdx_base=tmp_path, variants_base=tmp_path) == (
        f"{{* {a} hl[1] *}}\n"
        "{* docs_src/missing.py *}\n"
        f"Inline {{!{a}!}} and {{!+> {a} [ln:1-2] | utf-8 !}}.\n"
        "\\{!docs_src/a.py!} {!https://example.org/a.py!}\n"
    )
    assert rewrite_includes(text, mdx_base=None, variants_base=None) == text


def test_includes_resolve_per_project(make_project: Callable[..., Path], tmp_path: Path) -> None:
    extensions = {"markdown_extensions": {"mdx_include": {"base_path": "src"}, "markdown_include_variants": {}}}
    for name in ("lev", "dame"):
        make_project(name, extensions, files={"index.md": "{* docs_src/a.py *}\n\n{!a.md!}\n"})
        for path in ("docs_src/a.py", "src/a.md"):
            (tmp_path / name / path).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / name / path).write_text(name, encoding="utf-8")
    umbrella = make_project(
        "umbrella", {**extensions, "nav": [{"lev": "!include ../lev"}, {"dame": "!include ../dame"}]}
    )

    assembly = assemble(load_site(umbrella))

    for name in ("lev", "dame"):
        root = (tmp_path / name).as_posix()
        assert (assembly.docs_dir / name / "index.md").read_text(encoding="utf-8") == (
            f"{{* {root}/docs_src/a.py *}}\n\n{{!{root}/src/a.md!}}\n"
        )
    config = tomllib.loads(assembly.config_file.read_text(encoding="utf-8"))
    assert config["project"]["markdown_extensions"]["mdx_include"] == {}
    assert assembly.warnings == []


def test_rewrite_directives(tmp_path: Path) -> None:
    from unittest.mock import MagicMock

    from zmerge.directives import rewrite_directives

    project = MagicMock(prefix="pkg", config_file=tmp_path / "pkg.toml", root=tmp_path)
    project.config = {}
    site = MagicMock(projects=[project])

    (tmp_path / "pkg.md").write_text("::: pkg\n", encoding="utf-8")
    files = {
        "pkg.md": MagicMock(owner="pkg", path=tmp_path / "pkg.md"),
        "other.md": MagicMock(owner="pkg", path=tmp_path / "other.md"),
        "file.txt": MagicMock(owner="pkg", path=tmp_path / "file.txt"),
    }
    rewritten = {"other.md": "::: other\n"}

    merged = MagicMock(directive_options={"pkg": {"python": {"show_source": True}}}, default_handler="python")

    rewrite_directives(site, files, rewritten, merged, excluded=["other.md"])

    assert rewritten["pkg.md"] == "::: pkg\n    options:\n      show_source: true\n"
    assert rewritten["other.md"] == "::: other\n"
    assert "file.txt" not in rewritten

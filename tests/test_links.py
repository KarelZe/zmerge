from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from zmerge.assemble import assemble
from zmerge.cli import main
from zmerge.config import load_site
from zmerge.links import rewrite_destinations

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from zmerge.assemble import Assembly

LEV = {"site_url": "https://example.org/lev/", "repo_url": "https://github.com/me/lev", "edit_uri": "edit/main/docs/"}
DAME = {"site_url": "https://Example.org/dame-rs/"}


@pytest.fixture
def merge(make_project: Callable[..., Path]) -> Callable[..., Assembly]:
    def factory(lev_files: dict[str, str], *, lev: dict[str, object] | None = None, umbrella_index: str = "# Home\n"):
        make_project("lev", LEV if lev is None else lev, files=lev_files)
        make_project(
            "dame-rs",
            DAME,
            files={"index.md": "# dame\n", "design.md": "# Design\n\n## Opening book\n", "img/app.png": "png"},
        )
        umbrella = make_project(
            "umbrella",
            {"site_url": "https://example.org/", "nav": [{"lev": "!include ../lev"}, {"dame": "!include ../dame-rs"}]},
            files={"index.md": umbrella_index},
        )
        return assemble(load_site(umbrella))

    return factory


def staged(assembly: Assembly, path: str) -> str:
    return (assembly.docs_dir / path).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("link", "expected"),
    [
        ("https://example.org/dame-rs/design/#opening-book", "../../dame/design.md#opening-book"),
        ("https://example.org/dame-rs/design", "../../dame/design.md"),
        ("http://EXAMPLE.org/dame-rs/design.html", "../../dame/design.md"),
        ("https://example.org/dame-rs/", "../../dame/index.md"),
        ("https://example.org/dame-rs", "../../dame/index.md"),
        ("https://example.org/dame-rs/index.html", "../../dame/index.md"),
        ("https://example.org/dame-rs/img/app.png", "../../dame/img/app.png"),
        ("https://example.org/lev/", "../index.md"),
        ("https://example.org/", "../../index.md"),
        ("https://example.org/tclf/", "https://example.org/tclf/"),
        ("https://other.org/dame-rs/design/", "https://other.org/dame-rs/design/"),
        ("mailto:me@example.org", "mailto:me@example.org"),
        ("#anchor", "#anchor"),
        ("/absolute/", "/absolute/"),
        ("../index.md", "../index.md"),
    ],
)
def test_links_between_projects(merge: Callable[..., Assembly], link: str, expected: str) -> None:
    assembly = merge({"index.md": "# lev\n", "guide/page.md": f"# Page\n\nSee [it]({link}).\n"})

    assert staged(assembly, "lev/guide/page.md") == f"# Page\n\nSee [it]({expected}).\n"
    assert assembly.warnings == []


def test_unmatched_link_into_project_site_warns(merge: Callable[..., Assembly]) -> None:
    assembly = merge({"index.md": "[x](https://example.org/dame-rs/missing/)\n"})

    assert staged(assembly, "lev/index.md") == "[x](https://example.org/dame-rs/missing/)\n"
    (warning,) = assembly.warnings
    assert "matches no merged page" in warning


def test_umbrella_pages_are_rewritten(merge: Callable[..., Assembly]) -> None:
    assembly = merge({"index.md": "# lev\n"}, umbrella_index="[dame](https://example.org/dame-rs/design/)\n")

    assert staged(assembly, "index.md") == "[dame](dame/design.md)\n"


def test_code_is_left_untouched(merge: Callable[..., Assembly]) -> None:
    url = "https://example.org/dame-rs/"
    text = (
        f"`[a]({url})` and ``[b]({url})``\n\n"
        f"```md\n[c]({url})\n```\n\n"
        f"~~~~\n```\n[d]({url})\n```\n~~~~\n\n"
        f"!!! note\n\n    ```\n    [e]({url})\n    ```\n\n    [f]({url})\n"
    )

    assembly = merge({"index.md": text})

    assert staged(assembly, "lev/index.md") == text.replace(f"[f]({url})", "[f](../dame/index.md)")


def test_link_syntax_variants(merge: Callable[..., Assembly]) -> None:
    url = "https://example.org/dame-rs/design/"
    text = (
        f"[![logo]({url}logo.png)]({url})\n"
        f'[t]({url} "Title") [p](<{url}>)\n'
        f"[ref]: {url}#opening-book\n"
        f"[(paren)](https://en.wikipedia.org/wiki/Foo_(bar))\n"
    )

    assembly = merge({"index.md": text})

    assert staged(assembly, "lev/index.md") == (
        f"[![logo]({url}logo.png)](../dame/design.md)\n"
        '[t](../dame/design.md "Title") [p](<../dame/design.md>)\n'
        "[ref]: ../dame/design.md#opening-book\n"
        "[(paren)](https://en.wikipedia.org/wiki/Foo_(bar))\n"
    )
    (warning,) = assembly.warnings  # logo.png does not exist
    assert "logo.png matches no merged page" in warning


def test_links_leaving_the_docs_point_to_the_repository(merge: Callable[..., Assembly], tmp_path: Path) -> None:
    (tmp_path / "lev" / "src").mkdir(parents=True)
    (tmp_path / "lev" / "src" / "lib.rs").write_text("", encoding="utf-8")
    (tmp_path / "lev" / "LICENSE").write_text("", encoding="utf-8")

    assembly = merge({
        "index.md": "[l](../LICENSE#L3) [s](../src) [m](../missing.md) [i](sub/page.md)\n",
        "sub/page.md": "[r](../../src/lib.rs)\n",
    })

    assert staged(assembly, "lev/index.md") == (
        "[l](https://github.com/me/lev/blob/main/LICENSE#L3) [s](https://github.com/me/lev/tree/main/src) "
        "[m](../missing.md) [i](sub/page.md)\n"
    )
    assert staged(assembly, "lev/sub/page.md") == "[r](https://github.com/me/lev/blob/main/src/lib.rs)\n"


def test_gitlab_edit_uri(merge: Callable[..., Assembly], tmp_path: Path) -> None:
    (tmp_path / "lev").mkdir()
    (tmp_path / "lev" / "LICENSE").write_text("", encoding="utf-8")
    lev = {"repo_url": "https://gitlab.com/me/lev/", "edit_uri": "-/edit/dev/docs/"}

    assembly = merge({"index.md": "[l](../LICENSE)\n"}, lev=lev)

    assert staged(assembly, "lev/index.md") == "[l](https://gitlab.com/me/lev/-/blob/dev/LICENSE)\n"


def test_links_leaving_the_docs_without_repo_url_warn(merge: Callable[..., Assembly], tmp_path: Path) -> None:
    (tmp_path / "lev").mkdir()
    (tmp_path / "lev" / "LICENSE").write_text("", encoding="utf-8")

    assembly = merge({"index.md": "[l](../LICENSE)\n"}, lev={})

    assert staged(assembly, "lev/index.md") == "[l](../LICENSE)\n"
    (warning,) = assembly.warnings
    assert "set `repo_url` and `edit_uri`" in warning


def test_rewriting_never_touches_the_sources(merge: Callable[..., Assembly], tmp_path: Path) -> None:
    text = "[d](https://example.org/dame-rs/)\n"

    assembly = merge({"index.md": text})

    assert staged(assembly, "lev/index.md") == "[d](../dame/index.md)\n"
    assert (tmp_path / "lev" / "docs" / "index.md").read_text(encoding="utf-8") == text


def test_unterminated_angle_destination_is_ignored() -> None:
    assert rewrite_destinations("[a](<b.md\n", str.upper) == "[a](<b.md\n"


def test_build_validates_rewritten_links(make_project: Callable[..., Path]) -> None:
    make_project("lev", LEV, files={"index.md": "# lev\n\n[book](https://example.org/dame-rs/design/#opening-book)\n"})
    make_project("dame-rs", DAME, files={"index.md": "# dame\n", "design.md": "# Design\n\n## Opening book\n"})
    umbrella = make_project("umbrella", {"nav": [{"lev": "!include ../lev"}, {"dame": "!include ../dame-rs"}]})
    assert CliRunner().invoke(main, ["build", "--strict", "-f", str(umbrella)]).exit_code == 0

    make_project("lev", LEV, files={"index.md": "# lev\n\n[book](https://example.org/dame-rs/design/#closing-book)\n"})
    assert CliRunner().invoke(main, ["build", "--strict", "-f", str(umbrella)]).exit_code != 0

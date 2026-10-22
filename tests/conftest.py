from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
import tomli_w

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path


@pytest.fixture
def make_project(tmp_path: Path) -> Callable[..., Path]:
    """Create Zensical projects below ``tmp_path``.

    Returns:
        A factory that writes a project and returns the path to its ``zensical.toml``.
    """

    def factory(
        name: str,
        project: Mapping[str, Any] | None = None,
        *,
        files: Mapping[str, str] | None = None,
        zmerge: Mapping[str, Any] | None = None,
        docs_dir: str = "docs",
    ) -> Path:
        root = tmp_path / name
        (root / docs_dir).mkdir(parents=True, exist_ok=True)
        for path, content in (files or {"index.md": f"# {name}\n"}).items():
            file = root / docs_dir / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(content, encoding="utf-8")
        data: dict[str, Any] = {"project": {"site_name": name, **(project or {})}}
        if zmerge is not None:
            data["zmerge"] = zmerge
        config_file = root / "zensical.toml"
        config_file.write_text(tomli_w.dumps(data), encoding="utf-8")
        return config_file

    return factory

"""Load the umbrella configuration and the configurations of all included projects.

The umbrella site is a regular ``zensical.toml``. Child projects are pulled into its navigation with an
``!include`` entry, mirroring the syntax of the mkdocs-monorepo-plugin. Projects are configured with a
``zensical.toml`` or an ``mkdocs.yml``. A ``*include`` entry includes every project matching a glob pattern:

```toml
[project]
site_name = "My projects"
nav = [
  { Home = "index.md" },
  { lev = "!include ../lev/zensical.toml" },
  "*include ../packages/*/zensical.toml",
]

# Optional per-project overrides, keyed by the project id (the slug of the nav title).
[zmerge.projects.lev]
prefix = "levenshtein"
```
"""

from __future__ import annotations

import glob
import re
import tomllib
import unicodedata
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from zmerge.errors import ZmergeError
from zmerge.mkdocs import load_mkdocs_config
from zmerge.sources import GIT_PREFIX, REPOS_DIR, GitSource, fetch

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from pathlib import Path

INCLUDE = "!include"
WILDCARD_INCLUDE = "*include"
# Looked up in this order in included directories, like Zensical does.
CONFIG_FILE_NAMES = ("zensical.toml", "mkdocs.yml", "mkdocs.yaml")
_YAML_SUFFIXES = frozenset({".yml", ".yaml"})
STAGING_DIR = ".zmerge"

_PROJECT_OPTIONS = frozenset({"prefix"})
_SEGMENT = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._-]*")
# Zensical always excludes these directories from the docs, see `crates/zensical/src/config/inclusion.rs`.
_RESERVED_SEGMENTS = frozenset({"templates"})


@dataclass(frozen=True)
class Link:
    """A nav entry pointing to a page or an external URL.

    Attributes:
        title: Title shown in the nav, or ``None`` to use the page title.
        target: Path relative to the docs directory or an external URL.
    """

    title: str | None
    target: str


@dataclass(frozen=True)
class Section:
    """A nav section with nested entries.

    Attributes:
        title: Title of the section.
        items: Entries of the section.
    """

    title: str
    items: tuple[NavItem, ...]


@dataclass(frozen=True)
class Include:
    """A nav entry that includes the docs of another project.

    Attributes:
        title: Title of the section the project is mounted under.
        project: The included project.
    """

    title: str
    project: Project


NavItem = Link | Section | Include


@dataclass(frozen=True)
class Project:
    """A Zensical project whose docs are merged into the umbrella site.

    Attributes:
        id: Identifier of the project, used as key in ``[zmerge.projects]``.
        prefix: Path of the project's docs within the merged docs directory, e.g. ``lev`` or ``lev/core``.
        config_file: Path to the project's ``zensical.toml`` or ``mkdocs.yml``.
        config: The ``[project]`` table of the project's configuration.
        docs_dir: Absolute path to the project's docs directory.
        nav: Navigation of the project, or ``None`` if it has none.
    """

    id: str
    prefix: str
    config_file: Path
    config: Mapping[str, Any] = field(repr=False)
    docs_dir: Path
    nav: tuple[NavItem, ...] | None = field(repr=False)

    @property
    def root(self) -> Path:
        """Directory containing the project's configuration file."""
        return self.config_file.parent


@dataclass(frozen=True)
class Site:
    """The umbrella site that the projects are merged into.

    Attributes:
        config_file: Path to the umbrella ``zensical.toml``.
        config: The ``[project]`` table of the umbrella configuration.
        docs_dir: Absolute path to the umbrella docs directory.
        nav: Navigation of the umbrella site with the includes resolved.
    """

    config_file: Path
    config: Mapping[str, Any] = field(repr=False)
    docs_dir: Path
    nav: tuple[NavItem, ...] = field(repr=False)

    @property
    def root(self) -> Path:
        """Directory containing the umbrella configuration file."""
        return self.config_file.parent

    @property
    def projects(self) -> list[Project]:
        """All included projects, including nested ones, in nav order."""
        return list(_iter_projects(self.nav))


def slugify(title: str) -> str:
    """Turn a nav title into a URL-friendly project id.

    Args:
        title: The nav title.

    Returns:
        The slug.

    Examples:
        >>> slugify("API Reference")
        'api-reference'
        >>> slugify("Dämon Engine!")
        'damon-engine'
    """
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9._]+", "-", ascii_title.lower()).strip("-.")


def load_site(config_file: Path, *, update: bool = True) -> Site:
    """Load the umbrella configuration and all included projects.

    Args:
        config_file: Path to the umbrella ``zensical.toml``.
        update: Whether to fetch projects from git repositories that were fetched before again.

    Returns:
        The umbrella site with all includes resolved.

    Raises:
        ZmergeError: If a configuration is invalid.
    """
    config_file = config_file.resolve()
    config, zmerge = _read_config(config_file)
    if "nav" not in config:
        raise ZmergeError(f"{config_file}: the umbrella site needs a `nav` with at least one `{INCLUDE}` entry")
    loader = _Loader(repos_dir=config_file.parent / STAGING_DIR / REPOS_DIR, update=update)
    nav = loader.nav(config["nav"], config_file=config_file, zmerge=zmerge, parent_prefix="")
    if not loader.prefixes:
        raise ZmergeError(f"{config_file}: the umbrella `nav` contains no `{INCLUDE}` entry")
    return Site(config_file=config_file, config=config, docs_dir=_docs_dir(config_file, config), nav=nav)


def _iter_projects(nav: tuple[NavItem, ...] | None) -> Iterator[Project]:
    for item in nav or ():
        if isinstance(item, Include):
            yield item.project
            yield from _iter_projects(item.project.nav)
        elif isinstance(item, Section):
            yield from _iter_projects(item.items)


def _read_config(config_file: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if config_file.suffix in _YAML_SUFFIXES:
        config = load_mkdocs_config(config_file)
        zmerge = config.pop("zmerge", {})
        if "site_name" not in config:
            raise ZmergeError(f"{config_file}: `site_name` is required")
        return config, zmerge
    try:
        with config_file.open("rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        raise ZmergeError(f"{config_file}: configuration file not found") from None
    except tomllib.TOMLDecodeError as e:
        raise ZmergeError(f"{config_file}: invalid TOML: {e}") from None
    # Like Zensical, fall back to the top-level table if there is no `[project]` table.
    config = data.get("project", data)
    if "site_name" not in config:
        raise ZmergeError(f"{config_file}: `site_name` is required")
    return config, data.get("zmerge", {})


def _docs_dir(config_file: Path, config: Mapping[str, Any]) -> Path:
    docs_dir = (config_file.parent / config.get("docs_dir", "docs")).resolve()
    if not docs_dir.is_dir():
        raise ZmergeError(f"{config_file}: docs directory {docs_dir} does not exist")
    return docs_dir


def _directive(value: str) -> str | None:
    return next(iter(value.split(maxsplit=1)), None)


def _glob(pattern: str, *, config_file: Path) -> list[str]:
    if not pattern:
        raise ZmergeError(f"{config_file}: `{WILDCARD_INCLUDE}` needs a glob pattern")
    if pattern.startswith(GIT_PREFIX):
        raise ZmergeError(f"{config_file}: `{WILDCARD_INCLUDE}` doesn't support git repositories")
    # Unlike `Path.glob`, `glob.glob` supports absolute patterns.
    if not (matches := sorted(glob.glob(pattern, root_dir=config_file.parent))):  # ruff: ignore[glob]
        raise ZmergeError(f"{config_file}: `{WILDCARD_INCLUDE} {pattern}` matches no projects")
    return matches


def _validate_prefix(prefix: str, *, config_file: Path) -> str:
    segments = prefix.strip("/").split("/")
    for segment in segments:
        if not _SEGMENT.fullmatch(segment) or segment in _RESERVED_SEGMENTS:
            raise ZmergeError(
                f"{config_file}: invalid prefix {prefix!r}; use letters, digits, '.', '_' and '-', "
                f"don't start a segment with '.' and avoid reserved names {sorted(_RESERVED_SEGMENTS)}"
            )
    return "/".join(segments)


class _Loader:
    """Resolve includes recursively while detecting cycles and duplicate prefixes."""

    def __init__(self, *, repos_dir: Path, update: bool) -> None:
        self.prefixes: dict[str, Path] = {}
        self._ancestors: list[Path] = []
        self._repos_dir = repos_dir
        self._update = update

    def nav(
        self, raw: object, *, config_file: Path, zmerge: Mapping[str, Any], parent_prefix: str
    ) -> tuple[NavItem, ...]:
        if not isinstance(raw, list):
            raise ZmergeError(f"{config_file}: `nav` must be a list")
        overrides = zmerge.get("projects", {})
        self._ancestors.append(config_file)
        used: set[str] = set()
        items = tuple(
            self._items(raw, config_file=config_file, overrides=overrides, parent_prefix=parent_prefix, used=used)
        )
        self._ancestors.pop()
        if unknown := sorted(set(overrides) - used):
            raise ZmergeError(f"{config_file}: `[zmerge.projects]` lists unknown project(s) {unknown}")
        return items

    def _items(
        self,
        entries: list[object],
        *,
        config_file: Path,
        overrides: Mapping[str, Any],
        parent_prefix: str,
        used: set[str],
    ) -> Iterator[NavItem]:
        for entry in entries:
            if isinstance(entry, str) and _directive(entry) == WILDCARD_INCLUDE:
                for path in _glob(entry.removeprefix(WILDCARD_INCLUDE).strip(), config_file=config_file):
                    include_file = self._include_file(path, config_file=config_file)
                    yield self._include(
                        include_file,
                        None,
                        config_file=config_file,
                        overrides=overrides,
                        parent_prefix=parent_prefix,
                        used=used,
                    )
            else:
                yield self._item(
                    entry, config_file=config_file, overrides=overrides, parent_prefix=parent_prefix, used=used
                )

    def _item(
        self,
        entry: object,
        *,
        config_file: Path,
        overrides: Mapping[str, Any],
        parent_prefix: str,
        used: set[str],
    ) -> NavItem:
        if isinstance(entry, str):
            title, value = None, entry
        elif isinstance(entry, dict) and len(entry) == 1:
            ((title, value),) = entry.items()
        else:
            raise ZmergeError(f"{config_file}: invalid nav entry {entry!r}")

        if isinstance(value, list):
            if title is None:  # pragma: no cover - a bare list is rejected by the branches above
                raise ZmergeError(f"{config_file}: invalid nav entry {entry!r}")
            children = tuple(
                self._items(value, config_file=config_file, overrides=overrides, parent_prefix=parent_prefix, used=used)
            )
            return Section(title=title, items=children)
        if not isinstance(value, str):
            raise ZmergeError(f"{config_file}: invalid nav entry {entry!r}")
        directive = _directive(value)
        if directive == WILDCARD_INCLUDE:
            raise ZmergeError(f"{config_file}: `{WILDCARD_INCLUDE}` can't have a title, put it in a section instead")
        if directive != INCLUDE:
            return Link(title=title, target=value)

        include_file = self._include_file(value.removeprefix(INCLUDE).strip(), config_file=config_file)
        return self._include(
            include_file, title, config_file=config_file, overrides=overrides, parent_prefix=parent_prefix, used=used
        )

    def _include(
        self,
        include_file: Path,
        title: str | None,
        *,
        config_file: Path,
        overrides: Mapping[str, Any],
        parent_prefix: str,
        used: set[str],
    ) -> Include:
        child_config, child_zmerge = _read_config(include_file)
        title = title or str(child_config["site_name"])
        project_id = slugify(title)
        if not project_id:
            raise ZmergeError(f"{config_file}: cannot derive a project id from nav title {title!r}")
        if project_id in used:
            raise ZmergeError(f"{config_file}: duplicate project id {project_id!r}; give the includes distinct titles")
        used.add(project_id)

        options = overrides.get(project_id, {})
        if unknown := sorted(set(options) - _PROJECT_OPTIONS):
            raise ZmergeError(f"{config_file}: unknown option(s) {unknown} in `[zmerge.projects.{project_id}]`")
        own_prefix = _validate_prefix(str(options.get("prefix", project_id)), config_file=config_file)
        prefix = f"{parent_prefix}/{own_prefix}" if parent_prefix else own_prefix
        if prefix in self.prefixes:
            raise ZmergeError(
                f"{config_file}: prefix {prefix!r} of {include_file} is already used by {self.prefixes[prefix]}"
            )
        self.prefixes[prefix] = include_file

        nav = None
        if "nav" in child_config:
            nav = self.nav(child_config["nav"], config_file=include_file, zmerge=child_zmerge, parent_prefix=prefix)
        project = Project(
            id=project_id,
            prefix=prefix,
            config_file=include_file,
            config=child_config,
            docs_dir=_docs_dir(include_file, child_config),
            nav=nav,
        )
        return Include(title=title, project=project)

    def _include_file(self, path: str, *, config_file: Path) -> Path:
        if not path:
            raise ZmergeError(f"{config_file}: `{INCLUDE}` needs a path")
        if path.startswith(GIT_PREFIX):
            try:
                include_file = fetch(GitSource.parse(path), self._repos_dir, update=self._update).resolve()
            except ZmergeError as e:
                raise ZmergeError(f"{config_file}: {e}") from None
        else:
            include_file = (config_file.parent / path).resolve()
        if include_file.is_dir():
            candidates = [include_file / name for name in CONFIG_FILE_NAMES]
            include_file = next((c for c in candidates if c.is_file()), candidates[0])
        if include_file.suffix != ".toml" and include_file.suffix not in _YAML_SUFFIXES:
            raise ZmergeError(f"{config_file}: `{INCLUDE} {path}` must point to a `zensical.toml` or `mkdocs.yml`")
        if include_file in self._ancestors:
            chain = " -> ".join(str(p) for p in [*self._ancestors, include_file])
            raise ZmergeError(f"circular `{INCLUDE}`: {chain}")
        return include_file

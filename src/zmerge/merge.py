"""Merge the configurations of the included projects into the umbrella configuration.

The umbrella configuration owns everything that affects the site as a whole (``site_name``, ``theme``, ``extra``, ...).
From the projects, zmerge takes what their pages need to render:

- ``markdown_extensions`` and ``plugins`` are combined. The umbrella wins on conflicting options.
- ``mkdocstrings`` handler ``paths`` are rebased onto the umbrella, so API docs are still found. Handler options that
  differ between projects are returned per project, to be written into the projects' ``:::`` directives.
- ``pymdownx.snippets`` base paths of all projects are combined.
- Local ``extra_css`` and ``extra_javascript`` files are moved below the project prefix.
- ``exclude_docs``, ``draft_docs`` and ``not_in_nav`` patterns are anchored at the project prefix.
"""

from __future__ import annotations

import copy
import dataclasses
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

from zmerge.config import ZmergeError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from zmerge.config import Project, Site

_URL = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|//)")
_PATTERN_KEYS = ("exclude_docs", "draft_docs", "not_in_nav")
_ASSET_KEYS = ("extra_css", "extra_javascript")
# Python Markdown extension namespaces Zensical lets you write as nested tables, see `_convert_markdown_extensions`.
_NAMESPACES = {"pymdownx": "blocks", "zensical": "extensions"}
SNIPPETS = "pymdownx.snippets"
MDX_INCLUDE = "mdx_include"
INCLUDE_VARIANTS = "markdown_include_variants"
_MISSING = object()


@dataclass
class MergedConfig:
    """The merged configuration.

    Attributes:
        config: The merged ``[project]`` table without ``nav`` and ``docs_dir``.
        warnings: Settings that could not be merged.
        directive_options: mkdocstrings handler options per project prefix and handler, which differ from the merged
            handler options and must be set on the project's ``:::`` directives.
        default_handler: The default mkdocstrings handler.
    """

    config: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    directive_options: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)
    default_handler: str = "python"


def merge_config(site: Site) -> MergedConfig:
    """Merge the configurations of all projects into the umbrella configuration.

    Args:
        site: The umbrella site.

    Returns:
        The merged configuration.
    """
    config = copy.deepcopy(dict(site.config))
    merged = MergedConfig(config=config)
    warnings = merged.warnings
    projects = site.projects

    extensions = _merge_extensions(site, projects, warnings)
    if extensions is not None:
        config["markdown_extensions"] = extensions

    plugins = _merge_plugins(site, projects, warnings)
    if plugins is not None:
        config["plugins"] = plugins
        if "mkdocstrings" in plugins:
            merged.default_handler = plugins["mkdocstrings"].get("default_handler", "python")
            merged.directive_options = _directive_options(plugins["mkdocstrings"], projects, warnings)

    for key in _ASSET_KEYS:
        assets = _merge_assets(site, projects, key)
        if assets:
            config[key] = assets

    for key in _PATTERN_KEYS:
        patterns = [config[key].rstrip("\n")] if config.get(key) else []
        patterns += [_prefix_patterns(p.config[key], p.prefix) for p in projects if p.config.get(key)]
        if patterns:
            config[key] = "\n".join(patterns) + "\n"

    config.pop("nav", None)
    return merged


def normalize_extensions(value: object, *, config_file: Path) -> dict[str, dict[str, Any]]:
    """Normalize ``markdown_extensions`` into a mapping from extension name to options.

    Args:
        value: The ``markdown_extensions`` setting, either a list or a (nested) mapping.
        config_file: The configuration the setting comes from, for error messages.

    Returns:
        The extensions in their declared order.

    Raises:
        ZmergeError: If the setting is malformed.

    Examples:
        >>> from pathlib import Path
        >>> normalize_extensions({"toc": {"permalink": True}, "pymdownx": {"highlight": {}}}, config_file=Path("z"))
        {'toc': {'permalink': True}, 'pymdownx.highlight': {}}
        >>> normalize_extensions(["admonition", {"toc": {"permalink": True}}], config_file=Path("z"))
        {'admonition': {}, 'toc': {'permalink': True}}
    """
    entries: list[tuple[str, Any]]
    if isinstance(value, list):
        entries = []
        for item in value:
            if isinstance(item, str):
                entries.append((item, {}))
            elif isinstance(item, dict) and len(item) == 1:
                entries.extend(item.items())
            else:
                raise ZmergeError(f"{config_file}: invalid markdown extension {item!r}")
    elif isinstance(value, dict):
        entries = list(value.items())
    else:
        raise ZmergeError(f"{config_file}: `markdown_extensions` must be a list or a table")

    extensions: dict[str, dict[str, Any]] = {}
    for name, options in entries:
        if name in _NAMESPACES and isinstance(options, dict):
            nested = _NAMESPACES[name]
            for ext, ext_options in options.items():
                if ext == nested and isinstance(ext_options, dict):
                    for sub, sub_options in ext_options.items():
                        extensions[f"{name}.{ext}.{sub}"] = sub_options or {}
                else:
                    extensions[f"{name}.{ext}"] = ext_options or {}
        else:
            extensions[name] = options or {}
    return extensions


def _merge_extensions(site: Site, projects: list[Project], warnings: list[str]) -> dict[str, Any] | None:
    sources = [(site.config_file, site.config), *((p.config_file, p.config) for p in projects)]
    if not any("markdown_extensions" in config for _, config in sources):
        return None  # Everyone uses Zensical's defaults.

    merged: dict[str, dict[str, Any]] = {}
    origin: dict[str, Path] = {}
    base_paths: list[str] = []
    for config_file, config in sources:
        if "markdown_extensions" not in config:
            warnings.append(
                f"{config_file}: relies on Zensical's default markdown extensions, which are replaced by the merged "
                "`markdown_extensions`; define them explicitly"
            )
            continue
        for name, options in normalize_extensions(config["markdown_extensions"], config_file=config_file).items():
            if name == SNIPPETS:
                options = dict(options)
                for path in snippet_base_paths(options, root=config_file.parent):
                    rebased = _rebase(path, site.root)
                    if rebased not in base_paths:
                        base_paths.append(rebased)
                options.pop("base_path", None)
            elif name == MDX_INCLUDE:
                # Includes are resolved per project, see `zmerge.directives.rewrite_includes`.
                options = {key: value for key, value in options.items() if key != "base_path"}
            if name not in merged:
                merged[name] = dict(options)
                origin[name] = config_file
            elif conflicts := _merge_options(merged[name], options):
                warnings.append(
                    f"{config_file}: options {conflicts} of markdown extension {name!r} differ from {origin[name]}; "
                    f"using {_subset(merged[name], conflicts)!r}"
                )
    if SNIPPETS in merged:
        merged[SNIPPETS]["base_path"] = base_paths
    return merged


def snippet_base_paths(options: Mapping[str, Any], *, root: Path) -> list[Path]:
    """Return the absolute base paths of ``pymdownx.snippets``, assuming Zensical runs in ``root``.

    Args:
        options: Options of the extension.
        root: Directory of the configuration file.

    Returns:
        The base paths; ``root`` if none are set.
    """
    base_path = options.get("base_path", ["."])
    if isinstance(base_path, str):
        base_path = [base_path]
    return [(root / path).resolve() for path in base_path]


def _normalize_plugins(value: object, *, config_file: Path) -> dict[str, dict[str, Any]]:
    if isinstance(value, dict):
        return {name: options or {} for name, options in value.items()}
    if isinstance(value, list):
        plugins: dict[str, dict[str, Any]] = {}
        for item in value:
            if isinstance(item, str):
                plugins[item] = {}
            elif isinstance(item, dict) and len(item) == 1:
                ((name, options),) = item.items()
                plugins[name] = options or {}
            else:
                raise ZmergeError(f"{config_file}: invalid plugin {item!r}")
        return plugins
    raise ZmergeError(f"{config_file}: `plugins` must be a list or a table")


def _merge_plugins(site: Site, projects: list[Project], warnings: list[str]) -> dict[str, Any] | None:
    if "plugins" not in site.config and not any("plugins" in p.config for p in projects):
        return None

    merged = _normalize_plugins(copy.deepcopy(site.config.get("plugins", {})), config_file=site.config_file)
    if "mkdocstrings" in merged:
        _rebase_mkdocstrings(merged["mkdocstrings"], root=site.root, umbrella_root=site.root)
    for project in projects:
        plugins = _normalize_plugins(copy.deepcopy(project.config.get("plugins", {})), config_file=project.config_file)
        for name, options in plugins.items():
            if name == "mkdocstrings":
                _rebase_mkdocstrings(options, root=project.root, umbrella_root=site.root)
                _merge_mkdocstrings(merged.setdefault(name, {}), options, project, warnings)
            elif name not in merged:
                merged[name] = options
            elif conflicts := _merge_options(merged[name], options):
                warnings.append(
                    f"{project.config_file}: options {conflicts} of plugin {name!r} differ from the merged site; "
                    f"using {_subset(merged[name], conflicts)!r}"
                )
    return merged


def _merge_options(target: dict[str, Any], options: Mapping[str, Any]) -> list[str]:
    """Add the options missing in ``target`` and return the names of options with conflicting values."""
    conflicts = []
    for key, value in options.items():
        if key not in target:
            target[key] = value
        elif target[key] != value:
            conflicts.append(key)
    return conflicts


def _subset(options: Mapping[str, Any], keys: list[str]) -> dict[str, Any]:
    return {key: options[key] for key in keys}


def _rebase_mkdocstrings(options: dict[str, Any], *, root: Path, umbrella_root: Path) -> None:
    """Make handler ``paths`` relative to the umbrella root. Like mkdocstrings, an unset ``paths`` means ``["."]``."""
    for handler in options.get("handlers", {}).values():
        handler["paths"] = [_rebase(root / path, umbrella_root) for path in handler.get("paths", ["."])]


def _merge_mkdocstrings(
    merged: dict[str, Any], options: Mapping[str, Any], project: Project, warnings: list[str]
) -> None:
    for key, value in options.items():
        if key != "handlers":
            if key not in merged:
                merged[key] = value
            elif merged[key] != value:
                warnings.append(
                    f"{project.config_file}: mkdocstrings option {key!r} differs from the merged site; "
                    f"using {merged[key]!r}"
                )
            continue
        handlers = merged.setdefault("handlers", {})
        for name, handler in value.items():
            target = handlers.setdefault(name, {})
            for path in handler.get("paths", []):
                if path not in target.setdefault("paths", []):
                    target["paths"].append(path)
            for option, option_value in handler.items():
                if option == "paths":
                    continue
                if option == "options":
                    # Differences are resolved per project, see `_directive_options`.
                    for key, key_value in option_value.items():
                        target.setdefault("options", {}).setdefault(key, key_value)
                    continue
                if option not in target:
                    target[option] = option_value
                elif target[option] != option_value:
                    warnings.append(
                        f"{project.config_file}: mkdocstrings `handlers.{name}.{option}` differs from the merged site; "
                        f"using {target[option]!r}"
                    )


def _directive_options(
    mkdocstrings: Mapping[str, Any], projects: list[Project], warnings: list[str]
) -> dict[str, dict[str, dict[str, Any]]]:
    """Compute the handler options each project needs on its directives to render as when built on its own."""
    handlers = mkdocstrings.get("handlers", {})
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for project in projects:
        plugins = _normalize_plugins(project.config.get("plugins", {}), config_file=project.config_file)
        if "mkdocstrings" not in plugins:
            continue
        own_handlers = plugins["mkdocstrings"].get("handlers", {})
        for name, handler in handlers.items():
            merged_options = handler.get("options", {})
            own = own_handlers.get(name, {}).get("options", {})
            overrides = {key: value for key, value in own.items() if merged_options.get(key, _MISSING) != value}
            for key in merged_options.keys() - own.keys():
                default = _handler_default(name, key)
                if default is _MISSING:
                    warnings.append(
                        f"{project.config_file}: cannot determine the default of mkdocstrings option "
                        f"`handlers.{name}.options.{key}`; using {merged_options[key]!r}"
                    )
                else:
                    overrides[key] = default
            if overrides:
                result.setdefault(project.prefix, {})[name] = overrides
    return result


def _handler_default(handler: str, key: str) -> object:
    """Return the default of a handler option, or ``_MISSING`` if it is unknown."""
    if handler != "python":
        return _MISSING
    try:
        from mkdocstrings_handlers.python import PythonOptions
    except ImportError:
        return _MISSING
    names = {f.name for f in dataclasses.fields(PythonOptions)}
    value = getattr(PythonOptions(), key, _MISSING) if key in names else _MISSING
    return value if _is_plain(value) else _MISSING


def _is_plain(value: object) -> bool:
    if value is None or isinstance(value, str | int | float | bool):
        return True
    if isinstance(value, list | tuple):
        return all(_is_plain(v) for v in value)
    if isinstance(value, dict):
        return all(isinstance(k, str) and _is_plain(v) for k, v in value.items())
    return False


def _rebase(path: Path, root: Path) -> str:
    """Express ``path`` relative to ``root`` if it is inside of it, otherwise as an absolute path."""
    path = path.resolve()
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else path.as_posix()


def _merge_assets(site: Site, projects: list[Project], key: str) -> list[Any]:
    assets: list[Any] = []
    seen: set[str] = set()
    sources = [("", site.config), *((p.prefix, p.config) for p in projects)]
    for prefix, config in sources:
        for asset in config.get(key, []):
            entry = copy.deepcopy(asset)
            path = entry["path"] if isinstance(entry, dict) else entry
            if prefix and not _URL.match(path) and not path.startswith("/"):
                path = f"{prefix}/{PurePosixPath(path).as_posix().removeprefix('./')}"
            if path in seen:
                continue
            seen.add(path)
            if isinstance(entry, dict):
                entry["path"] = path
            else:
                entry = path
            assets.append(entry)
    return assets


def _prefix_patterns(patterns: str, prefix: str) -> str:
    r"""Anchor gitignore-style patterns at ``prefix``.

    Returns:
        The anchored patterns.

    Examples:
        >>> print(_prefix_patterns("drafts/\n/private.md\nsub/*.md\n!keep.md\n# comment\n", "lev"))
        /lev/**/drafts/
        /lev/private.md
        /lev/sub/*.md
        !/lev/**/keep.md
        # comment
    """
    lines = []
    for line in patterns.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            lines.append(line)
            continue
        negate = "!" if stripped.startswith("!") else ""
        pattern = stripped.removeprefix("!")
        # As in gitignore, a pattern containing a slash (other than a trailing one) is relative to the root.
        anchored = "/" in pattern.rstrip("/")
        pattern = pattern.lstrip("/")
        lines.append(f"{negate}/{prefix}/{pattern}" if anchored else f"{negate}/{prefix}/**/{pattern}")
    return "\n".join(lines)

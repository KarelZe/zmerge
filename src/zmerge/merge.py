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

from zmerge.config import Section, ZmergeError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from zmerge.config import NavItem, Project, Site

_URL = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|//)")
_PATTERN_KEYS = ("exclude_docs", "draft_docs", "not_in_nav")
_ASSET_KEYS = ("extra_css", "extra_javascript")
# Libraries a site must load only once, by the job they do. Assets are recognized by name and, if remote, versioned
# like `mathjax@3`, `katex@0.16.9` (unpkg, jsdelivr) or `KaTeX/0.16.9` (cdnjs).
_LIBRARIES = {"mathjax": ("MathJax", "math renderer"), "katex": ("KaTeX", "math renderer")}
_LIBRARY = re.compile(r"(mathjax|katex)(?:[@/-]v?(\d+(?:\.\d+)*))?", re.IGNORECASE)
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
    _check_libraries(site, projects, warnings)

    for key in _PATTERN_KEYS:
        patterns = [config[key].rstrip("\n")] if config.get(key) else []
        patterns += [_prefix_patterns(p.config[key], p.prefix) for p in projects if p.config.get(key)]
        if patterns:
            config[key] = "\n".join(patterns) + "\n"

    # Untitled sections show the title of their index page only with `navigation.indexes`, which the umbrella owns.
    theme = config.get("theme")
    if "navigation.indexes" not in (theme.get("features", []) if isinstance(theme, dict) else []):
        warnings.extend(
            f"{p.config_file}: nav has untitled sections; add `navigation.indexes` to the umbrella's theme features "
            "to title them like their index page"
            for p in projects
            if _has_untitled_section(p.nav)
        )

    config.pop("nav", None)
    return merged


def _has_untitled_section(nav: tuple[NavItem, ...] | None) -> bool:
    return any(
        isinstance(item, Section) and (not item.title or _has_untitled_section(item.items)) for item in nav or ()
    )


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

    umbrella: dict[str, dict[str, Any]] = {}
    entries: dict[str, list[tuple[Path, Mapping[str, Any]]]] = {}
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
            if config_file == site.config_file:
                umbrella[name] = dict(options)
            entries.setdefault(name, [])
            if config_file != site.config_file:
                entries[name].append((config_file, options))
    merged = {
        name: _combine_options("markdown extension", name, umbrella.get(name), project_options, warnings)
        for name, project_options in entries.items()
    }
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

    umbrella = _normalize_plugins(copy.deepcopy(site.config.get("plugins", {})), config_file=site.config_file)
    merged: dict[str, Any] = {}
    entries: dict[str, list[tuple[Path, Mapping[str, Any]]]] = {name: [] for name in umbrella}
    if "mkdocstrings" in umbrella:
        _rebase_mkdocstrings(umbrella["mkdocstrings"], root=site.root, umbrella_root=site.root)
        merged["mkdocstrings"] = umbrella["mkdocstrings"]
    for project in projects:
        plugins = _normalize_plugins(copy.deepcopy(project.config.get("plugins", {})), config_file=project.config_file)
        for name, options in plugins.items():
            if name == "mkdocstrings":
                _rebase_mkdocstrings(options, root=project.root, umbrella_root=site.root)
                _merge_mkdocstrings(merged.setdefault(name, {}), options, project, warnings)
            entries.setdefault(name, []).append((project.config_file, options))
    return {
        name: merged[name]
        if name == "mkdocstrings"
        else _combine_options("plugin", name, umbrella.get(name), project_options, warnings)
        for name, project_options in entries.items()
    }


def _combine_options(
    kind: str,
    name: str,
    umbrella: Mapping[str, Any] | None,
    entries: list[tuple[Path, Mapping[str, Any]]],
    warnings: list[str],
) -> dict[str, Any]:
    """Combine the options of a markdown extension or plugin, which apply to all pages of the merged site.

    Options of the umbrella project override those of the projects. Every other option a project sets applies to all
    projects, so zmerge warns if projects set it differently or only some set it.

    Args:
        kind: What is combined, for warnings.
        name: Name of the extension or plugin.
        umbrella: Options of the umbrella project, or ``None`` if it doesn't use the extension or plugin.
        entries: Configuration file and options of every project that uses the extension or plugin.
        warnings: Receives the warnings.

    Returns:
        The combined options.
    """
    combined = dict(umbrella or {})
    overridden = set(combined)
    origin: dict[str, Path] = {}
    for config_file, options in entries:
        conflicts = []
        for key, value in options.items():
            if key in overridden:
                continue
            if key not in combined:
                combined[key] = value
                origin[key] = config_file
            elif combined[key] != value:
                conflicts.append(key)
        if conflicts:
            warnings.append(
                f"{config_file}: options {conflicts} of {kind} {name!r} differ from other projects; "
                f"using {_subset(combined, conflicts)!r}. Set them in the umbrella project to override them"
            )
    for config_file, options in entries:
        if missing := [key for key in origin if key not in options]:
            warnings.append(
                f"{config_file}: doesn't set options {missing} of {kind} {name!r}, which other projects set and which "
                f"apply to all pages; using {_subset(combined, missing)!r}. Set them in the umbrella project to "
                "override them"
            )
    return combined


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
    options = dict(options)
    handlers = options.pop("handlers", {})
    for key in _merge_options(merged, options):
        warnings.append(
            f"{project.config_file}: mkdocstrings option {key!r} differs from the merged site; using {merged[key]!r}"
        )
    for name, handler in handlers.items():
        handler = dict(handler)
        target = merged.setdefault("handlers", {}).setdefault(name, {})
        # Keep the order of the paths and drop duplicates.
        target["paths"] = list(dict.fromkeys([*target.get("paths", []), *handler.pop("paths", [])]))
        # Differences are resolved per project, see `_directive_options`.
        if handler_options := handler.pop("options", None):
            target["options"] = handler_options | target.get("options", {})
        for option in _merge_options(target, handler):
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
    value = _config_value(getattr(PythonOptions(), key)) if key in names else _MISSING
    return value if _is_plain(value) else _MISSING


def _config_value(value: object) -> object:
    """Turn a parsed handler option back into the form it takes in the configuration.

    Args:
        value: The parsed option, e.g. a dataclass or compiled filters.

    Returns:
        The option as it is written in the configuration.

    Examples:
        >>> import re
        >>> _config_value([(re.compile("^_[^_]"), True), (re.compile("^__init__$"), False)])
        ['!^_[^_]', '^__init__$']
    """
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: _config_value(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], re.Pattern):  # a parsed filter
        pattern, exclude = value
        return f"!{pattern.pattern}" if exclude else pattern.pattern
    if isinstance(value, list | tuple):
        return [_config_value(v) for v in value]
    return value


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


def _check_libraries(site: Site, projects: list[Project], warnings: list[str]) -> None:
    """Warn about libraries in ``extra_css`` and ``extra_javascript`` that conflict once loaded on every page.

    Assets are only deduplicated by their exact path. So projects using different math renderers, or the same one in
    different versions or from different CDNs, load all of them.
    """
    users: dict[str, list[Path]] = {}  # library -> configuration files using it
    urls: dict[str, dict[str, list[Path]]] = {}  # library -> remote URL -> configuration files loading it
    sources = [(site.config_file, site.config), *((p.config_file, p.config) for p in projects)]
    for config_file, config in sources:
        for key in _ASSET_KEYS:
            for asset in config.get(key, []):
                path = asset["path"] if isinstance(asset, dict) else asset
                if not isinstance(path, str) or not (match := _LIBRARY.search(path)):
                    continue
                library = _LIBRARIES[match[1].lower()][0]
                _add(users.setdefault(library, []), config_file)
                if _URL.match(path):
                    _add(urls.setdefault(library, {}).setdefault(path, []), config_file)

    groups: dict[str, list[str]] = {}
    for library, group in _LIBRARIES.values():
        if library in users and library not in groups.setdefault(group, []):
            groups[group].append(library)
    for group, libraries in groups.items():
        if len(libraries) > 1:
            used = "; ".join(f"{library} in {_join(users[library])}" for library in libraries)
            warnings.append(
                f"conflicting {group}s: {used}; all are loaded on every page, use the same {group} in all projects"
            )

    for library, loaded in urls.items():
        versions: dict[str, list[Path]] = {}
        names: dict[str, list[str]] = {}
        for url, files in loaded.items():
            match = _LIBRARY.search(url)
            version = match[2] if match and match[2] else "unversioned"
            for file in files:
                _add(versions.setdefault(version, []), file)
            names.setdefault(PurePosixPath(url.split("?", 1)[0].split("#", 1)[0]).name, []).append(url)
        if len(versions) > 1:
            listed = ", ".join(f"{version} ({_join(files)})" for version, files in versions.items())
            warnings.append(f"{library} is loaded in several versions: {listed}; use the same version in all projects")
            continue
        for name, duplicates in names.items():
            if len(duplicates) > 1:
                listed = ", ".join(f"{url} ({_join(loaded[url])})" for url in duplicates)
                warnings.append(
                    f"{library} {name!r} is loaded from several URLs: {listed}; use the same URL in all projects"
                )


def _add(items: list[Any], item: object) -> None:
    if item not in items:
        items.append(item)


def _join(files: list[Path]) -> str:
    return ", ".join(str(file) for file in files)


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

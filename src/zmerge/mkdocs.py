"""Load ``mkdocs.yml`` configurations like Zensical does.

Zensical builds projects configured with an ``mkdocs.yml``. zmerge reads them with the same extensions to YAML:

- ``INHERIT`` merges the configuration into a parent configuration.
- ``!ENV`` reads environment variables, e.g. ``!ENV [NAME, fallback]``.
- Python tags like ``!!python/name:pymdownx.superfences.fence_code_format`` become the dotted names
  (``!!python/object/apply`` becomes ``{object = ..., kwds = ...}``), which Zensical resolves in a ``zensical.toml``.
- ``material.extensions`` and ``materialx`` are renamed to ``zensical.extensions``.
- ``!include`` keeps the include for zmerge, as in the mkdocs-monorepo-plugin.

``null`` can't be written to TOML: extensions and plugins without options become empty tables, other ``null`` values
are dropped, which leaves the setting at its default.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import yaml
from yaml.constructor import ConstructorError

from zmerge.errors import ZmergeError

if TYPE_CHECKING:
    from pathlib import Path

_PYTHON_TAG = "tag:yaml.org,2002:python/"
_ENABLE_KEYS = ("markdown_extensions", "plugins")


class _Loader(yaml.SafeLoader):
    """A safe loader with the tags Zensical supports in ``mkdocs.yml``."""


def _construct_env(loader: _Loader, node: yaml.Node) -> Any:
    """Resolve ``!ENV NAME`` and ``!ENV [NAME, ..., fallback]`` like Zensical."""
    default = None
    if isinstance(node, yaml.ScalarNode):
        names = [loader.construct_scalar(node)]
    elif isinstance(node, yaml.SequenceNode):
        children = node.value
        if len(children) > 1:
            default = loader.construct_object(children[-1])
            children = children[:-1]
        names = [loader.construct_scalar(child) for child in children]
    else:
        raise ConstructorError(context="expected a scalar or sequence node", context_mark=node.start_mark)
    for name in names:
        if name in os.environ:
            value = os.environ[name]
            tag = loader.resolve(yaml.ScalarNode, value, (True, False))
            return loader.construct_object(yaml.ScalarNode(tag, value))
    return default


def _construct_include(loader: _Loader, node: yaml.Node) -> str:
    return f"!include {loader.construct_scalar(node)}".strip()


def _construct_python(loader: _Loader, suffix: str, node: yaml.Node) -> Any:
    kind, _, name = suffix.partition(":")
    if kind == "name":
        return name
    if kind == "object/apply" and isinstance(node, yaml.MappingNode):
        mapping = loader.construct_mapping(node, deep=True)
        if set(mapping) <= {"kwds"}:
            return {"object": name, "kwds": mapping.get("kwds", {})}
    raise ConstructorError(
        problem=f"unsupported tag !!python/{suffix}; use !!python/name or !!python/object/apply with kwds",
        problem_mark=node.start_mark,
    )


_Loader.add_constructor("!ENV", _construct_env)
_Loader.add_constructor("!include", _construct_include)
_Loader.add_multi_constructor(_PYTHON_TAG, _construct_python)


def load_mkdocs_config(config_file: Path) -> dict[str, Any]:
    """Load an ``mkdocs.yml`` and the configurations it inherits from.

    Args:
        config_file: Path to the ``mkdocs.yml``.

    Returns:
        The configuration, with values that can be written to TOML.

    Raises:
        ZmergeError: If the configuration can't be read.
    """
    return _without_nulls(_load(config_file, ancestors=[]))


def _load(config_file: Path, *, ancestors: list[Path]) -> dict[str, Any]:
    if config_file in ancestors:
        raise ZmergeError(f"{ancestors[-1]}: circular `INHERIT` of {config_file}")
    try:
        text = config_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ZmergeError(f"{config_file}: configuration file not found") from None
    text = text.replace("material.extensions", "zensical.extensions").replace("materialx", "zensical.extensions")
    try:
        config = yaml.load(text, Loader=_Loader)
    except yaml.YAMLError as e:
        raise ZmergeError(f"{config_file}: invalid YAML: {e}") from None
    if config is None:
        return {}
    if not isinstance(config, dict):
        raise ZmergeError(f"{config_file}: the configuration must be a mapping")
    if "INHERIT" in config:
        parent_file = (config_file.parent / str(config.pop("INHERIT"))).resolve()
        if not parent_file.is_file():
            raise ZmergeError(f"{config_file}: inherited configuration {parent_file} doesn't exist")
        config = deep_merge(_load(parent_file, ancestors=[*ancestors, config_file]), config)
    return config


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge ``override`` into ``base`` like ``INHERIT``: mappings are merged, lists appended, other values replaced.

    Args:
        base: The inherited configuration. Modified in place.
        override: The configuration that inherits.

    Returns:
        The merged configuration.

    Examples:
        >>> deep_merge({"a": {"b": 1, "c": [1]}, "d": 1}, {"a": {"c": [2]}, "d": 2})
        {'a': {'b': 1, 'c': [1, 2]}, 'd': 2}
    """
    for key, value in override.items():
        if isinstance(base.get(key), dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        elif isinstance(base.get(key), list) and isinstance(value, list):
            base[key] += value
        else:
            base[key] = value
    return base


def _without_nulls(config: dict[str, Any]) -> dict[str, Any]:
    """Turn extensions and plugins without options into empty tables and drop other ``null`` values.

    Args:
        config: The loaded configuration.

    Returns:
        The configuration without ``null`` values.

    Examples:
        >>> _without_nulls({"markdown_extensions": [{"abbr": None}, "toc"], "plugins": {"search": None}, "a": None})
        {'markdown_extensions': [{'abbr': {}}, 'toc'], 'plugins': {'search': {}}}
    """
    for key in _ENABLE_KEYS:
        value = config.get(key)
        if isinstance(value, dict):
            config[key] = {name: {} if options is None else options for name, options in value.items()}
        elif isinstance(value, list):
            config[key] = [
                {name: {} if options is None else options for name, options in item.items()}
                if isinstance(item, dict)
                else item
                for item in value
            ]
    return _drop_nulls(config)


def _drop_nulls(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _drop_nulls(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [_drop_nulls(item) for item in value if item is not None]
    return value

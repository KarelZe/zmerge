"""Rewrite directives in project pages that depend on the project's configuration.

- **mkdocstrings.** There is only one set of handler options per build. If a project's handler options differ from
  the merged ones, they are written into every ``:::`` directive of the project, where they take precedence over the
  handler options.
- **Snippets.** ``pymdownx.snippets`` resolves files relative to its base paths. Snippets of a project are resolved
  against the project's base paths and replaced by absolute paths, so a ``README.md`` snippet includes the README of
  the right project.
- **Includes.** ``mdx_include`` (``{! file !}``) resolves files relative to its ``base_path`` and
  ``markdown_include_variants`` (``{* file *}``) relative to the working directory. Like snippets, includes of a
  project are resolved against the project and replaced by absolute paths.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import yaml

from zmerge.links import outside_fences
from zmerge.merge import INCLUDE_VARIANTS, MDX_INCLUDE, SNIPPETS, normalize_extensions, snippet_base_paths

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from zmerge.assemble import Source
    from zmerge.config import Project, Site
    from zmerge.merge import MergedConfig

_DIRECTIVE = re.compile(r"^(?P<indent>[ \t]*)(?:#{1,6} *)?::: ?(?P<identifier>\S.*?) *$")
# The patterns below are taken from `pymdownx.snippets.SnippetPreprocessor`.
_SNIPPET = re.compile(
    r"""(?x)
    ^(?P<space>[ \t]*)
    (?P<escape>;*)
    (?:
        (?P<inline_marker>-{1,}8<-{1,}[ \t]+)
        (?P<quote>["'])(?P<snippet>(?:\\"|\\'|(?!(?P=quote))[^\n\r])+?)(?P=quote)(?![ \t]) |
        (?P<block_marker>-{1,}8<-{1,})(?![ \t])
    )\r?$
    """
)
_SNIPPET_FILE = re.compile(
    r"(?i)(.*?)((?:(?::-?[0-9]*){1,2}(?:(?:,(?=[-0-9:])-?[0-9]*)(?::-?[0-9]*)?)*)|(?::[a-z][-_0-9a-z]*))?$"
)
# The default syntax of `mdx_include.IncludePreprocessor` and the line pattern of `markdown_include_variants`.
_MDX_INCLUDE = re.compile(r"(?<!\\)\{![+-]?>?\s*(?P<path>[^]|[]+?)(?=\s*(?:\[ln:[\d.,-]+\])?\s*(?:\|\s*.+?\s*)?!\})")
_INCLUDE_VARIANT = re.compile(r"^\{\*\s*(?P<path>\S+)\s*.*\*\}$", re.MULTILINE)


def rewrite_directives(
    site: Site,
    files: Mapping[str, Source],
    pages: Mapping[str, str],
    rewritten: dict[str, str],
    merged: MergedConfig,
) -> None:
    """Rewrite the mkdocstrings directives and snippets of the project pages in place.

    Args:
        site: The umbrella site.
        files: The merged files.
        pages: The content of the pages to rewrite, keyed by their merged path.
        rewritten: New content of changed files, keyed by merged path. Updated in place.
        merged: The merged configuration.
    """
    projects = {p.prefix: p for p in site.projects}
    snippet_paths = {prefix: _snippet_paths(project) for prefix, project in projects.items()}
    include_paths = {prefix: _include_paths(project) for prefix, project in projects.items()}
    for path in pages:
        project = projects.get(files[path].owner)
        if project is None:
            continue
        options = merged.directive_options.get(project.prefix)
        base_paths = snippet_paths[project.prefix]
        mdx_base, variants_base = include_paths[project.prefix]
        if not options and base_paths is None and mdx_base is None and variants_base is None:
            continue
        text = rewritten.get(path, pages[path])
        new_text = text
        if base_paths is not None and "8<-" in new_text:
            new_text = rewrite_snippets(new_text, base_paths)
        new_text = rewrite_includes(new_text, mdx_base=mdx_base, variants_base=variants_base)
        if options and ":::" in new_text:
            new_text = inject_options(new_text, options, default_handler=merged.default_handler)
        if new_text != text:
            rewritten[path] = new_text


def _snippet_paths(project: Project) -> list[Path] | None:
    extensions = project.config.get("markdown_extensions")
    if extensions is None:
        return None
    options = normalize_extensions(extensions, config_file=project.config_file).get(SNIPPETS)
    return None if options is None else snippet_base_paths(options, root=project.root)


def _include_paths(project: Project) -> tuple[Path | None, Path | None]:
    """Return the base paths of ``mdx_include`` and ``markdown_include_variants``, if the project uses them."""
    extensions = project.config.get("markdown_extensions")
    if extensions is None:
        return None, None
    normalized = normalize_extensions(extensions, config_file=project.config_file)
    mdx = normalized.get(MDX_INCLUDE)
    mdx_base = None if mdx is None else (project.root / str(mdx.get("base_path", "."))).resolve()
    # `markdown_include_variants` resolves paths relative to the working directory, i.e. the project root.
    return mdx_base, project.root if INCLUDE_VARIANTS in normalized else None


def rewrite_includes(text: str, *, mdx_base: Path | None, variants_base: Path | None) -> str:
    r"""Replace the paths of ``{! file !}`` and ``{* file *}`` includes that exist below the base paths.

    Args:
        text: Markdown source.
        mdx_base: Base path of ``mdx_include``, or ``None`` if the project doesn't use it.
        variants_base: Base path of ``markdown_include_variants``, or ``None`` if the project doesn't use it.

    Returns:
        The Markdown source with absolute include paths.

    Examples:
        >>> from pathlib import Path
        >>> rewrite_includes("{* missing.py hl[1] *}\n", mdx_base=None, variants_base=Path("/nowhere"))
        '{* missing.py hl[1] *}\n'
    """
    if variants_base is not None and "{*" in text:
        text = _INCLUDE_VARIANT.sub(lambda m: _replace_path(m, variants_base), text)
    if mdx_base is not None and "{!" in text:
        text = _MDX_INCLUDE.sub(lambda m: _replace_path(m, mdx_base), text)
    return text


def _replace_path(match: re.Match[str], base: Path) -> str:
    path = match.group("path")
    candidate = (base / path).resolve()
    if "://" in path or not candidate.is_file():
        return match.group(0)
    start, end = match.span("path")
    offset = match.start()
    return match.group(0)[: start - offset] + candidate.as_posix() + match.group(0)[end - offset :]


def inject_options(text: str, options: Mapping[str, Mapping[str, Any]], *, default_handler: str) -> str:
    r"""Add handler options to the ``:::`` directives in ``text``.

    Options set on a directive take precedence over the injected ones.

    Args:
        text: Markdown source.
        options: Options per handler.
        default_handler: Handler of directives that don't select one.

    Returns:
        The Markdown source with updated directives.

    Examples:
        >>> text = "::: lev\n    options:\n      members: [distance]\n\n::: dame\n"
        >>> print(inject_options(text, {"python": {"show_source": True}}, default_handler="python"), end="")
        ::: lev
            options:
              show_source: true
              members:
              - distance
        <BLANKLINE>
        ::: dame
            options:
              show_source: true
    """
    lines = text.splitlines(keepends=True)
    output: list[str] = []
    code_lines = set(range(len(lines))) - {i for i, _ in outside_fences(lines)}
    i = 0
    while i < len(lines):
        line = lines[i]
        match = None if i in code_lines else _DIRECTIVE.match(line)
        output.append(line)
        i += 1
        if match is None:
            continue
        indent = match.group("indent")
        start = i
        # Like mkdocstrings, the YAML configuration is the indented block following the directive.
        while i < len(lines) and lines[i].strip() and _indent(lines[i]) > len(indent) and i not in code_lines:
            i += 1
        block = "".join(lines[start:i])
        config = yaml.safe_load(_dedent(block, indent)) if block.strip() else None
        config = config if isinstance(config, dict) else {}
        handler_options = options.get(config.get("handler", default_handler))
        if not handler_options:
            output.extend(lines[start:i])
            continue
        config["options"] = {**handler_options, **(config.get("options") or {})}
        dumped = yaml.safe_dump(config, sort_keys=False, default_flow_style=False, allow_unicode=True)
        if not line.endswith("\n"):
            output[-1] += "\n"
        output.extend(f"{indent}    {row}\n" for row in dumped.splitlines())
    result = "".join(output)
    return result if text.endswith("\n") else result.removesuffix("\n")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _dedent(block: str, indent: str) -> str:
    lines = [line.removeprefix(indent) for line in block.splitlines()]
    width = min((len(line) - len(line.lstrip()) for line in lines if line.strip()), default=0)
    return "\n".join(line[width:] for line in lines)


def rewrite_snippets(text: str, base_paths: list[Path]) -> str:
    """Replace the paths of snippets that exist in ``base_paths`` with absolute paths.

    Args:
        text: Markdown source.
        base_paths: Absolute base paths of the project's snippets.

    Returns:
        The Markdown source with absolute snippet paths.
    """
    lines = text.splitlines(keepends=True)
    in_block = False
    for i, line in enumerate(lines):
        match = _SNIPPET.match(line.rstrip("\n"))
        if match is not None and not match.group("escape"):
            if match.group("block_marker"):
                in_block = not in_block
            else:
                start, end = match.span("snippet")
                lines[i] = line[:start] + _resolve(match.group("snippet"), base_paths) + line[end:]
            continue
        if in_block and line.strip() and not line.lstrip().startswith(";"):
            content = line.rstrip("\r\n")
            stripped = content.strip()
            start = content.index(stripped)
            lines[i] = content[:start] + _resolve(stripped, base_paths) + line[len(content) :]
    return "".join(lines)


def _resolve(snippet: str, base_paths: list[Path]) -> str:
    if "://" in snippet:
        return snippet
    match = _SNIPPET_FILE.match(snippet)
    filename, suffix = (match.group(1), match.group(2) or "") if match else (snippet, "")
    for base in base_paths:
        candidate = (base / filename).resolve()
        if candidate.is_relative_to(base) and candidate.is_file():
            return candidate.as_posix() + suffix
    return snippet

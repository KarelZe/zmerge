"""Rewrite links in the merged Markdown files so they work in the merged site.

Two kinds of links are rewritten:

- **Links between projects.** Projects link to each other with absolute URLs of their published sites, e.g.
  ``https://example.org/typer/tutorial/first-steps/#the-simplest-example``. These links work when every project is
  built on its own. In the merged site, they become relative links to the merged page, e.g.
  ``../typer/tutorial/first-steps.md#the-simplest-example``, so Zensical validates them and they stay within the merged
  site.
- **Links leaving a project's docs.** Relative links like ``../LICENSE`` point outside the project's ``docs_dir``. In
  the merged site, they would resolve to unrelated files, so they become links to the file in the project's
  repository, derived from ``repo_url`` and ``edit_uri``.

Links in fenced code blocks and inline code are left untouched.
"""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterator, Mapping

    from zmerge.assemble import Source
    from zmerge.config import Project, Site

_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
_CODE_SPAN = re.compile(r"(`+)(.+?)\1")
_INLINE_LINK = re.compile(r"\]\(\s*")
_REFERENCE = re.compile(r"^ {0,3}\[[^\]]+\]:[ \t]*")
_EDIT_URI = re.compile(r"^(.*?)(?:edit|blob|tree)/([^/]+)/")
_AUTOLINK = re.compile(r"<([a-zA-Z][a-zA-Z0-9+.-]*:[^>\s]+)>")
_HREF_SRC = re.compile(r"\b(?:href|src)\s*=\s*(['\"])(.*?)\1", re.IGNORECASE)
_BARE_LINK = re.compile(r"(?<!<)\b(https?://[^\s<'\"]+)")
_REWRITE_CANDIDATE = re.compile(r"\]\(|\]:|\b(?:href|src)\s*=|http|<", re.IGNORECASE)


@dataclass(frozen=True)
class _Site:
    """A published site whose absolute URLs are mapped to merged files."""

    netloc: str
    path: str
    prefix: str


def rewrite_links(
    site: Site, files: Mapping[str, Source], *, excluded: Collection[str] = ()
) -> tuple[dict[str, str], list[str]]:
    """Rewrite the links of all Markdown files of the merged docs.

    Args:
        site: The umbrella site.
        files: The merged files, keyed by their path relative to the merged docs directory.
        excluded: Merged paths of pages to leave alone, e.g. pages excluded with ``exclude_docs``.

    Returns:
        The new content of the files that changed, keyed by their merged path, and warnings about links that could
        not be rewritten.
    """
    projects = {p.prefix: p for p in site.projects}
    sites = _published_sites(site)
    rewritten: dict[str, str] = {}
    warnings: list[str] = []
    for path, source in files.items():
        if not path.endswith(".md") or path in excluded:
            continue
        text = source.path.read_text(encoding="utf-8")
        if not _REWRITE_CANDIDATE.search(text):
            continue
        project = projects.get(source.owner)

        def rewrite(destination: str, *, path: str = path, project: Project | None = project) -> str:
            return _rewrite(destination, page=path, project=project, sites=sites, files=files, warnings=warnings)

        new_text = rewrite_destinations(text, rewrite)
        if new_text != text:
            rewritten[path] = new_text
    return rewritten, warnings


def rewrite_destinations(text: str, rewrite: Callable[[str], str]) -> str:
    r"""Apply ``rewrite`` to the destination of every inline link, image and link reference definition.

    Args:
        text: Markdown source.
        rewrite: Maps a link destination to its replacement.

    Returns:
        The Markdown source with rewritten destinations.

    Examples:
        >>> text = "[a](a.md) ![b](<b c.png> 'title') `[c](c.md)`\n[d]: d.md\n```\n[e](e.md)\n```\n"
        >>> print(rewrite_destinations(text, str.upper), end="")
        [a](A.MD) ![b](<B C.PNG> 'title') `[c](c.md)`
        [d]: D.MD
        ```
        [e](e.md)
        ```
    """
    lines = text.splitlines(keepends=True)
    for i, line in outside_fences(lines):
        if _REWRITE_CANDIDATE.search(line):
            lines[i] = _rewrite_line(line, rewrite)
    return "".join(lines)


def outside_fences(lines: list[str]) -> Iterator[tuple[int, str]]:
    """Yield the lines that are not part of a fenced code block, including the fences.

    Args:
        lines: Lines of Markdown source.

    Yields:
        Index and content of every line outside of fenced code blocks.
    """
    fence: str | None = None
    for i, line in enumerate(lines):
        if match := _FENCE.match(line):
            marker = match.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence) and not line[match.end() :].strip():
                fence = None
            continue
        if fence is None:
            yield i, line


def _rewrite_line(line: str, rewrite: Callable[[str], str]) -> str:
    # Blank out code spans, keeping offsets intact, so links inside them are not found.
    masked = _CODE_SPAN.sub(lambda m: " " * len(m.group(0)), line)
    spans: list[tuple[int, int]] = []
    if match := _REFERENCE.match(masked):
        spans.append(_destination(masked, match.end()))
    spans.extend(_destination(masked, m.end()) for m in _INLINE_LINK.finditer(masked))
    spans.extend((m.start(2), m.end(2)) for m in _HREF_SRC.finditer(masked))
    spans.extend((m.start(1), m.end(1)) for m in _AUTOLINK.finditer(masked))

    masked_for_bare = list(masked)
    for start, end in spans:
        masked_for_bare[start:end] = [" "] * (end - start)
    masked_bare_str = "".join(masked_for_bare)

    for m in _BARE_LINK.finditer(masked_bare_str):
        url = m.group(1)
        while url and url[-1] in ".,;:?!":
            url = url[:-1]
        start = m.start(1)
        spans.append((start, start + len(url)))

    spans = list(set(spans))

    for start, end in sorted(spans, reverse=True):
        if start == end:
            continue
        destination = line[start:end]
        if destination.startswith("<") and destination.endswith(">"):
            replacement = "<" + rewrite(destination[1:-1]) + ">"
        else:
            replacement = rewrite(destination)
        line = line[:start] + replacement + line[end:]
    return line


def _destination(text: str, start: int) -> tuple[int, int]:
    """Find the link destination starting at ``start``, see https://spec.commonmark.org/0.31.2/#link-destination."""
    if text.startswith("<", start):
        end = text.find(">", start)
        return (start, end + 1) if end != -1 else (start, start)
    depth = 0
    end = start
    while end < len(text) and not text[end].isspace():
        char = text[end]
        if char == "(":
            depth += 1
        elif char == ")":
            if depth == 0:
                break
            depth -= 1
        end += 1
    return start, end


def _published_sites(site: Site) -> list[_Site]:
    """Map the ``site_url`` of the umbrella and every project to its prefix, longest URL first."""
    sites = []
    for prefix, config in [("", site.config), *((p.prefix, p.config) for p in site.projects)]:
        if site_url := config.get("site_url"):
            parts = urlsplit(site_url)
            sites.append(_Site(netloc=parts.netloc.lower(), path=parts.path.rstrip("/") + "/", prefix=prefix))
    return sorted(sites, key=lambda s: len(s.path), reverse=True)


def _rewrite(
    destination: str,
    *,
    page: str,
    project: Project | None,
    sites: list[_Site],
    files: Mapping[str, Source],
    warnings: list[str],
) -> str:
    if destination.startswith("#") or destination.startswith("/"):
        return destination
    if _SCHEME.match(destination):
        if destination.startswith(("http://", "https://")):
            return _rewrite_absolute(destination, page=page, sites=sites, files=files, warnings=warnings)
        return destination
    if project is not None:
        return _rewrite_escaping(destination, page=page, project=project, warnings=warnings)
    return destination


def _rewrite_absolute(
    destination: str, *, page: str, sites: list[_Site], files: Mapping[str, Source], warnings: list[str]
) -> str:
    parts = urlsplit(destination)
    netloc = parts.netloc.lower()
    path = parts.path if parts.path.endswith("/") or "." in posixpath.basename(parts.path) else parts.path + "/"
    for published in sites:
        if netloc != published.netloc or not path.startswith(published.path):
            continue
        rest = path.removeprefix(published.path)
        base = f"{published.prefix}/{rest}" if published.prefix else rest
        target = next((c for c in _candidates(base) if c in files), None)
        if target is None:
            # The umbrella's URL may host other sites, too, so only links into a project's site are suspicious.
            if published.prefix:
                warnings.append(f"{page}: {destination} matches no merged page; leaving it unchanged")
            return destination
        relative = posixpath.relpath(target, posixpath.dirname(page) or ".")
        return relative + (f"#{parts.fragment}" if parts.fragment else "")
    return destination


def _candidates(path: str) -> list[str]:
    """Return the merged files a URL path may have been generated from.

    Examples:
        >>> _candidates("dame/design/")
        ['dame/design.md', 'dame/design/index.md', 'dame/design/README.md']
        >>> _candidates("dame/design.html")
        ['dame/design.md']
        >>> _candidates("dame/index.html")
        ['dame/index.md', 'dame/README.md']
        >>> _candidates("dame/assets/app.png")
        ['dame/assets/app.png']
    """
    path = path.lstrip("/")
    if not path or path.endswith("/"):
        directory = path.rstrip("/")
        prefix = f"{directory}/" if directory else ""
        pages = [f"{prefix}index.md", f"{prefix}README.md"]
        return [f"{directory}.md", *pages] if directory else pages
    if path.endswith("/index.html"):
        return [path.removesuffix("index.html") + "index.md", path.removesuffix("index.html") + "README.md"]
    if path.endswith(".html"):
        return [path.removesuffix(".html") + ".md"]
    return [path]


def _rewrite_escaping(destination: str, *, page: str, project: Project, warnings: list[str]) -> str:
    path, _, fragment = destination.partition("#")
    if not path:
        return destination
    page_dir = posixpath.dirname(page.removeprefix(project.prefix + "/"))
    relative = posixpath.normpath(posixpath.join(page_dir, path))
    if not relative.startswith("../"):
        return destination  # The link stays inside the project's docs.

    target = (project.docs_dir / relative).resolve()
    if not target.exists() or not target.is_relative_to(project.root):
        return destination  # Zensical reports broken links to pages.
    repo_url = project.config.get("repo_url")
    match = _EDIT_URI.match(project.config.get("edit_uri", ""))
    if not repo_url or not match:
        warnings.append(
            f"{project.config_file}: {page} links to {destination} outside of the docs; set `repo_url` and "
            "`edit_uri` to link to the repository instead"
        )
        return destination
    kind = "tree" if target.is_dir() else "blob"
    repo_path = target.relative_to(project.root).as_posix()
    url = f"{repo_url.rstrip('/')}/{match.group(1)}{kind}/{match.group(2)}/{repo_path}"
    return url + (f"#{fragment}" if fragment else "")

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

Both are rewritten wherever Zensical resolves relative links: in inline links, images, reference definitions and the
``href``, ``src`` and ``srcset`` attributes of raw HTML. Like Zensical, zmerge leaves autolinks and links in fenced
code blocks and inline code untouched.
"""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from itertools import chain
from typing import TYPE_CHECKING
from urllib.parse import ParseResult, urlparse

from markdown.inlinepatterns import HTML_RE

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping

    from zmerge.assemble import Source
    from zmerge.config import Project, Site

_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
_CODE_SPAN = re.compile(r"(`+)(.+?)\1")
_NOT_NEWLINE = re.compile(r"[^\r\n]")
_INLINE_LINK = re.compile(r"\]\(\s*")
_REFERENCE = re.compile(r"^ {0,3}\[[^\]\n]+\]:[ \t]*", re.MULTILINE)
_ANGLE_DESTINATION = re.compile(r"<[^<>\n]*>")
_EDIT_URI = re.compile(r"^(.*?)(?:edit|blob|tree)/([^/]+)/")
# Raw HTML as Python-Markdown finds it, and the attributes in it that Zensical rewrites, see
# `zensical.extensions.links`. Python-Markdown compiles its inline patterns with these flags.
_HTML_TAG = re.compile(HTML_RE, re.DOTALL | re.UNICODE)
_HTML_URL = re.compile(r"""(href|src|srcset)=(["'])([^"']+)\2""", re.IGNORECASE)
_SRCSET_URL = re.compile(r"[\s,]*([^\s,]\S*)")
_SRCSET_DESCRIPTORS = re.compile(r"[^,(]*(?:\([^)]*\)[^,(]*)*,?")
# Pages without any of these have no links to rewrite.
_MARKER = re.compile(r"\]\(|\]:|<[a-zA-Z]")


@dataclass(frozen=True)
class _Site:
    """A published site whose absolute URLs are mapped to merged files."""

    netloc: str
    path: str
    prefix: str


def rewrite_links(
    site: Site, files: Mapping[str, Source], pages: Mapping[str, str]
) -> tuple[dict[str, str], list[str]]:
    """Rewrite the links of the Markdown pages of the merged docs.

    Args:
        site: The umbrella site.
        files: The merged files, keyed by their path relative to the merged docs directory.
        pages: The content of the pages to rewrite, keyed by their merged path.

    Returns:
        The new content of the files that changed, keyed by their merged path, and warnings about links that could
        not be rewritten.
    """
    projects = {p.prefix: p for p in site.projects}
    sites = _published_sites(site)
    rewritten: dict[str, str] = {}
    warnings: list[str] = []
    for path, text in pages.items():
        if not _MARKER.search(text):
            continue
        project = projects.get(files[path].owner)

        def rewrite(destination: str, *, path: str = path, project: Project | None = project) -> str:
            return _rewrite(destination, page=path, project=project, sites=sites, files=files, warnings=warnings)

        new_text = rewrite_destinations(text, rewrite)
        if new_text != text:
            rewritten[path] = new_text
    return rewritten, warnings


def rewrite_destinations(text: str, rewrite: Callable[[str], str]) -> str:
    r"""Apply ``rewrite`` to every link destination that Zensical resolves.

    These are the destinations of inline links, images and link reference definitions, and the ``href``, ``src`` and
    ``srcset`` attributes of raw HTML.

    Args:
        text: Markdown source.
        rewrite: Maps a link destination to its replacement.

    Returns:
        The Markdown source with rewritten destinations.

    Examples:
        >>> text = "[a](a.md) ![b](<b c.png> 'title') `[c](c.md)`\n[d]: d.md <http://e>\n```\n[f](f.md)\n```\n"
        >>> print(rewrite_destinations(text, str.upper), end="")
        [a](A.MD) ![b](<B C.PNG> 'title') `[c](c.md)`
        [d]: D.MD <http://e>
        ```
        [f](f.md)
        ```
        >>> rewrite_destinations('<a href="a.md">a</a> <img\nSRCSET="b.png 2x, c.png">', str.upper)
        '<a href="A.MD">a</a> <img\nSRCSET="B.PNG 2x, C.PNG">'
    """
    masked = _mask_code(text)
    edits: list[tuple[int, int, str]] = []
    for match in chain(_REFERENCE.finditer(masked), _INLINE_LINK.finditer(masked)):
        start, end = _destination(masked, match.end())
        if masked.startswith("<", start):
            start, end = start + 1, end - 1
        if start < end:
            edits.append((start, end, rewrite(text[start:end])))
    for tag in _HTML_TAG.finditer(masked):
        for attribute in _HTML_URL.finditer(masked, tag.start(), tag.end()):
            start, end = attribute.span(3)
            urls = _srcset_urls(text, start, end) if attribute.group(1).lower() == "srcset" else [(start, end)]
            edits.extend((s, e, rewrite(text[s:e])) for s, e in urls)

    parts: list[str] = []
    position = 0
    for start, end, replacement in sorted(edits):
        if start < position:
            continue  # Overlaps the previous destination.
        parts += [text[position:start], replacement]
        position = end
    return "".join(parts) + text[position:]


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


def _mask_code(text: str) -> str:
    """Blank out fenced code blocks and code spans, keeping offsets and line breaks, so links in them are not found."""
    lines = text.splitlines(keepends=True)
    masked = [_NOT_NEWLINE.sub(" ", line) for line in lines]
    for i, line in outside_fences(lines):
        masked[i] = _CODE_SPAN.sub(lambda m: " " * len(m.group(0)), line)
    return "".join(masked)


def _destination(text: str, start: int) -> tuple[int, int]:
    """Find the link destination starting at ``start``, see https://spec.commonmark.org/0.31.2/#link-destination."""
    if text.startswith("<", start):
        match = _ANGLE_DESTINATION.match(text, start)
        return match.span() if match else (start, start)
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


def _srcset_urls(text: str, start: int, end: int) -> Iterator[tuple[int, int]]:
    """Find the URLs of the ``srcset`` in ``text[start:end]``, see https://html.spec.whatwg.org/#srcset-attributes.

    Yields:
        Start and end of every URL, without its descriptors.

    Examples:
        >>> value = "a.png, b.png 2x,c,d.png 100w"
        >>> [value[s:e] for s, e in _srcset_urls(value, 0, len(value))]
        ['a.png', 'b.png', 'c,d.png']
    """
    position = start
    while match := _SRCSET_URL.match(text, position, end):
        url_start, position = match.span(1)
        url_end = url_start + len(match.group(1).rstrip(","))
        yield url_start, url_end
        # Unless the URL ends in a comma, descriptors follow up to the next comma.
        if url_end == position and (descriptors := _SRCSET_DESCRIPTORS.match(text, position, end)):
            position = descriptors.end()


def _published_sites(site: Site) -> list[_Site]:
    """Map the ``site_url`` of the umbrella and every project to its prefix, longest URL first."""
    sites = []
    for prefix, config in [("", site.config), *((p.prefix, p.config) for p in site.projects)]:
        if site_url := config.get("site_url"):
            parts = urlparse(site_url)
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
    try:
        url = urlparse(destination)
    except ValueError:
        return destination
    if url.scheme in ("http", "https"):
        return _rewrite_absolute(url, page=page, sites=sites, files=files, warnings=warnings) or destination
    if project is None or not _is_relative(url):
        return destination
    return _rewrite_escaping(url, page=page, project=project, warnings=warnings) or destination


def _is_relative(url: ParseResult) -> bool:
    """Tell whether Zensical resolves a URL relative to the page, like ``zensical.extensions.links._is_relative``.

    Returns:
        Whether the URL is relative to the page.

    Examples:
        >>> [_is_relative(urlparse(u)) for u in ("../a.md#b", "?q", "#b", "/a.md", "//host/a", "mailto:me")]
        [True, True, False, False, False, False]
    """
    if url.scheme or url.netloc or url.path.startswith("/"):
        return False
    # A link to an anchor points within the page.
    return bool(url.path) or not url.fragment


def _rewrite_absolute(
    url: ParseResult, *, page: str, sites: list[_Site], files: Mapping[str, Source], warnings: list[str]
) -> str | None:
    """Return the relative link to the merged page an absolute URL points to, or ``None`` to leave it unchanged."""
    netloc = url.netloc.lower()
    path = url.path if url.path.endswith("/") or "." in posixpath.basename(url.path) else url.path + "/"
    for published in sites:
        if netloc != published.netloc or not path.startswith(published.path):
            continue
        rest = path.removeprefix(published.path)
        base = f"{published.prefix}/{rest}" if published.prefix else rest
        target = next((c for c in _candidates(base) if c in files), None)
        if target is None:
            # The umbrella's URL may host other sites, too, so only links into a project's site are suspicious.
            if published.prefix:
                warnings.append(f"{page}: {url.geturl()} matches no merged page; leaving it unchanged")
            return None
        relative = posixpath.relpath(target, posixpath.dirname(page) or ".")
        return url._replace(scheme="", netloc="", path=relative).geturl()
    return None


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


def _rewrite_escaping(url: ParseResult, *, page: str, project: Project, warnings: list[str]) -> str | None:
    """Return the repository URL of a file a relative link out of the docs points to, or ``None`` to leave it."""
    page_dir = posixpath.dirname(page.removeprefix(project.prefix + "/"))
    relative = posixpath.normpath(posixpath.join(page_dir, url.path))
    if not relative.startswith("../"):
        return None  # The link stays inside the project's docs.

    target = (project.docs_dir / relative).resolve()
    if not target.exists() or not target.is_relative_to(project.root):
        return None  # Zensical reports broken links to pages.
    repo_url = project.config.get("repo_url")
    match = _EDIT_URI.match(project.config.get("edit_uri", ""))
    if not repo_url or not match:
        warnings.append(
            f"{project.config_file}: {page} links to {url.geturl()} outside of the docs; set `repo_url` and "
            "`edit_uri` to link to the repository instead"
        )
        return None
    kind = "tree" if target.is_dir() else "blob"
    repo_path = target.relative_to(project.root).as_posix()
    repo_file = urlparse(f"{repo_url.rstrip('/')}/{match.group(1)}{kind}/{match.group(2)}/{repo_path}")
    return repo_file._replace(query=url.query, fragment=url.fragment).geturl()

"""Fetch projects from git repositories.

An include can point to a git repository instead of a local path, using the syntax known from pip:

```toml
nav = [
  { lev = "!include git+https://github.com/KarelZe/lev.git" },
  { dame = "!include git+https://github.com/KarelZe/dame-rs.git@main" },
  { docs = "!include git+https://github.com/me/mono.git@v1.0#subdirectory=packages/docs" },
]
```

The ref (branch, tag or commit) defaults to the repository's default branch. The ``subdirectory`` is the directory
containing the ``zensical.toml`` or the path to it. Repositories are shallowly fetched into ``.zmerge/repos`` next to
the umbrella configuration and updated on every run, unless fetching is disabled.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from zmerge.errors import ZmergeError

if TYPE_CHECKING:
    from pathlib import Path

GIT_PREFIX = "git+"
REPOS_DIR = "repos"

_REF = re.compile(r"^[\w./-]+$")


@dataclass(frozen=True)
class GitSource:
    """A project in a git repository.

    Attributes:
        url: URL of the repository.
        ref: Branch, tag or commit, or ``None`` for the default branch.
        subdirectory: Path of the project within the repository.
    """

    url: str
    ref: str | None
    subdirectory: str

    @classmethod
    def parse(cls, spec: str) -> GitSource:
        """Parse a ``git+<url>[@<ref>][#subdirectory=<path>]`` specification.

        Args:
            spec: The specification.

        Returns:
            The parsed source.

        Raises:
            ZmergeError: If the specification is invalid.

        Examples:
            >>> GitSource.parse("git+https://github.com/me/lev.git@v1#subdirectory=docs")
            GitSource(url='https://github.com/me/lev.git', ref='v1', subdirectory='docs')
            >>> GitSource.parse("git+ssh://git@github.com/me/lev.git")
            GitSource(url='ssh://git@github.com/me/lev.git', ref=None, subdirectory='')
        """
        rest, _, fragment = spec.removeprefix(GIT_PREFIX).partition("#")
        subdirectory = ""
        if fragment:
            key, _, value = fragment.partition("=")
            if key != "subdirectory" or not value:
                raise ZmergeError(f"invalid fragment {fragment!r} in {spec!r}; use `#subdirectory=<path>`")
            subdirectory = value.strip("/")
        parts = urlsplit(rest)
        url, ref = rest, None
        # An `@` in the path separates the ref, while one in the netloc separates the user, e.g. `git@github.com`.
        if "@" in parts.path:
            path, _, ref = parts.path.rpartition("@")
            url = parts._replace(path=path).geturl()
        if not parts.scheme or (not parts.netloc and parts.scheme != "file") or url.startswith("-"):
            raise ZmergeError(f"invalid git URL in {spec!r}")
        if ref is not None and (not _REF.match(ref) or ref.startswith("-")):
            raise ZmergeError(f"invalid git ref {ref!r} in {spec!r}")
        if ".." in subdirectory.split("/"):
            raise ZmergeError(f"subdirectory of {spec!r} must stay inside the repository")
        return cls(url=url, ref=ref, subdirectory=subdirectory)

    @property
    def cache_name(self) -> str:
        """Name of the directory the repository is fetched into."""
        parts = urlsplit(self.url)
        name = re.sub(r"[^A-Za-z0-9._-]+", "-", f"{parts.netloc}{parts.path}".removesuffix(".git")).strip("-.")
        digest = hashlib.sha256(f"{self.url}@{self.ref or ''}".encode()).hexdigest()[:8]
        return f"{name[-60:]}-{digest}"


def fetch(source: GitSource, cache_dir: Path, *, update: bool = True) -> Path:
    """Fetch a repository into ``cache_dir`` and return the path to the project.

    Args:
        source: The git source.
        cache_dir: Directory holding fetched repositories.
        update: Whether to fetch an already fetched repository again.

    Returns:
        Path to the project, i.e. the ``subdirectory`` of the checked out repository.

    Raises:
        ZmergeError: If git fails.
    """
    checkout = cache_dir / source.cache_name
    fetched = (checkout / ".git").is_dir()
    if not fetched or update:
        if not fetched:
            checkout.mkdir(parents=True, exist_ok=True)
            _git(["init", "--quiet"], cwd=checkout)
        ref = source.ref or "HEAD"
        _git(["fetch", "--quiet", "--depth", "1", "--", source.url, ref], cwd=checkout)
        _git(["checkout", "--quiet", "--force", "--detach", "FETCH_HEAD"], cwd=checkout)
        _git(["clean", "--quiet", "-d", "--force", "-x"], cwd=checkout)
    return checkout / source.subdirectory if source.subdirectory else checkout


def _git(args: list[str], *, cwd: Path) -> None:
    try:
        subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        raise ZmergeError("git is required for `git+` includes but was not found") from None
    except subprocess.CalledProcessError as e:
        raise ZmergeError(f"`git {' '.join(args)}` failed: {e.stderr.strip()}") from None

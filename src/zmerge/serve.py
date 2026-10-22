"""Serve the merged site and re-assemble it when the sources of the umbrella site or a project change.

``zensical serve`` watches the merged docs directory. zmerge watches the sources and incrementally re-assembles the
merged project, so Zensical only sees the files that changed.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

from zmerge.assemble import assemble
from zmerge.config import ZmergeError, load_site

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

    from zmerge.config import Site

Snapshot = dict[Path, tuple[int, int, int]]


def watched_paths(site: Site) -> list[Path]:
    """Return the configuration files and docs directories of the umbrella site and all projects.

    Args:
        site: The umbrella site.

    Returns:
        The paths to watch.
    """
    paths = [site.config_file, site.docs_dir]
    for project in site.projects:
        paths += [project.config_file, project.docs_dir]
    return paths


def snapshot(paths: Iterable[Path]) -> Snapshot:
    """Record modification time, size and inode of every file below ``paths``.

    Args:
        paths: Files or directories.

    Returns:
        The state of all files, keyed by path.
    """
    state: Snapshot = {}
    for path in paths:
        if path.is_file():
            state[path] = _stat(path)
            continue
        for dirpath, dirnames, filenames in os.walk(path):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for filename in filenames:
                file = Path(dirpath, filename)
                try:
                    state[file] = _stat(file)
                except FileNotFoundError:  # pragma: no cover - deleted while walking
                    continue
    return state


def _stat(path: Path) -> tuple[int, int, int]:
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size, stat.st_ino


def serve(
    config_file: Path,
    zensical_args: Sequence[str] = (),
    *,
    update: bool = True,
    interval: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Assemble the merged site, serve it with ``zensical serve`` and re-assemble it on changes.

    Args:
        config_file: Path to the umbrella configuration.
        zensical_args: Additional arguments for ``zensical serve``.
        update: Whether to update fetched git repositories at startup. They are never fetched on changes.
        interval: Seconds between checks for changes.
        sleep: Function to wait between checks.

    Returns:
        The exit code of ``zensical serve``. A ``ZmergeError`` of the initial merge is propagated.
    """
    site = load_site(config_file, update=update)
    assembly = assemble(site)
    _report(assembly.warnings)
    command = [sys.executable, "-m", "zensical", "serve", "--config-file", str(assembly.config_file), *zensical_args]
    process = subprocess.Popen(command, cwd=site.root)
    # Turn the first SIGTERM into an exception, so the server is stopped below instead of being orphaned. Further
    # signals, e.g. forwarded by `uv run`, must not interrupt stopping it.
    stopping = False

    def on_sigterm(signum: int, frame: object) -> None:
        nonlocal stopping
        if not stopping:
            stopping = True
            raise KeyboardInterrupt

    previous = signal.signal(signal.SIGTERM, on_sigterm)
    state = snapshot(watched_paths(site))
    try:
        while process.poll() is None:
            sleep(interval)
            current = snapshot(watched_paths(site))
            if current == state:
                continue
            state = current
            try:
                site = load_site(config_file, update=False)
                assembly = assemble(site)
            except ZmergeError as e:
                print(f"zmerge: error: {e}", file=sys.stderr)
                continue
            _report(assembly.warnings)
            print("zmerge: re-assembled the merged site", file=sys.stderr)
            # Projects may have been added or removed.
            state = snapshot(watched_paths(site))
    except KeyboardInterrupt:
        pass
    finally:
        stopping = True
        _stop(process)
        signal.signal(signal.SIGTERM, previous)
    return process.returncode


def _stop(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:  # pragma: no cover - Zensical ignores SIGTERM
            process.kill()
            process.wait()


def _report(warnings: list[str]) -> None:
    for warning in warnings:
        print(f"zmerge: warning: {warning}", file=sys.stderr)

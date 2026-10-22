"""Command line interface of zmerge."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

from zmerge import __version__

if TYPE_CHECKING:
    from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    Returns:
        The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="zmerge",
        description="Merge the documentation of multiple Zensical projects into one site.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line interface.

    Args:
        argv: Command line arguments without the program name. Defaults to ``sys.argv[1:]``.

    Returns:
        The exit code.
    """
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 0

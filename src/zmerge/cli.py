"""Command line interface of zmerge."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from zmerge import __version__
from zmerge.assemble import assemble
from zmerge.config import ZmergeError, load_site

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
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")

    config = argparse.ArgumentParser(add_help=False)
    config.add_argument(
        "-f",
        "--config-file",
        type=Path,
        default=Path("zensical.toml"),
        help="umbrella configuration (default: %(default)s)",
    )

    commands.add_parser(
        "assemble",
        parents=[config],
        help="write the merged Zensical project without building it",
        description="Write the merged Zensical project (.zmerge.toml and .zmerge/) next to the umbrella config.",
    )
    build = commands.add_parser(
        "build",
        parents=[config],
        help="assemble and build the merged site with Zensical",
        description="Assemble the merged Zensical project and build it with `zensical build`.",
    )
    build.add_argument("-s", "--strict", action="store_true", help="abort on zmerge or Zensical warnings")
    build.add_argument("-c", "--clean", action="store_true", help="clean the Zensical build cache")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line interface.

    Args:
        argv: Command line arguments without the program name. Defaults to ``sys.argv[1:]``.

    Returns:
        The exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        site = load_site(args.config_file)
        assembly = assemble(site)
    except ZmergeError as e:
        print(f"zmerge: error: {e}", file=sys.stderr)
        return 1
    for warning in assembly.warnings:
        print(f"zmerge: warning: {warning}", file=sys.stderr)
    if args.command == "assemble":
        print(assembly.config_file)
        return 0

    if args.strict and assembly.warnings:
        print("zmerge: aborted because --strict is set", file=sys.stderr)
        return 1
    command = [sys.executable, "-m", "zensical", "build", "--config-file", str(assembly.config_file)]
    command += ["--strict"] * args.strict + ["--clean"] * args.clean
    return subprocess.run(command, cwd=site.root, check=False).returncode

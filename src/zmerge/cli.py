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
from zmerge.serve import serve

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
        allow_abbrev=False,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")

    # Options unknown to zmerge are passed to Zensical. No abbreviations, so they can't be mistaken for zmerge's.
    config = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    config.add_argument(
        "-f",
        "--config-file",
        type=Path,
        default=Path("zensical.toml"),
        help="umbrella configuration (default: %(default)s)",
    )
    config.add_argument(
        "--no-fetch",
        dest="fetch",
        action="store_false",
        help="reuse fetched git repositories instead of updating them",
    )

    commands.add_parser(
        "assemble",
        parents=[config],
        help="write the merged Zensical project without building it",
        description="Write the merged Zensical project (.zmerge.toml and .zmerge/) next to the umbrella config.",
        allow_abbrev=False,
    )
    build = commands.add_parser(
        "build",
        parents=[config],
        help="assemble and build the merged site with Zensical",
        description="Assemble the merged Zensical project and build it with `zensical build`.",
        epilog="Other options are passed to `zensical build`, e.g.:\n"
        "  -c, --clean           clean the Zensical build cache\n\n"
        "See `zensical build --help`.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    build.add_argument("-s", "--strict", action="store_true", help="abort on zmerge or Zensical warnings")
    commands.add_parser(
        "serve",
        parents=[config],
        help="serve the merged site and re-assemble it on changes",
        description="Serve the merged site with `zensical serve` and re-assemble it when a project changes.",
        epilog="Other options are passed to `zensical serve`, e.g.:\n"
        "  -a, --dev-addr IP:PORT\n"
        "                        IP address and port (default: localhost:8000)\n"
        "  -o, --open            open the preview in the default browser\n\n"
        "See `zensical serve --help`.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line interface.

    Args:
        argv: Command line arguments without the program name. Defaults to ``sys.argv[1:]``.

    Returns:
        The exit code.
    """
    parser = build_parser()
    args, zensical_args = parser.parse_known_args(argv)
    if zensical_args[:1] == ["--"]:
        zensical_args = zensical_args[1:]
    if zensical_args and args.command not in {"build", "serve"}:
        parser.error(f"unrecognized arguments: {' '.join(zensical_args)}")
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "serve":
        try:
            return serve(args.config_file, zensical_args, update=args.fetch)
        except ZmergeError as e:
            print(f"zmerge: error: {e}", file=sys.stderr)
            return 1
    try:
        site = load_site(args.config_file, update=args.fetch)
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
    command += ["--strict"] * args.strict + zensical_args
    try:
        return subprocess.run(command, cwd=site.root, check=True).returncode
    except subprocess.CalledProcessError as e:
        return e.returncode

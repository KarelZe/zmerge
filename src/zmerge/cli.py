"""Command line interface of zmerge."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any

import click

from zmerge import __version__
from zmerge.assemble import assemble
from zmerge.config import ZmergeError, load_site
from zmerge.errors import error, warn
from zmerge.serve import serve

if TYPE_CHECKING:
    from collections.abc import Callable

    from zmerge.assemble import Assembly
    from zmerge.config import Site

# Options unknown to zmerge are collected in `zensical_args` and passed to Zensical.
PASS_THROUGH = {"ignore_unknown_options": True}


class CliError(click.ClickException):
    """A fatal error, reported like zmerge's other errors."""

    def show(self, file: IO[Any] | None = None) -> None:
        """Report the error on stderr."""
        error(self.format_message())


def project_options(command: Callable[..., None]) -> Callable[..., None]:
    """Add the options shared by all commands."""
    command = click.option(
        "--fetch/--no-fetch",
        default=True,
        help="Update fetched git repositories or reuse them.",
    )(command)
    return click.option(
        "-f",
        "--config-file",
        type=click.Path(dir_okay=False, path_type=Path),
        default="zensical.toml",
        show_default=True,
        help="Umbrella configuration.",
    )(command)


def zensical_arguments(command: Callable[..., None]) -> Callable[..., None]:
    """Collect the arguments passed to Zensical."""
    return click.argument("zensical_args", nargs=-1, type=click.UNPROCESSED)(command)


def load(config_file: Path, *, fetch: bool) -> tuple[Site, Assembly]:
    """Load and assemble the merged site and report zmerge's warnings.

    Args:
        config_file: Path to the umbrella configuration.
        fetch: Whether to update fetched git repositories.

    Returns:
        The loaded site and its assembly.

    Raises:
        CliError: If the site can't be merged.
    """
    try:
        site = load_site(config_file, update=fetch)
        assembly = assemble(site)
    except ZmergeError as e:
        raise CliError(str(e)) from e
    for warning in assembly.warnings:
        warn(warning)
    return site, assembly


@click.version_option(__version__, "--version", prog_name="zmerge", message="%(prog)s %(version)s")
@click.group("zmerge", context_settings={"help_option_names": ["-h", "--help"]})
def main() -> None:
    """Merge the documentation of multiple Zensical projects into one site."""


@main.command("assemble")
@project_options
def assemble_command(config_file: Path, fetch: bool) -> None:
    """Write the merged Zensical project (.zmerge.toml and .zmerge/) next to the umbrella config."""
    _, assembly = load(config_file, fetch=fetch)
    click.echo(assembly.config_file)


@main.command(
    "build",
    help="Assemble the merged Zensical project and build it with `zensical build`.",
    epilog="\b\nOther options are passed to `zensical build`, e.g.:\n"
    "  -c, --clean  Clean the Zensical build cache.\n"
    "See `zensical build --help`.",
    context_settings=PASS_THROUGH,
)
@project_options
@click.option("-s", "--strict", is_flag=True, help="Abort on zmerge or Zensical warnings.")
@zensical_arguments
def build_command(config_file: Path, fetch: bool, strict: bool, zensical_args: tuple[str, ...]) -> None:
    """Assemble the merged project and build it with ``zensical build``.

    Raises:
        CliError: If --strict is set and zmerge warns.
    """
    site, assembly = load(config_file, fetch=fetch)
    if strict and assembly.warnings:
        raise CliError("aborted because --strict is set")
    command = [sys.executable, "-m", "zensical", "build", "--config-file", str(assembly.config_file)]
    command += ["--strict"] * strict + list(zensical_args)
    try:
        subprocess.run(command, cwd=site.root, check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)


@main.command(
    "serve",
    help="Serve the merged site with `zensical serve` and re-assemble it when a project changes.",
    epilog="\b\nOther options are passed to `zensical serve`, e.g.:\n"
    "  -a, --dev-addr IP:PORT  IP address and port (default: localhost:8000).\n"
    "  -o, --open              Open the preview in the default browser.\n"
    "See `zensical serve --help`.",
    context_settings=PASS_THROUGH,
)
@project_options
@zensical_arguments
def serve_command(config_file: Path, fetch: bool, zensical_args: tuple[str, ...]) -> None:
    """Serve the merged site with ``zensical serve`` and re-assemble it on changes.

    Raises:
        CliError: If the site can't be merged.
    """
    try:
        sys.exit(serve(config_file, list(zensical_args), update=fetch))
    except ZmergeError as e:
        raise CliError(str(e)) from e

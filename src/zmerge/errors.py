"""Errors raised by zmerge and how they are reported."""

import click


class ZmergeError(Exception):
    """Raised for invalid configurations and failed merges."""


def warn(message: str) -> None:
    """Report a warning on stderr with a yellow label."""
    click.echo(f"{click.style('zmerge: warning:', fg='yellow')} {message}", err=True)


def error(message: str) -> None:
    """Report an error on stderr with a red label."""
    click.echo(f"{click.style('zmerge: error:', fg='red')} {message}", err=True)

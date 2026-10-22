# zmerge 📚

[![PyPI](https://img.shields.io/pypi/v/zmerge)](https://pypi.org/project/zmerge/)
[![Test](https://github.com/KarelZe/zmerge/actions/workflows/test.yml/badge.svg)](https://github.com/KarelZe/zmerge/actions/workflows/test.yml)
[![Docs](https://img.shields.io/badge/docs-zensical-blue)](https://karelze.github.io/zmerge/)

`zmerge` merges the documentation of multiple [Zensical](https://zensical.org/) projects into one site with working
links, a single navigation and one global search. It fills the gap left by the
[mkdocs-monorepo-plugin](https://github.com/backstage/mkdocs-monorepo-plugin) until Zensical ships
[an official solution](https://github.com/zensical/backlog/issues/22).

> [!WARNING]
> zmerge is in early development and does not merge anything yet.

## Installation

```bash
uv tool install zmerge
```

## How it works

zmerge needs no custom Zensical. It assembles the documentation of all projects into a single, regular Zensical
project and builds it once with `zensical build`, so links can be validated across projects and the search index
covers every page.

## Development

```bash
uv sync
uv run pytest
uv run prek run --all-files
uv run zensical serve
```

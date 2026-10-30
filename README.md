# zmerge ☂️

[![PyPI](https://img.shields.io/pypi/v/zmerge)](https://pypi.org/project/zmerge/)
[![Test](https://github.com/KarelZe/zmerge/actions/workflows/test.yml/badge.svg)](https://github.com/KarelZe/zmerge/actions/workflows/test.yml)
[![Docs](https://img.shields.io/badge/docs-zensical-blue)](https://karelze.github.io/zmerge/)

`zmerge` merges the documentation of multiple [Zensical](https://zensical.org/) projects into one site with working
links, a single navigation and one global search. It fills the gap left by the
[mkdocs-monorepo-plugin](https://github.com/backstage/mkdocs-monorepo-plugin) until Zensical ships
[an official solution](https://github.com/zensical/backlog/issues/22).

- **No custom Zensical, no plugins.** zmerge assembles one regular Zensical project and builds it with `zensical build`.
- **One site.** One navigation, one search index and one link check across all projects.
- **Links that work everywhere.** Link between projects with their published URLs; zmerge turns them into validated
  relative links.
- **Per-project settings.** zmerge merges the markdown extensions, plugins, mkdocstrings options and snippets of every
  project.
- **Local or git, TOML or YAML.** Include projects from local paths or git repositories, configured with a
  `zensical.toml` or an `mkdocs.yml`.
- **Fast.** Hardlinks instead of copies, incremental re-assembly in milliseconds and live previews with `zmerge serve`.

## Installation

```bash
uv tool install zmerge --with mkdocstrings-python  # add the extensions and plugins your projects use
```

`zm` is a short alias of `zmerge`, e.g. `zm serve`.

## Quick start

Create an umbrella project, the Zensical project that hosts the merged site, and include projects in its `nav`:

```toml
[project]
site_name = "My projects"
site_url = "https://example.github.io/"
nav = [
  { Home = "index.md" },
  { lev = "!include ../lev/zensical.toml" },
  { Typer = "!include git+https://github.com/fastapi/typer.git" },
]

[project.markdown_extensions.admonition]
[project.markdown_extensions.toc]
permalink = true
```

Build or preview the merged site:

```bash
zmerge build --strict
zmerge serve
```

zmerge generates `.zmerge/` and `.zmerge.toml` next to the umbrella configuration. Keep `.zmerge.toml` out of git:

```bash
echo .zmerge.toml >> .gitignore
```

Read the [documentation](https://karelze.github.io/zmerge/) for the configuration, links between projects and
[limitations](https://karelze.github.io/zmerge/limitations/). The docs are built with zmerge themselves: their
[example](https://karelze.github.io/zmerge/example/lev/) merges lev and Typer from GitHub, see
[`zensical.toml`](https://github.com/KarelZe/zmerge/blob/main/zensical.toml).

## Development

```bash
uv sync
uv run pytest
uv run prek run --all-files
uv run zmerge serve
```

> [!WARNING]
> zmerge is not affiliated with the Zensical project.

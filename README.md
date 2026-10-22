# zmerge 📚

[![PyPI](https://img.shields.io/pypi/v/zmerge)](https://pypi.org/project/zmerge/)
[![Test](https://github.com/KarelZe/zmerge/actions/workflows/test.yml/badge.svg)](https://github.com/KarelZe/zmerge/actions/workflows/test.yml)
[![Docs](https://img.shields.io/badge/docs-zensical-blue)](https://karelze.github.io/zmerge/)

`zmerge` merges the documentation of multiple [Zensical](https://zensical.org/) projects into one site with working
links, a single navigation and one global search. It fills the gap left by the
[mkdocs-monorepo-plugin](https://github.com/backstage/mkdocs-monorepo-plugin) until Zensical ships
[an official solution](https://github.com/zensical/backlog/issues/22).

> [!NOTE]
> zmerge is not affiliated with the Zensical project. It is purely meant as a temporary solution until Zensical ships
> official support for merging projects, tracked in [zensical/backlog#22](https://github.com/zensical/backlog/issues/22).

- **No custom Zensical, no plugins.** zmerge assembles one regular Zensical project and builds it with `zensical build`.
- **One site.** One navigation, one global search, one link check across all projects.
- **Links that work everywhere.** Links between projects use the projects' published URLs and are rewritten into
  validated relative links when merging.
- **Per-project settings.** Markdown extensions, plugins, mkdocstrings options and snippets of every project are merged.
- **Local or git.** Include projects from local paths or straight from git repositories.
- **Fast.** Hardlinks instead of copies, incremental re-assembly in a few milliseconds, and `zmerge serve` for live
  previews.

## Installation

```bash
uv tool install zmerge --with mkdocstrings-python  # mkdocstrings-python only if you render API docs
```

## Quick start

Include other projects in the `nav` of an umbrella project's `zensical.toml`, just like with the
mkdocs-monorepo-plugin:

```toml
[project]
site_name = "My projects"
site_url = "https://example.github.io/"
nav = [
  { Home = "index.md" },
  { lev = "!include ../lev/zensical.toml" },
  { dame = "!include git+https://github.com/KarelZe/dame-rs.git" },
]
```

Then build or preview the merged site:

```bash
zmerge build --strict
zmerge serve
```

Add `.zmerge/` and `.zmerge.toml` to your `.gitignore`. See the [documentation](https://karelze.github.io/zmerge/) for
the configuration, linking between projects and [limitations](https://karelze.github.io/zmerge/limitations/), and
[examples/karelze](examples/karelze) for a complete umbrella site.

## Development

```bash
uv sync
uv run pytest
uv run prek run --all-files
uv run zensical serve
```

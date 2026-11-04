# zmerge

`zmerge` merges the documentation of multiple [Zensical](https://zensical.org/) projects into one site with a single
navigation, one search index and links that are validated across projects. It fills the gap left by the
[mkdocs-monorepo-plugin](https://github.com/backstage/mkdocs-monorepo-plugin) until Zensical ships
[an official solution](https://github.com/zensical/backlog/issues/22).

!!! warning

    zmerge is not affiliated with the Zensical project.

## Installation

```bash
uv tool install zmerge
```

Add the markdown extensions and plugins your projects use with `--with`, e.g. `--with mkdocstrings-python` to render
API docs with [mkdocstrings](https://mkdocstrings.github.io/).

## Quick start

Create an umbrella project, a regular Zensical project that hosts the merged site, and include your projects in its
`nav`:

```toml
[project]
site_name = "My projects"
site_url = "https://example.github.io/"
nav = [
  { Home = "index.md" },
  { lev = "!include ../lev/zensical.toml" },
  { Typer = "!include git+https://github.com/fastapi/typer.git" },
]

[project.theme]
features = ["navigation.indexes"]

[project.markdown_extensions.admonition]
[project.markdown_extensions.toc]
permalink = true
```

Build the merged site into `site/`, or preview it:

```bash
zmerge build --strict
zmerge serve
```

zmerge writes the merged project to `.zmerge.toml` and `.zmerge/` and regenerates both on every run. Don't edit them:
your changes are lost, and editing a hardlinked file in `.zmerge/docs/` changes your original. Keep `.zmerge.toml` out
of git; `.zmerge/` contains its own `.gitignore`:

```bash
echo .zmerge.toml >> .gitignore
```

Next, see how to [include projects](configuration.md) and
[link between them](configuration.md#links-between-projects).

## Example

These docs are built with zmerge. The [example](https://karelze.github.io/zmerge/example/lev/) merges the docs of
[lev](https://github.com/KarelZe/lev) and [Typer](https://github.com/fastapi/typer) straight from GitHub, with their
API docs and code examples. See the [`zensical.toml`](https://github.com/KarelZe/zmerge/blob/main/zensical.toml).

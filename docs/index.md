# zmerge

`zmerge` merges the documentation of multiple [Zensical](https://zensical.org/) projects into one site with working
links, a single navigation and one global search. It fills the gap left by the
[mkdocs-monorepo-plugin](https://github.com/backstage/mkdocs-monorepo-plugin) until Zensical ships
[an official solution](https://github.com/zensical/backlog/issues/22).

!!! warning

    zmerge is not affiliated with the Zensical project. It is purely meant as a temporary solution until Zensical ships
    official support for merging projects, tracked in [zensical/backlog#22](https://github.com/zensical/backlog/issues/22).

## Installation

```bash
uv tool install zmerge
```

Add the markdown extensions and plugins your projects use with `--with`, e.g. `--with mkdocstrings-python` to render
API docs with [mkdocstrings](https://mkdocstrings.github.io/).

## Quick start

Create an umbrella project, a regular Zensical project that hosts the merged site, and include other projects in its
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

[project.markdown_extensions.admonition]
[project.markdown_extensions.toc]
permalink = true
```

Build the merged site into `site/`, or preview it with live re-assembly:

```bash
zmerge build --strict
zmerge serve
```

Keep the [generated](#generated-files) `.zmerge.toml` out of git; `.zmerge/` ignores itself:

```bash
echo .zmerge.toml >> .gitignore
```

!!! example

    These docs are built with zmerge. The [example](example/lev/index.md) merges the docs of
    [lev](https://github.com/KarelZe/lev) and [Typer](https://github.com/fastapi/typer) straight from GitHub, with
    their API docs and code examples. See the
    [`zensical.toml`](https://github.com/KarelZe/zmerge/blob/main/zensical.toml).

## How it works

1. zmerge reads the umbrella configuration and every included project, from local paths or git repositories.
2. It assembles one regular Zensical project from the docs and configurations of all projects.
3. It rewrites what would break in the merged site: links between projects, links out of a project's docs, and
   per-project mkdocstrings and snippets settings.
4. It builds the merged project once with `zensical build`. So there is one search index, and Zensical validates every
   link across projects.

### Generated files

zmerge writes the merged project next to the umbrella configuration:

- `.zmerge.toml`: the merged Zensical configuration.
- `.zmerge/docs/`: the docs of all projects below their prefixes, hardlinked to the originals where possible.
- `.zmerge/repos/`: projects fetched from git repositories.

These files are internal to zmerge. Inspect them to debug a build, but don't edit or commit them: zmerge overwrites
them on every run, and editing a hardlinked file in `.zmerge/docs/` changes the original.

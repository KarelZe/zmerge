# zmerge

`zmerge` merges the documentation of multiple [Zensical](https://zensical.org/) projects into one site with working
links, a single navigation and one global search. It fills the gap left by the
[mkdocs-monorepo-plugin](https://github.com/backstage/mkdocs-monorepo-plugin) until Zensical ships
[an official solution](https://github.com/zensical/backlog/issues/22).

## Installation

```bash
uv tool install zmerge
```

To render API docs with [mkdocstrings](https://mkdocstrings.github.io/), install `mkdocstrings-python` alongside:

```bash
uv tool install zmerge --with mkdocstrings-python
```

## Quick start

Create an umbrella project with a regular `zensical.toml` and include other projects in its `nav`, just like with the
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

[project.markdown_extensions.admonition]
[project.markdown_extensions.toc]
permalink = true
```

Build the merged site into `site/`:

```bash
zmerge build --strict
```

Or preview it, re-assembling it whenever a project changes:

```bash
zmerge serve
```

Add `.zmerge/` and `.zmerge.toml` to your `.gitignore`.

!!! example "Example"

    [examples/karelze](https://github.com/KarelZe/zmerge/tree/main/examples/karelze) merges the docs of
    [lev](https://github.com/KarelZe/lev) and [dame-rs](https://github.com/KarelZe/dame-rs) straight from GitHub.
    See the [result](https://karelze.github.io/zmerge/example/).

## How it works

zmerge needs no custom Zensical and no plugins:

1. It reads the umbrella configuration and every included project, from local paths or git repositories.
2. It assembles a single, regular Zensical project next to the umbrella configuration: `.zmerge/docs` holds the docs of
   all projects below their prefix (hardlinked, not copied), and `.zmerge.toml` holds the merged configuration and
   navigation.
3. It rewrites what wouldn't work in the merged site: links between projects, links leaving a project's docs, and
   mkdocstrings and snippets settings that differ between projects.
4. It builds the merged project once with `zensical build`. As it is one build, there is one search index, and
   Zensical validates every link across projects.

Re-assembling is incremental and takes a few milliseconds, so it adds next to nothing to a Zensical build.

## Next steps

- [Configuration](configuration.md): includes, prefixes, git sources and how project settings are merged.
- [Links](links.md): how to link between projects.
- [Command line](cli.md): all commands and options.
- [Migrating from mkdocs-monorepo-plugin](migrating.md).
- [Limitations](limitations.md): what's not supported (yet).

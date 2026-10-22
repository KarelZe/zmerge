# zmerge

`zmerge` merges the documentation of multiple [Zensical](https://zensical.org/) projects into one site with working
links, a single navigation and one global search. It fills the gap left by the
[mkdocs-monorepo-plugin](https://github.com/backstage/mkdocs-monorepo-plugin) until Zensical ships
[an official solution](https://github.com/zensical/backlog/issues/22).

!!! warning "Work in progress"

    zmerge is in early development and is not feature complete yet.

## Installation

```bash
uv tool install zmerge
```

## Usage

Create an umbrella project with a regular `zensical.toml` and include other projects in its `nav`, just like with the
mkdocs-monorepo-plugin:

```toml
[project]
site_name = "My projects"
nav = [
  { Home = "index.md" },
  { lev = "!include ../lev/zensical.toml" },
  { dame = "!include ../dame-rs" },  # a directory containing a zensical.toml works, too
]
```

Then build the merged site:

```bash
zmerge build --strict
```

Each project is mounted below a prefix derived from its nav title (`lev/`, `dame/`). Override it with a
`[zmerge.projects.<id>]` table, where `<id>` is the slug of the nav title:

```toml
[zmerge.projects.dame]
prefix = "engines/dame"
```

Projects without a `nav` get one generated from their folder structure. Includes can be nested.

`zmerge build` writes the merged project to `.zmerge.toml` and `.zmerge/` next to the umbrella configuration and builds
it with `zensical build`. Add both to your `.gitignore`. Use `zmerge assemble` to only write the merged project, e.g.
to run `zensical serve -f .zmerge.toml` yourself.

## Configuration of the projects

The umbrella configuration owns everything that affects the site as a whole, like `site_name`, `site_url`, `theme`,
`extra` and `validation`. From each project, zmerge takes what its pages need to render:

| Setting | Merge behaviour |
| --- | --- |
| `markdown_extensions` | Combined. The umbrella's extensions come first, followed by those only the projects use. |
| `plugins` | Combined, e.g. `search`, `tags` or `mkdocstrings`. |
| `mkdocstrings` handlers | `paths` of all projects are combined and rebased onto the umbrella. Other options are combined. |
| `extra_css`, `extra_javascript` | Local files are moved below the project prefix, duplicates are removed. |
| `exclude_docs`, `draft_docs`, `not_in_nav` | Patterns are anchored at the project prefix. |

If projects set different options for the same extension or plugin, the first one wins and zmerge prints a warning.
Zensical's default markdown extensions can't be combined with explicit ones, so define `markdown_extensions` in every
project, including the umbrella. `zmerge build --strict` treats zmerge's warnings like Zensical's and aborts.

!!! tip "API docs with mkdocstrings"

    Install `mkdocstrings-python` next to zmerge, e.g. `uvx --with mkdocstrings-python zmerge build`. Packages are
    found through the handler `paths` of each project (default: the project root). If a project relies on its package
    being installed instead, install it into the same environment or set `paths` in the project.

## Links

Links within a project keep working, because each project keeps its folder structure below its prefix. zmerge rewrites
two kinds of links:

- **Links between projects.** Link to another project with the absolute URL of its published site, e.g.
  `https://karelze.github.io/dame-rs/design/#opening-book`. The link works when the project is built on its own. When
  merged, zmerge turns every link into the `site_url` of the umbrella or a project into a relative link to the merged
  page, e.g. `../dame/design.md#opening-book`, so Zensical validates it, anchors included.
- **Links leaving a project's docs**, e.g. `../LICENSE`, become links to the file in the project's repository, built
  from `repo_url` and `edit_uri`.

Links in code blocks and inline code are left untouched.

## How it works

zmerge needs no custom Zensical. It assembles the documentation of all projects into a single, regular Zensical
project and builds it once with `zensical build`, so links can be validated across projects and the search index
covers every page.

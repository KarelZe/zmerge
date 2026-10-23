# Configuration

Configure zmerge in the umbrella project's `zensical.toml`.

## Including projects

Include a project with an `!include` entry in the `nav`. The nav title becomes the title of the project's section:

```toml
[project]
site_name = "My projects"
nav = [
  { Home = "index.md" },
  { lev = "!include ../lev/zensical.toml" },
  { Engines = [
    { dame = "!include ../dame-rs" },  # a directory containing a zensical.toml works, too
  ] },
  "!include ../tclf",  # without a title, the project's `site_name` is used
]
```

Paths are relative to the configuration file that contains the include. Projects can include other projects; their
prefixes are nested, e.g. `lev/core`.

A project's section uses the project's own `nav`. Without one, zmerge generates it from the folder structure like
Zensical does: index pages first, then pages and folders in alphabetical order.

## Prefixes

Each project's URLs start with its prefix. The prefix defaults to the project id, the slug of the nav title (or of the
`site_name`), e.g. `lev` or `api-reference`. To change it, add a `[zmerge.projects.<id>]` table to the configuration
file that contains the include:

```toml
[zmerge.projects.dame]
prefix = "engines/dame"
```

A prefix may have several segments of letters, digits, `.`, `_` and `-`. A segment must not start with `.` or be
`templates`, because Zensical ignores these directories.

## Projects from git repositories

Include a project from its git repository with pip's syntax:

```toml
nav = [
  { lev = "!include git+https://github.com/KarelZe/lev.git" },
  { dame = "!include git+https://github.com/KarelZe/dame-rs.git@main" },
  { docs = "!include git+https://github.com/me/mono.git@v1.0#subdirectory=packages/docs" },
]
```

The ref (branch, tag or commit) defaults to the default branch. `subdirectory` points to the folder containing the
`zensical.toml`. zmerge fetches repositories shallowly into `.zmerge/repos` and updates them on every run, using your
usual git credentials. Pass `--no-fetch` to reuse them, e.g. when offline.

## How project settings are merged

The umbrella project owns the settings of the site as a whole, like `site_name`, `site_url`, `theme`, `extra`,
`copyright` and `validation`. From each project, zmerge takes what its pages need to render:

| Setting | Merge behaviour |
| --- | --- |
| `markdown_extensions` | Combined. The umbrella's extensions come first, followed by those only projects use. |
| `plugins` | Combined, e.g. `search`, `tags` or `mkdocstrings`. |
| `mkdocstrings` handlers | `paths` of all projects are combined and rebased onto the umbrella project. Handler `options` that differ from the merged ones are written into the project's `:::` directives, so each project renders as when built on its own. |
| `pymdownx.snippets` | `base_path` of all projects are combined. Snippets resolve against the base paths of their project. |
| `mdx_include`, `markdown_include_variants` | `{! file !}` and `{* file *}` resolve against the project, as when it is built on its own. |
| `extra_css`, `extra_javascript` | Local paths get the project prefix; duplicates are removed. |
| `exclude_docs`, `draft_docs`, `not_in_nav` | Patterns are anchored at the project prefix. |

Options are combined key by key. If the umbrella project and the projects set different values for the same option of an
extension or plugin, the umbrella's value or else the first in nav order wins, and zmerge warns. `zmerge build --strict` aborts on zmerge's warnings, too.

!!! note "Define markdown extensions explicitly"

    Without `markdown_extensions`, Zensical enables a set of defaults, which zmerge can't combine with explicit
    extensions. Define `markdown_extensions` in the umbrella project and in every project; zmerge warns if one doesn't.

## API docs with mkdocstrings

[Install](index.md#installation) `mkdocstrings-python` alongside zmerge. mkdocstrings finds packages through each
project's handler `paths`, which default to the project root. If a project's package isn't there, install it into the
same environment or set `paths` in the project:

```toml
[project.plugins.mkdocstrings.handlers.python]
paths = ["python"]
```

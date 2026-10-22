# Configuration

zmerge is configured in the umbrella site's `zensical.toml`. Zensical ignores zmerge's additions, so the umbrella
configuration stays a valid Zensical configuration.

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

Paths are relative to the configuration file containing the include. Projects can include other projects, too; their
prefixes are nested, e.g. `lev/core`.

A project's own `nav` is used for its section. Projects without a `nav` get one generated from their folder structure,
like Zensical does: index pages first, then pages and folders in alphabetical order, with section titles derived from
folder names.

## Prefixes

Each project is mounted below a prefix, which becomes part of its URLs. It defaults to the slug of the nav title, e.g.
`lev/` or `api-reference/`. Override it with a `[zmerge.projects.<id>]` table, where `<id>` is the slug of the nav title:

```toml
[zmerge.projects.dame]
prefix = "engines/dame"
```

Prefixes may consist of several segments, but must not start with a `.` or be named `templates`, as Zensical ignores
these directories.

## Projects from git repositories

Include a project straight from its git repository, using the syntax known from pip:

```toml
nav = [
  { lev = "!include git+https://github.com/KarelZe/lev.git" },
  { dame = "!include git+https://github.com/KarelZe/dame-rs.git@main" },
  { docs = "!include git+https://github.com/me/mono.git@v1.0#subdirectory=packages/docs" },
]
```

The ref (branch, tag or commit) defaults to the default branch. `subdirectory` points to the folder containing the
`zensical.toml`. Repositories are fetched shallowly into `.zmerge/repos` and updated on every run; pass `--no-fetch` to
reuse them, e.g. when offline. `zmerge serve` only fetches at startup. git uses your usual credentials.

## How project settings are merged

The umbrella configuration owns everything that affects the site as a whole, like `site_name`, `site_url`, `theme`,
`extra`, `copyright` and `validation`. From each project, zmerge takes what its pages need to render:

| Setting | Merge behaviour |
| --- | --- |
| `markdown_extensions` | Combined. The umbrella's extensions come first, followed by those only the projects use. |
| `plugins` | Combined, e.g. `search`, `tags` or `mkdocstrings`. |
| `mkdocstrings` handlers | `paths` of all projects are combined and rebased onto the umbrella. Handler `options` that differ from the merged ones are written into the project's `:::` directives, so each project renders as when built on its own. |
| `pymdownx.snippets` | `base_path` of all projects are combined. Snippets are resolved against the base paths of their project. |
| `extra_css`, `extra_javascript` | Local files are moved below the project prefix, duplicates are removed. |
| `exclude_docs`, `draft_docs`, `not_in_nav` | Patterns are anchored at the project prefix. |

Options are combined key by key. If projects set different values for the same option of an extension or plugin, the
first one wins and zmerge prints a warning. `zmerge build --strict` treats zmerge's warnings like Zensical's and
aborts.

!!! note "Define markdown extensions explicitly"

    Without `markdown_extensions`, Zensical enables a set of defaults. These can't be combined with explicit
    extensions, so define `markdown_extensions` in the umbrella and in every project. zmerge warns if one doesn't.

## API docs with mkdocstrings

Install `mkdocstrings-python` next to zmerge, e.g. `uvx --with mkdocstrings-python zmerge build`. Packages are found
through the handler `paths` of each project, which default to the project root. If a project relies on its package
being installed instead, either install the package into the same environment or set `paths` in the project:

```toml
[project.plugins.mkdocstrings.handlers.python]
paths = ["python"]
```

## Generated files

zmerge writes the merged project next to the umbrella configuration:

- `.zmerge.toml`: the merged Zensical configuration. Don't edit it, zmerge overwrites it.
- `.zmerge/docs`: the merged docs.
- `.zmerge/repos`: projects fetched from git repositories.

Add both to your `.gitignore`. The site is built into the umbrella's `site_dir` (default: `site/`).

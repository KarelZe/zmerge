# Configuration

Configure zmerge in the umbrella project's `zensical.toml`, or in its [`mkdocs.yml`](#projects-with-an-mkdocsyml).

## Including projects

Include a project with an `!include` entry in the `nav`. Point it to the project's configuration file, its directory or
its git repository:

```toml
[project]
site_name = "My projects"
nav = [
  { Home = "index.md" },
  { lev = "!include ../lev/zensical.toml" },
  { Typer = "!include git+https://github.com/fastapi/typer.git" },
  "!include ../oterm",  # a directory, titled by the project's `site_name`
]
```

Paths are relative to the configuration file that contains the include. The nav title becomes the title of the
project's section, and its slug becomes the URL prefix: lev is served at `lev/`, "API Reference" at `api-reference/`.
Without a title, zmerge uses the project's `site_name`. Nav sections don't add to the prefix.

The section uses the project's own `nav`. Without one, zmerge generates it from the folder structure like Zensical does.
Projects can include other projects; their prefixes are nested, e.g. `lev/core`.

## Links between projects

Links within a project keep working. To link to another project, use the absolute URL of its published site:

```md
Start with the [simplest example](https://typer.tiangolo.com/tutorial/first-steps/#the-simplest-example).
```

The link works when the project is built on its own. When merging, zmerge rewrites it into a relative link to the merged
page, and Zensical validates it, anchors included:

```md
Start with the [simplest example](../typer/tutorial/first-steps.md#the-simplest-example).
```

zmerge rewrites links that point into the `site_url` of the umbrella project or an included project. Set `site_url` in
every project; zmerge warns about links into a project's site that match no merged page.

From the umbrella project's pages, link to projects with their published URL or their merged path, e.g.
`[lev](lev/index.md)`.

## Advanced configuration

### Prefixes

To change a project's prefix, add a `[zmerge.projects.<id>]` table to the configuration file that contains the include.
The id is the default prefix, the slug of the nav title or `site_name`:

```toml
[zmerge.projects.typer]
prefix = "tools/typer"
```

A prefix may have several segments of letters, digits, `.`, `_` and `-`. A segment must not start with `.` or be
`templates`, because Zensical ignores these directories. Prefixes must be unique, and zmerge fails if two files end up
at the same path, e.g. the umbrella's `docs/lev/index.md` and lev's index page.

### Git repositories

Include a project from its git repository with pip's syntax, optionally with a ref (branch, tag or commit) and the
project's folder or configuration file in the repository:

```toml
nav = [
  { Typer = "!include git+https://github.com/fastapi/typer.git@master" },
  { docs = "!include git+https://github.com/me/mono.git@v1.0#subdirectory=packages/docs" },
]
```

zmerge fetches repositories shallowly into `.zmerge/repos` with your usual git credentials and updates them on every
run. Pass `--no-fetch` to reuse them, e.g. when offline.

### Wildcard includes

A `*include` entry includes every local project matching a glob pattern, in alphabetical order and titled by their
`site_name`. Put it into a section, because it can't have a title of its own:

```toml
nav = [
  { Packages = ["*include ../packages/*/zensical.toml"] },
]
```

### Projects with an `mkdocs.yml`

Projects configured with an `mkdocs.yml` are included like any other, e.g. `!include ../typer/mkdocs.yml`. zmerge reads
them like Zensical does, including `INHERIT`, `!ENV` and Python tags. In a directory, zmerge looks for `zensical.toml`,
`mkdocs.yml` and `mkdocs.yaml`, in this order.

The umbrella project can use an `mkdocs.yml`, too. Build it with `zmerge build -f mkdocs.yml` and set zmerge's options
in its `zmerge` key:

```yaml
zmerge:
  projects:
    typer:
      prefix: tools/typer
```

### Links out of a project's docs

Relative links out of a project's `docs_dir`, e.g. to `../LICENSE`, would break in the merged site. zmerge turns them
into links to the project's repository, built from `repo_url` and the branch in `edit_uri` (GitHub or GitLab style):

```toml
[project]
repo_url = "https://github.com/KarelZe/lev"
edit_uri = "edit/main/docs/"
```

`[license](../LICENSE)` becomes `[license](https://github.com/KarelZe/lev/blob/main/LICENSE)`. Without `repo_url` and
`edit_uri`, zmerge leaves the link unchanged and warns.

### API docs with mkdocstrings

Install `mkdocstrings-python` alongside zmerge. mkdocstrings finds packages through each project's handler `paths`,
which default to the project root. If a project's package isn't there, install it into the same environment or set
`paths` in the project:

```toml
[project.plugins.mkdocstrings.handlers.python]
paths = ["python"]
```

## Merging configurations

The umbrella project owns the settings of the site as a whole, like `site_name`, `site_url`, `theme`, `extra` and
`validation`. From each project, zmerge takes what its pages need:

| Setting | Merge logic |
| --- | --- |
| `markdown_extensions`, `plugins` | Combined. The umbrella's extensions come first, followed by those only projects use. |
| `mkdocstrings` handlers | `paths` are combined and rebased onto the umbrella project. Handler `options` the umbrella sets, or all projects set alike, stay site-wide. Others are written into the project's `:::` directives, so it renders as when built on its own. |
| `pymdownx.snippets`, `mdx_include`, `markdown_include_variants` | Included files resolve against their project. |
| `extra_css`, `extra_javascript` | Local paths get the project prefix; duplicates are removed. zmerge warns about different math renderers or versions of one. |
| `exclude_docs`, `draft_docs`, `not_in_nav` | Patterns are anchored at the project prefix. |
| `watch` | Combined and rebased onto the umbrella project, see [`zmerge serve`](cli.md#zmerge-serve). |

Options of extensions and plugins are combined key by key and apply to all pages, because Zensical can't set them per
page. If projects set an option differently, or only some set it, the first value in nav order applies to all pages
and zmerge warns. Set the option in the umbrella project to decide and silence the warning. `zmerge build --strict`
aborts on these warnings.

!!! note "Define markdown extensions explicitly"

    Without `markdown_extensions`, Zensical enables a set of defaults, which zmerge can't combine with explicit
    extensions. Define `markdown_extensions` in the umbrella project and in every project; zmerge warns if one doesn't.

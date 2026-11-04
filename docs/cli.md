# Command line

`zmerge build` and `zmerge serve` are drop-in replacements for `zensical build` and `zensical serve`: options zmerge
doesn't know are passed to Zensical unchanged. `zm` is a short alias of `zmerge`, e.g. `zm serve`.

All commands accept these options:

| Option | Description |
| --- | --- |
| `-f`, `--config-file` | Umbrella `zensical.toml` or `mkdocs.yml`, default: `zensical.toml`. |
| `--no-fetch` | Reuse fetched git repositories instead of updating them. |

## `zmerge build`

Assemble the merged project and build it with `zensical build`.

```bash
zmerge build [-f CONFIG_FILE] [--no-fetch] [-s/--strict] [ZENSICAL_OPTIONS]
```

| Option | Description |
| --- | --- |
| `-s`, `--strict` | Abort on zmerge or Zensical warnings, e.g. broken links. |
| `-c`, `--clean` | Clean Zensical's build cache (passed to Zensical). |

## `zmerge serve`

Assemble the merged project, serve it with `zensical serve` and re-assemble it whenever the configuration or docs of a
project change. Git repositories are only fetched at startup.

```bash
zmerge serve [-f CONFIG_FILE] [--no-fetch] [ZENSICAL_OPTIONS]
```

| Option | Description |
| --- | --- |
| `-a`, `--dev-addr` | IP address and port, default: `localhost:8000` (passed to Zensical). |
| `-o`, `--open` | Open the preview in the default browser (passed to Zensical). |

The site also rebuilds when the mkdocstrings sources of a project or files included with snippets or includes change.
To watch other files, e.g. templates used by a macro, add them to the project's `watch` setting, relative to the
project:

```toml
[project]
watch = ["templates"]
```

## `zmerge assemble`

Write `.zmerge.toml` and `.zmerge/` without building, and print the path of `.zmerge.toml`. Use it to run Zensical
yourself:

```bash
zensical build -f "$(zmerge assemble)"
```

# Command line

`zm` is a short alias of `zmerge`, e.g. `zm serve`.

All commands accept these options:

| Option | Description |
| --- | --- |
| `-f`, `--config-file` | Umbrella `zensical.toml`, default: `zensical.toml`. |
| `--no-fetch` | Reuse fetched git repositories instead of updating them. |

`zmerge build` and `zmerge serve` are drop-in replacements for `zensical build` and `zensical serve`: all other options
are passed to Zensical unchanged.

## `zmerge build`

Assemble the merged project and build it with `zensical build`.

```bash
zmerge build [-f CONFIG_FILE] [--no-fetch] [-s/--strict] [ZENSICAL_OPTIONS]
```

| Option | Description |
| --- | --- |
| `-s`, `--strict` | Abort on zmerge or Zensical warnings, e.g. broken links. |

Common options passed to `zensical build`, see `zensical build --help` for all:

| Option | Description |
| --- | --- |
| `-c`, `--clean` | Clean Zensical's build cache. |

## `zmerge serve`

Assemble the merged project, serve it with `zensical serve` and re-assemble it whenever the configuration or docs of the
umbrella project or an included project change. Git repositories are only fetched at startup.

```bash
zmerge serve [-f CONFIG_FILE] [--no-fetch] [ZENSICAL_OPTIONS]
```

Common options passed to `zensical serve`, see `zensical serve --help` for all:

| Option | Description |
| --- | --- |
| `-a`, `--dev-addr` | IP address and port, default: `localhost:8000`. |
| `-o`, `--open` | Open the preview in the default browser. |

## `zmerge assemble`

Write the [generated files](index.md#generated-files) without building, and print the path of `.zmerge.toml`. Use it
to run Zensical yourself:

```bash
zensical build -f "$(zmerge assemble)"
```

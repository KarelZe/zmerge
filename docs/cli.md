# Command line

All commands accept these options:

| Option | Description |
| --- | --- |
| `-f`, `--config-file` | Umbrella `zensical.toml`, default: `zensical.toml`. |
| `--no-fetch` | Reuse fetched git repositories instead of updating them. |

## `zmerge build`

Assemble the merged project and build it with `zensical build`.

```bash
zmerge build [-f CONFIG_FILE] [--no-fetch] [-s/--strict] [-c/--clean]
```

| Option | Description |
| --- | --- |
| `-s`, `--strict` | Abort on zmerge or Zensical warnings, e.g. broken links. |
| `-c`, `--clean` | Clean Zensical's build cache. |

## `zmerge serve`

Assemble the merged project, serve it with `zensical serve` and re-assemble it whenever the configuration or docs of the
umbrella project or an included project change. Git repositories are only fetched at startup.

```bash
zmerge serve [-f CONFIG_FILE] [--no-fetch] [-a/--dev-addr IP:PORT] [-o/--open]
```

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

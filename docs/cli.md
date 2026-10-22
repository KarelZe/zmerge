# Command line

All commands read the umbrella configuration from `zensical.toml` in the working directory, unless `-f` is given.

## `zmerge build`

Assemble the merged project and build it with `zensical build`.

```bash
zmerge build [-f CONFIG_FILE] [--no-fetch] [-s/--strict] [-c/--clean]
```

| Option | Description |
| --- | --- |
| `-f`, `--config-file` | Umbrella configuration, default: `zensical.toml`. |
| `--no-fetch` | Reuse fetched git repositories instead of updating them. |
| `-s`, `--strict` | Abort on zmerge or Zensical warnings, e.g. broken links. |
| `-c`, `--clean` | Clean Zensical's build cache. |

## `zmerge serve`

Assemble the merged project, serve it with `zensical serve` and re-assemble it whenever the configuration or docs of the
umbrella site or a project change.

```bash
zmerge serve [-f CONFIG_FILE] [--no-fetch] [-a/--dev-addr IP:PORT] [-o/--open]
```

| Option | Description |
| --- | --- |
| `-a`, `--dev-addr` | IP address and port, default: `localhost:8000`. |
| `-o`, `--open` | Open the preview in the default browser. |

Git repositories are only fetched at startup.

## `zmerge assemble`

Only write the merged project (`.zmerge.toml` and `.zmerge/`) and print the path of the generated configuration, e.g.
to run Zensical yourself:

```bash
zensical build -f "$(zmerge assemble)"
```

# Migrating from mkdocs-monorepo-plugin

zmerge keeps the `!include` and `*include` syntax of the [mkdocs-monorepo-plugin](https://github.com/backstage/mkdocs-monorepo-plugin):

1. Point the `!include` entries to the projects' `zensical.toml`, `mkdocs.yml` or their directories.
2. Remove `monorepo` from the plugins.
3. Build with `zmerge build -f mkdocs.yml` instead of `mkdocs build`.

The umbrella project and the projects can keep their `mkdocs.yml`. To migrate them to `zensical.toml`, follow Zensical's
[migration guide](https://zensical.org/docs/setup/basics/) and drop `-f mkdocs.yml`.

```yaml
site_name: My projects
nav:
  - Home: index.md
  - lev: "!include ./lev/mkdocs.yml"
```

## Differences

| mkdocs-monorepo-plugin | zmerge |
| --- | --- |
| A project's `site_name` is its URL prefix. | The [prefix](configuration.md#prefixes) is the slug of the nav title, configurable with `[zmerge.projects.<id>] prefix`. Set it to the old `site_name` to keep URLs. |
| Nested includes are not supported. | Projects can include projects. |
| Links between projects use paths of the merged site, which break when a project is built on its own. | Links between projects use the projects' published URLs and are rewritten when merging. |
| Plugins and markdown extensions of projects are ignored. | They are merged, including per-project mkdocstrings options. |
| Files at the same path silently overwrite each other. | Collisions are errors. |
| Includes are local files. | Includes can be git repositories. |
| Per-project edit links. | Not supported yet, see [#9](https://github.com/KarelZe/zmerge/issues/9). |

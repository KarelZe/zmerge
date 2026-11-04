# Migrating from mkdocs-monorepo-plugin

zmerge keeps the `!include` and `*include` syntax of the
[mkdocs-monorepo-plugin](https://github.com/backstage/mkdocs-monorepo-plugin):

1. Remove `monorepo` from the plugins.
2. Build with `zmerge build -f mkdocs.yml` instead of `mkdocs build`.

```yaml
site_name: My projects
nav:
  - Home: index.md
  - lev: "!include ./lev/mkdocs.yml"
```

The projects can keep their `mkdocs.yml`. To migrate them to `zensical.toml`, follow Zensical's
[migration guide](https://zensical.org/docs/setup/basics/) and drop `-f mkdocs.yml`.

## Differences

- **URLs change.** The URL prefix of a project is the slug of its nav title, not its `site_name`. To keep the old URLs
  and the relative links between projects working, set each project's [prefix](configuration.md#prefixes) to its old
  path.
- **Links between projects can use published URLs.** Relative links to another project break when the project is built
  on its own. Links to the [published URL](configuration.md#links-between-projects) work in both.
- **Project settings apply.** Markdown extensions and plugins of projects are
  [merged](configuration.md#merging-configurations) instead of ignored.
- **Edit links** point to the umbrella repository ([#9](https://github.com/KarelZe/zmerge/issues/9)).

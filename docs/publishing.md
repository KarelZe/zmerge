# Publishing

zmerge builds a static site into `site/` next to the umbrella `zensical.toml`, so you can host it anywhere. This page
publishes it with [GitHub Pages](https://docs.github.com/en/pages) from the umbrella project's repository.

## Set up the repository

1. In the umbrella repository, open **Settings → Pages** and set **Source** to **GitHub Actions**.
2. Set `site_url` in the umbrella `zensical.toml` to the address of the site, e.g.
   `https://<user>.github.io/<repository>/`. zmerge needs it to recognize [links](links.md) into the merged site.
3. Add the workflow below as `.github/workflows/docs.yml`.

## Workflow

The workflow builds the merged site on every push and pull request and deploys it from `main`:

```yaml
name: docs

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:  # rebuild by hand
  schedule:
    - cron: "0 3 * * *"  # pick up changes in the included projects daily
  repository_dispatch:
    types: [docs]  # rebuild when an included project asks for it

permissions:
  contents: read

concurrency:
  group: pages-${{ github.ref }}
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1

      - uses: astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0

      - name: Build docs
        run: uvx zmerge build --strict

      - uses: actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9 # v5.0.0
        if: github.event_name != 'pull_request'
        with:
          path: site/

  deploy:
    needs: build
    if: github.event_name != 'pull_request'
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@368f82528645a54fb793d4d04e342629a3f51346 # v5.0.1
```

`--strict` fails the build on broken links between projects, so pull requests can't break the published site. If the
umbrella `zensical.toml` isn't at the root of the repository, pass it with `-f` and upload the `site/` next to it.

!!! tip "API docs"

    If projects render API docs with mkdocstrings, install the handler and the documented packages alongside zmerge,
    e.g. `uvx --with mkdocstrings-python --with my-package zmerge build --strict`. See
    [API docs with mkdocstrings](configuration.md#api-docs-with-mkdocstrings).

## Rebuilding when projects change

zmerge fetches projects from [git repositories](configuration.md#projects-from-git-repositories) on every build, so
each run publishes their latest docs. The workflow above rebuilds daily and on demand. To rebuild as soon as an included
project changes, send a `repository_dispatch` event from that project's workflow:

```yaml
- name: Rebuild the merged docs
  run: gh api repos/<user>/<umbrella>/dispatches -f event_type=docs
  env:
    GH_TOKEN: ${{ secrets.UMBRELLA_TOKEN }}
```

`UMBRELLA_TOKEN` is a fine-grained personal access token with write access to the **Contents** of the umbrella
repository. Scheduled and dispatched runs build the default branch.

## Private projects

The workflow's `GITHUB_TOKEN` can only read the umbrella repository. To include private repositories, create a token
with read access to their **Contents**, store it as a secret and let git use it before building:

```yaml
- name: Authenticate git
  run: git config --global url."https://x-access-token:${TOKEN}@github.com/".insteadOf "https://github.com/"
  env:
    TOKEN: ${{ secrets.DOCS_TOKEN }}
```

zmerge runs `git` with your git configuration, so includes like `git+https://github.com/<user>/<private>.git` then
work unchanged.

!!! warning

    GitHub Pages sites are public, even if the included repositories are private. Restricting access to a site
    requires GitHub Enterprise Cloud.

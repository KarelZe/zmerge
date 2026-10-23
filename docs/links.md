# Links

Links within a project keep working, because each project keeps its folder structure below its prefix. zmerge rewrites
links that would break in the merged site, so a project's docs build both on their own and merged.

## Links between projects

Link to another project with the absolute URL of its published site:

```md
Start with the [simplest example](https://typer.tiangolo.com/tutorial/first-steps/#the-simplest-example).
```

The link works when the project is built on its own. When merging, zmerge turns every link into the `site_url` of the
umbrella project or an included project into a relative link to the merged page:

```md
Start with the [simplest example](../typer/tutorial/first-steps.md#the-simplest-example).
```

Zensical then validates the link, anchors included. zmerge understands directory URLs (`first-steps/`), `.html`
URLs (`first-steps.html`), index pages and assets. It leaves a link into a project's site that matches no merged
page unchanged and warns.

!!! tip

    Set `site_url` in every project. zmerge leaves links to other sites under the umbrella's `site_url` unchanged,
    without a warning.

## Links out of a project's docs

Relative links out of a project's `docs_dir`, e.g. to `../LICENSE` or `../src/`, would resolve to unrelated files in
the merged site. zmerge turns them into links to the file in the project's repository, built from `repo_url` and the
branch in `edit_uri`:

```toml
[project]
repo_url = "https://github.com/KarelZe/lev"
edit_uri = "edit/main/docs/"
```

`[license](../LICENSE)` becomes `[license](https://github.com/KarelZe/lev/blob/main/LICENSE)`. zmerge supports GitHub
and GitLab (`-/edit/main/docs/`) style edit URIs. Without `repo_url` and `edit_uri`, it leaves the link unchanged and
warns.

## Links from the umbrella project

Link from the umbrella project's pages to project pages with their merged path, e.g. `[lev](lev/index.md)`, or with
absolute URLs as above.

## What is rewritten

zmerge rewrites the destinations of inline links, images and reference definitions in Markdown, but not inside code.
It skips pages excluded with `exclude_docs` in the umbrella project or a project, because Zensical doesn't build them.
Links in raw HTML and in snippets aren't rewritten yet, see [limitations](limitations.md).

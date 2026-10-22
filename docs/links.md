# Links

Links within a project keep working, because each project keeps its folder structure below its prefix. Links that
would break in the merged site are rewritten, so a project's docs build on their own **and** as part of the merged
site.

## Links between projects

Link to another project with the absolute URL of its published site:

```md
The engine uses an [opening book](https://karelze.github.io/dame-rs/design/#opening-book).
```

The link works when the project is built on its own. When merged, zmerge turns every link pointing into the `site_url`
of the umbrella site or a project into a relative link to the merged page:

```md
The engine uses an [opening book](../dame/design.md#opening-book).
```

As a result, the link stays within the merged site and Zensical validates it, anchors included. zmerge understands
directory URLs (`design/`), `.html` URLs (`design.html`), index pages and assets. If a link points into a project's site
but matches no merged page, zmerge leaves it unchanged and warns.

!!! tip

    Set `site_url` in every project. Links to sites under the umbrella's `site_url` that aren't part of the merge are
    left unchanged, without a warning.

## Links leaving a project's docs

Relative links pointing outside of a project's `docs_dir`, e.g. to `../LICENSE` or `../src/`, would resolve to unrelated
files in the merged site. zmerge turns them into links to the file in the project's repository, built from `repo_url`
and the branch in `edit_uri`:

```toml
[project]
repo_url = "https://github.com/KarelZe/lev"
edit_uri = "edit/main/docs/"
```

`[license](../LICENSE)` becomes `[license](https://github.com/KarelZe/lev/blob/main/LICENSE)`. GitHub and GitLab
(`-/edit/main/docs/`) style edit URIs are supported.

## Links from the umbrella site

The umbrella site's pages link to project pages with their merged path, e.g. `[lev](lev/index.md)`, or with absolute
URLs as above.

## What is rewritten

zmerge rewrites the destinations of inline links, images and reference definitions in Markdown. It leaves fenced code
blocks and inline code untouched. Links in raw HTML and in content included with snippets are not rewritten yet, see
[limitations](limitations.md).

# Limitations

These features aren't supported yet; the
[backlog](https://github.com/KarelZe/zmerge/issues?q=is%3Aissue+label%3Abacklog) tracks them:

- **Edit and view links** of project pages point to the umbrella repository, because Zensical has no per-page edit URL
  ([#9](https://github.com/KarelZe/zmerge/issues/9)).
- **Theme overrides, `extra` and analytics** of projects are ignored; only the umbrella's are used
  ([#10](https://github.com/KarelZe/zmerge/issues/10)). Projects with untitled nav sections, like Typer, need
  `navigation.indexes` in the umbrella's theme features; zmerge warns otherwise.
- **Conflicting JavaScript**, e.g. MathJax in one project and KaTeX in another, is loaded on every page. zmerge warns,
  but can't choose one for you ([#13](https://github.com/KarelZe/zmerge/issues/13)).
- **Markdown extensions apply to every page**, also to pages of projects that don't use them. Includes or macros of
  one project can change text in another ([#36](https://github.com/KarelZe/zmerge/issues/36)).
- **Links in snippets** aren't rewritten ([#14](https://github.com/KarelZe/zmerge/issues/14)).
- **Versioned docs** with mike ([#15](https://github.com/KarelZe/zmerge/issues/15)).

# Limitations

These features aren't supported yet; the
[backlog](https://github.com/KarelZe/zmerge/issues?q=is%3Aissue+label%3Abacklog) tracks them:

- **Edit and view links** of project pages point to the umbrella repository, because Zensical has no per-page edit URL
  ([#9](https://github.com/KarelZe/zmerge/issues/9)).
- **Theme overrides, `extra` and analytics** of projects are ignored; only the umbrella's are used
  ([#10](https://github.com/KarelZe/zmerge/issues/10)).
- **Conflicting JavaScript**, e.g. one project using MathJax and another KaTeX, is loaded on every page
  ([#13](https://github.com/KarelZe/zmerge/issues/13)).
- **Markdown extensions apply to every page**, also to pages of projects that don't use them. Includes or macros of
  one project can change text in another ([#36](https://github.com/KarelZe/zmerge/issues/36)).
- **Links in snippets and bare URLs** aren't rewritten ([#14](https://github.com/KarelZe/zmerge/issues/14)).
- **Relative links out of the umbrella's docs**, e.g. to `../LICENSE`, aren't rewritten and break
  ([#66](https://github.com/KarelZe/zmerge/issues/66)).
- **Versioned docs** with mike ([#15](https://github.com/KarelZe/zmerge/issues/15)).
- **`zmerge serve`** doesn't watch mkdocstrings sources and snippet files outside the docs
  ([#16](https://github.com/KarelZe/zmerge/issues/16)).
- **mkdocstrings handlers other than Python** can't restore option defaults per project
  ([#17](https://github.com/KarelZe/zmerge/issues/17)).

# Limitations

zmerge only bridges the gap until Zensical supports merging projects natively
([zensical/backlog#22](https://github.com/zensical/backlog/issues/22),
[#44](https://github.com/zensical/backlog/issues/44), [#110](https://github.com/zensical/backlog/issues/110)); then
zmerge will be retired ([#18](https://github.com/KarelZe/zmerge/issues/18)). These features aren't supported yet; the
[backlog](https://github.com/KarelZe/zmerge/issues?q=is%3Aissue+label%3Abacklog) tracks them:

- **Edit and view links** of project pages point to the umbrella repository, because Zensical has no per-page edit URL
  ([#9](https://github.com/KarelZe/zmerge/issues/9)).
- **Theme overrides, `extra` and analytics** of projects are ignored; only the umbrella's are used
  ([#10](https://github.com/KarelZe/zmerge/issues/10)).
- **Wildcard includes** like `*include ./projects/*/zensical.toml` ([#12](https://github.com/KarelZe/zmerge/issues/12)).
- **Conflicting JavaScript**, e.g. one project using MathJax and another KaTeX, is loaded on every page
  ([#13](https://github.com/KarelZe/zmerge/issues/13)).
- **Links in raw HTML and in snippets** aren't rewritten ([#14](https://github.com/KarelZe/zmerge/issues/14)).
- **Versioned docs** with mike ([#15](https://github.com/KarelZe/zmerge/issues/15)).
- **`zmerge serve`** doesn't watch mkdocstrings sources and snippet files outside the docs
  ([#16](https://github.com/KarelZe/zmerge/issues/16)).
- **mkdocstrings handlers other than Python** can't restore option defaults per project
  ([#17](https://github.com/KarelZe/zmerge/issues/17)).

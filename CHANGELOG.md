# Changelog

## [0.6.0](https://github.com/KarelZe/zmerge/compare/0.5.0...0.6.0) (2026-11-04)


### Features

* rewrite links in raw HTML like Zensical ✨ ([#68](https://github.com/KarelZe/zmerge/issues/68)) ([708fefa](https://github.com/KarelZe/zmerge/commit/708fefab498c34fcfc47c447d2581a19556cc632))
* watch project sources and snippet files in serve ✨ ([#80](https://github.com/KarelZe/zmerge/issues/80)) ([e2c7d57](https://github.com/KarelZe/zmerge/commit/e2c7d57f29ce946e9c41a74e851864759787df3c))


### Documentation

* leave links out of the umbrella's docs unchanged like Zensical 📝 ([#82](https://github.com/KarelZe/zmerge/issues/82)) ([0f1450b](https://github.com/KarelZe/zmerge/commit/0f1450b94d0307e3e1701d5f6128d070bef129b3)), closes [#66](https://github.com/KarelZe/zmerge/issues/66)

## [0.5.0](https://github.com/KarelZe/zmerge/compare/0.4.1...0.5.0) (2026-11-03)


### Features

* let the umbrella override extension and plugin options ✨ ([#76](https://github.com/KarelZe/zmerge/issues/76)) ([88722ba](https://github.com/KarelZe/zmerge/commit/88722baeb26ce16f9954bd41898ff199c1cf234d))
* warn about conflicting math renderers and library versions ✨ ([#72](https://github.com/KarelZe/zmerge/issues/72)) ([a1b4a08](https://github.com/KarelZe/zmerge/commit/a1b4a0807681303b61a10fb77e81186d0ec2626a)), closes [#13](https://github.com/KarelZe/zmerge/issues/13)


### Bug Fixes

* keep mkdocstrings handler defaults without knowing them 🐛 ([#74](https://github.com/KarelZe/zmerge/issues/74)) ([97041cd](https://github.com/KarelZe/zmerge/commit/97041cd867003de78600e97d34a978ef7b88c9f2))


### Documentation

* prefer generic mechanisms in agent guidelines 📝 ([#77](https://github.com/KarelZe/zmerge/issues/77)) ([e546d53](https://github.com/KarelZe/zmerge/commit/e546d53a69aacaa18ee697a969a7b24a1e182f5c))

## [0.4.1](https://github.com/KarelZe/zmerge/compare/0.4.0...0.4.1) (2026-10-30)


### Bug Fixes

* warn about untitled nav sections without navigation.indexes 🐛 ([#70](https://github.com/KarelZe/zmerge/issues/70)) ([3877a09](https://github.com/KarelZe/zmerge/commit/3877a09c640d523ef923a39a403eb5067fa9ba3a))

## [0.4.0](https://github.com/KarelZe/zmerge/compare/0.3.0...0.4.0) (2026-10-30)


### Features

* support wildcard includes ✨ ([#65](https://github.com/KarelZe/zmerge/issues/65)) ([b6f86db](https://github.com/KarelZe/zmerge/commit/b6f86dbe8b6b6ecb84f5e61341a7a524678fbc16))


### Bug Fixes

* address unsafe yaml.load vulnerability in mkdocs.py🔒  ([#53](https://github.com/KarelZe/zmerge/issues/53)) ([b513763](https://github.com/KarelZe/zmerge/commit/b513763ae3ff2cd593420410234ee6aa75b881e0))


### Performance

* optimize directory title regular expression compilation⚡  ([#50](https://github.com/KarelZe/zmerge/issues/50)) ([12455ae](https://github.com/KarelZe/zmerge/commit/12455ae9314016e5ca47250029219d0129e53a83))
* read each page once for link and directive rewrites ⚡ ([#64](https://github.com/KarelZe/zmerge/issues/64)) ([c160f3c](https://github.com/KarelZe/zmerge/commit/c160f3c049a526d198588e734dda8896601f71ab))

## [0.3.0](https://github.com/KarelZe/zmerge/compare/0.2.0...0.3.0) (2026-10-24)


### Features

* add zm as a short alias of zmerge ✨ ([#38](https://github.com/KarelZe/zmerge/issues/38)) ([ba5bfee](https://github.com/KarelZe/zmerge/commit/ba5bfee0054b8e99d9c36ec87cc4a4bc0895edd1))
* pass unknown options through to Zensical ✨ ([#39](https://github.com/KarelZe/zmerge/issues/39)) ([f5f99dc](https://github.com/KarelZe/zmerge/commit/f5f99dcbf4d98e9e25ab1275e31767277459ed85))

## [0.2.0](https://github.com/KarelZe/zmerge/compare/0.1.2...0.2.0) (2026-10-24)


### Features

* include projects configured with mkdocs.yml ✨ ([#33](https://github.com/KarelZe/zmerge/issues/33)) ([3a078e7](https://github.com/KarelZe/zmerge/commit/3a078e7aae5f1599885eca7e25cafe45c327ea09))
* resolve mdx_include and include-variants paths per project ✨ ([#34](https://github.com/KarelZe/zmerge/issues/34)) ([949192c](https://github.com/KarelZe/zmerge/commit/949192c1321a5628e3c14de9b6f887540075a2d4))


### Bug Fixes

* restore structured mkdocstrings defaults per project 🐛 ([#32](https://github.com/KarelZe/zmerge/issues/32)) ([94ad1e8](https://github.com/KarelZe/zmerge/commit/94ad1e896ae53879d7cd5f0c91db9d2e0de91cb7))
* skip pages excluded with exclude_docs when rewriting 🐛 ([#35](https://github.com/KarelZe/zmerge/issues/35)) ([e01f7bb](https://github.com/KarelZe/zmerge/commit/e01f7bb4c16b9e7713219c2edf3c3f3bc0e6e87b))


### Documentation

* build the docs with zmerge, merging lev and Typer 📝 ([#29](https://github.com/KarelZe/zmerge/issues/29)) ([200830f](https://github.com/KarelZe/zmerge/commit/200830f5cc2968136fe3c55650e063c4501d38e1))

## [0.1.2](https://github.com/KarelZe/zmerge/compare/0.1.1...0.1.2) (2026-10-22)


### Documentation

* use the umbrella emoji ☂️ ([#27](https://github.com/KarelZe/zmerge/issues/27)) ([e99a77d](https://github.com/KarelZe/zmerge/commit/e99a77d86a9772cc49a62cd0688eb59692770282))

## [0.1.1](https://github.com/KarelZe/zmerge/compare/0.1.0...0.1.1) (2026-10-22)


### Documentation

* tighten the docs and explain generated files 📝 ([3e0c9e0](https://github.com/KarelZe/zmerge/commit/3e0c9e0e6d269fc86603e39a1370be9ef6f66274))

## 0.1.0 (2026-10-22)


### Features

* assemble incrementally and add serve command ✨ ([680fb96](https://github.com/KarelZe/zmerge/commit/680fb9680449237cfb0b831452a34793fc178051))
* assemble merged docs tree and build it ✨ ([f1c41ac](https://github.com/KarelZe/zmerge/commit/f1c41ac176005a3b9f483d2a5303bc502bfa5653))
* include projects from git repositories ✨ ([2a592cf](https://github.com/KarelZe/zmerge/commit/2a592cf31b8880043c07220f298c270c15a4a9d4))
* keep mkdocstrings options and snippets per project ✨ ([864d72e](https://github.com/KarelZe/zmerge/commit/864d72e2c31110d11eaa10e0a97cf079c10eeb36))
* load umbrella and child configs ✨ ([3644160](https://github.com/KarelZe/zmerge/commit/3644160aef2c12f15d440b482aa90c49028a1e73))
* merge markdown extensions, plugins and assets of projects ✨ ([abd655d](https://github.com/KarelZe/zmerge/commit/abd655df1ca98f235d4796cb28639071206476e6))
* rewrite links between projects and out of the docs ✨ ([4ea6805](https://github.com/KarelZe/zmerge/commit/4ea68058602f080c533dc15d489ca61532c4c9e2))

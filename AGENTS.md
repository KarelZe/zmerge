# AGENTS.md

## Project Overview
`zmerge` merges the documentation of multiple Zensical projects into one site. It assembles the docs of all
child projects into a single, regular Zensical project and builds it once with `zensical build`, so links are
validated across projects and there is one global search index. It must work with an unmodified Zensical and only
bridges the gap until Zensical ships an official solution (https://github.com/zensical/backlog/issues/22).

Speed matters: prefer hardlinks over copies and only rewrite files that need changes.

## Environment Setup
- Python >= 3.11
- Install: `uv sync`

## Testing
- `uv run pytest`

## Documentation
- Serve locally: `uv run zensical serve`, then access http://localhost:8000

## Code Style
- `uv run ruff format .` and `uv run ruff check . --fix`
- Type check: `uv run ty check`
- Pre-commit hooks (via prek): `uv run prek install` once, then `uv run prek run --all-files`
- Google-style docstrings.

## Before Committing
- All tests pass
- `prek run --all-files` passes
- Commit message follows Conventional Commits with a trailing emoji:
  - `feat: … ✨`  `fix: … 🐛`  `perf: … ⚡`
  - `docs: … 📝`  `test: … ✅`  `style: … 💄`  `build: … 🔧`

## Releasing
- The version lives only in `pyproject.toml`.
- PRs are squash-merged, so the PR title becomes the commit on `main` and must be
  a conventional commit (checked by `.github/workflows/pr-title.yml`).
- release-please keeps a release PR open that bumps `pyproject.toml` and `CHANGELOG.md`.
  Merging it tags the release, creates the GitHub Release and publishes to PyPI.
- Never bump versions or push tags by hand. To rebuild an existing release, run
  the `release` workflow manually with its tag.

## Project Structure
- `src/zmerge/` — Python package
- `tests/` — pytest suite
- `docs/` — Zensical documentation source

## PR Guidelines
- Keep diffs small and focused
- Add or update tests for changed code paths
- Update `docs/` and `README.md` when behavior changes

## Permissions

**Allowed without asking**
- Read files, run tests, run linters and formatters
- Build the docs locally

**Ask first**
- Installing new packages
- Pushing to `main`
- Deleting files
- Modifying CI workflows or release configuration

# Agent Guidelines for exa-py

## Releases

Release Please owns versioning. Never edit versions or `CHANGELOG.md` by hand — the
versions in `pyproject.toml`, `setup.py`, and `uv.lock` are updated automatically
(see `release-please-config.json` and `.github/workflows/release-please.yml`).

- Use Conventional Commit titles (`feat:`, `fix:`, `chore:`, …); they determine the
  next version and the changelog entry.
- Merges to `master` keep a single Release PR up to date. Merging that PR creates the
  tag and GitHub Release, which triggers the PyPI publish job.

## Development

```bash
make test              # uv run pytest tests/
make test-unit         # tests/unit only
make test-integration  # tests/integration only
```

Run `uv lock` after changing dependencies (not for version changes).

## Docstrings and type hints

The reference documentation is the docstrings and type hints themselves.

### Docstrings
- All public methods should have Google-style docstrings with `Args`, `Returns`, and `Examples` sections

### Type Hints
- All parameters and return types should have proper type hints
- For Pydantic models, use `Field(description="...")` to document fields

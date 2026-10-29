# Contributing

The canonical guide is [`CONTRIBUTING.md`](../CONTRIBUTING.md).

The local loop is:

```bash
cd patcher && uv sync
uv run pytest -q
uv run ruff check src tests --select F
uv run patcher validate
```

Keep GitHub Actions pinned to commit SHAs, never run upstream code with
credentials, and make every dependency bump, skip, hold, override and VEX
decision visible in the generated report.

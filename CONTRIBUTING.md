# Contributing

How to change this repo safely: the local loop, then how to extend each part. Background is in
[docs/architecture.md](docs/architecture.md); open work is in [docs/roadmap.md](docs/roadmap.md).

## Local loop

```bash
cd patcher && uv sync               # Python 3.12 + dev dependencies
uv run pytest -q                    # unit tests (fixtures, no network)
uv run ruff check src tests --select F
uv run patcher validate             # every recipe, skip, VEX, state and inventory file
uv run patcher schema --out ../schema   # after changing models.py; CI fails on drift
cd ..

# the real thing, in the patcher image, as CI runs it (never pushes)
docker build -t patcher:dev patcher
scripts/patcher-docker.sh run dex --out out --skip-tests
```

- Changes to the pipeline need a unit test, and should go through at least one real run of an
  affected recipe.
- Report wording is part of the product: reviewers act on it. Keep reasons specific ("cooldown:
  v0.62.0 released 1 day ago"), never generic.

## Adding a project

Follow [the runbook](docs/runbook.md#adding-a-release-line-or-a-project): `patcher init`, resolve
the TODOs, run it, add the image to `inventory.yaml`. Start from the closest worked example in
[docs/recipes.md](docs/recipes.md#worked-examples) or [docs/examples/](docs/examples/README.md).

## Adding a bundled-binary component

A recipe with `mode: component` and an `artifact` build (copy `recipes/gomplate.yaml`), plus a
`components:` entry in each parent recipe that bundles it. Run the component on its own first
(`patcher run <component> --skip-build`), then the parent.

Jars of a Java distribution that an image unpacks (Maven's `lib/`, Kafka's `libs/`) aren't
components: set `bundledJars` on the image (see `recipes/maven.yaml` and
[docs/recipes.md](docs/recipes.md#bundled-jars)), with a smoke command that loads those jars.

## Adding an ecosystem

1. A row in `patcher/src/patcher/ecosystems.py`: Trivy types, lockfiles, toolchain fields, the 0.x
   rule. Scan mapping, overrides/holds keys, the malicious-package check, the planner and the retry
   rules read it.
2. The recipe model in `models.py` (`<Name>Eco`, added to the `Ecosystem` union).
3. The adapter in `adapters/<name>.py`, dispatched from `adapters/__init__.py`. Apply the bump with
   the ecosystem's own tool, verify that it landed in the lockfile, and return `Change`s for what
   landed and `Failure`s for what didn't. Use `needs-human:` for decisions the policy can't make.
4. Publish times in `releases.ReleaseAges._lookup`, so the 7-day rule applies to it.
5. Detection in `detect.py` (manifests, toolchain versions), so `patcher init` drafts it.
6. If built images carry its packages: the target mapping in `pipeline.image_derived`.
7. Tests in `patcher/tests/test_languages.py` (adapter edits, planner mapping), then a real run.

## Adding a test framework

Today a framework touches five places (a registry is on the [roadmap](docs/roadmap.md)):
1. `models.Tests.framework` (the literal).
2. In `tests_runner.py`: `FAILURE_PATTERNS`, a `render_skips` branch, and a `_stable_id` branch.
   Failing-test ids must be identical between the patched and the baseline run: no durations,
   counts or numbering.
3. `toolchain.FRAMEWORK_FIELDS`.
4. `onboarding.infer_tests`, if `patcher init` can recognize it.
5. Tests in `test_languages.py` (skip rendering) and `test_security.py` (failure ids).

## Rules that keep the pipeline trustworthy

- **Pin everything to versions at least 14 days old:**
  - Dockerfile downloads, by version and sha256; `tool-pins.yml` maintains them.
  - GitHub Actions, by commit SHA.
  - Tools run with `go run …@vX` or `uvx --from pkg==X`.
- **Never run upstream code with credentials.** The patch job has none. See the roadmap for the
  release job.
- **Upstream commands run with `clean=True`** (no `PATCHER_*`, `TRIVY_*` or `COPA_*` variables),
  and anything long-running gets a timeout.
- **Nothing is applied silently:** every bump, skip, hold, override and VEX decision appears in the
  PR report with its reason.

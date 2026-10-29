import datetime as dt
import json

import yaml

from patcher import inventory, onboarding
from patcher.config import Repo
from patcher.models import LineState, Recipe, ReleasedImage, State


def test_tag_pattern():
    assert onboarding.tag_pattern("v4.1.6") == r"^v4\.1\.\d+$"
    assert onboarding.tag_pattern("1.3.0") == r"^1\.3\.\d+$"
    assert onboarding.tag_pattern("release-2.0.9") == r"^release\-2\.0\.\d+$"


def test_draft_from_checkout_is_a_valid_recipe(tmp_path):
    src = tmp_path / "src"
    (src / "ui").mkdir(parents=True)
    (src / ".github" / "workflows").mkdir(parents=True)
    (src / "go.mod").write_text("module github.com/o/app\n\ngo 1.26.10\n")
    (src / "Makefile").write_text("test:\n\tgo test ./...\n")
    (src / "ui" / "package.json").write_text(json.dumps({"packageManager": "pnpm@11.9.0", "devDependencies": {"jest": "1"}}))
    (src / "ui" / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n")
    (src / "Dockerfile").write_text("FROM golang:1.26 AS builder\nFROM alpine:3.24 AS controller\nFROM alpine:3.24 AS cli\n")
    (src / "README.md").write_text("docker pull quay.io/o/controller:latest\n")
    (src / ".github" / "workflows" / "ci.yml").write_text("jobs:\n  t:\n    steps:\n      - run: make test-unit\n")
    text = onboarding.draft(src, "app", "o/app", "v4.1.6")
    data = yaml.safe_load(text)
    r = Recipe.model_validate(data)  # the draft must validate as-is
    assert r.source.lines[0].tagPattern == r"^v4\.1\.\d+$"
    assert [e.type for e in r.ecosystems] == ["gomod", "pnpm", "dockerfile"]
    assert r.toolchain.go == "1.26" and r.toolchain.pnpm == "11.9.0"
    assert r.tests.framework == "go" and "{{skip_args}}" in r.tests.command
    assert [(i.name, i.target, i.upstream) for i in r.build.images] == [("controller", "controller", "quay.io/o/controller"),
                                                                        ("cli", "cli", None)]
    assert "make test-unit" in text  # CI hint kept as a comment


def test_image_only_draft_validates():
    data = yaml.safe_load(onboarding.draft_image_only("vendor-app", "docker.io/vendor/app", "2.4.1", ["linux/amd64"]))
    r = Recipe.model_validate(data)
    assert r.mode == "image-only" and r.build.images[0].upstream == "docker.io/vendor/app"


def _repo(tmp_path, recipes: dict[str, dict], images: list[str], states: dict[str, State]) -> Repo:
    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "_global.yaml").write_text("registry: ghcr.io/me\n")
    for name, body in recipes.items():
        (tmp_path / "recipes" / f"{name}.yaml").write_text(yaml.safe_dump({"name": name, **body}))
    (tmp_path / "inventory.yaml").write_text(yaml.safe_dump({"images": [{"image": i} for i in images]}))
    (tmp_path / "state").mkdir()
    repo = Repo(tmp_path)
    for name, st in states.items():
        repo.save_state(name, st)
    return repo


def test_coverage_statuses(tmp_path):
    recipes = {"dex": {"source": {"repo": "dexidp/dex", "lines": [{"name": "v2", "tagPattern": r"^v2\.\d+\.\d+$"}]},
                       "build": {"images": [{"name": "dex", "upstream": "ghcr.io/dexidp/dex"},
                                            {"name": "dex", "id": "dex-distroless", "upstream": "ghcr.io/dexidp/dex",
                                             "upstreamTag": "{{tag}}-distroless"}]}},
               "trivy": {"source": {"repo": "aquasecurity/trivy", "lines": [{"tagPattern": r"^v0\.76\.\d+$"}]},
                         "build": {"images": [{"name": "trivy", "upstream": "ghcr.io/aquasecurity/trivy", "upstreamTag": "{{version}}"}]}}}
    now = dt.datetime(2026, 10, 28, tzinfo=dt.timezone.utc)
    st = State(lines={"v2": LineState(upstreamTag="v2.46.1", commit="c", revision=2, releasedAt=now, images=[
        ReleasedImage(name="dex", ref="ghcr.io/me/dex:v2.46.1-patched.2", digest="sha256:aa", knownFixable=["x|y|z"]),
        ReleasedImage(name="dex-distroless", ref="ghcr.io/me/dex:v2.46.1-distroless-patched.2", digest="sha256:bb")])})
    repo = _repo(tmp_path, recipes, ["ghcr.io/dexidp/dex:v2.46.1", "ghcr.io/dexidp/dex:v2.45.0-distroless",
                                     "ghcr.io/aquasecurity/trivy:0.76.1", "ghcr.io/aquasecurity/trivy:0.70.0",
                                     "docker.io/library/nginx:1.27"], {"dex": st})
    rows = {r.image: r for r in inventory.coverage(repo)}
    assert rows["ghcr.io/dexidp/dex:v2.46.1"].status == "patched"
    assert rows["ghcr.io/dexidp/dex:v2.46.1"].use == "ghcr.io/me/dex@sha256:aa"
    assert rows["ghcr.io/dexidp/dex:v2.45.0-distroless"].status == "newer release patched"
    assert rows["ghcr.io/aquasecurity/trivy:0.76.1"].status == "pending first release"
    assert rows["ghcr.io/aquasecurity/trivy:0.70.0"].status == "version not tracked"
    assert rows["docker.io/library/nginx:1.27"].status == "no recipe"
    assert "**1** no recipe" in inventory.render_markdown(list(rows.values()))


def test_python_test_draft_uses_a_project_venv(tmp_path):
    src = tmp_path / "src"
    (src / ".github" / "workflows").mkdir(parents=True)
    (src / "pyproject.toml").write_text('[project]\nname = "app"\nrequires-python = ">=3.12"\n'
                                        '[project.optional-dependencies]\ntest = ["pytest"]\n')
    (src / "requirements.txt").write_text("flask==3.1.0\n")
    (src / ".github" / "workflows" / "test.yml").write_text(
        "# runs the pytest tests in CI\njobs:\n  pytest:\n    steps:\n      - name: Run pytest\n"
        "        run: |\n          pytest -k unit --maxfail=2 tests\n")
    data = yaml.safe_load(onboarding.draft(src, "app", "o/app", "1.2.3"))
    tests = Recipe.model_validate(data).tests
    assert tests.framework == "pytest"
    assert tests.setup == ["uv venv --seed .venv && uv pip install --python .venv -r requirements.txt && "
                           "uv pip install --python .venv -e '.[test]'"]
    assert tests.command.startswith('PATH="$PWD/.venv/bin:$PATH" python -m pytest')
    assert onboarding.ci_test_hints(src) == ["pytest -k unit --maxfail=2 tests"]  # no comments, keys or step names
    (src / "uv.lock").write_text("version = 1\n")
    assert onboarding.infer_tests(src, [{"type": "python", "dirs": ["."]}])["setup"] == ["uv sync --frozen --all-extras --all-groups"]


def test_default_target_and_sibling_images(tmp_path):
    src = tmp_path / "src"
    (src / "ui").mkdir(parents=True)
    (src / "go.mod").write_text("module github.com/o/rollouts\n\ngo 1.26\n")
    (src / "ui" / "package.json").write_text(json.dumps({"packageManager": "pnpm@11.9.0"}))
    (src / "ui" / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n")
    (src / "Dockerfile").write_text("FROM --platform=$BUILDPLATFORM golang:1.26 AS builder\n"
                                    "FROM --platform=$BUILDPLATFORM docker.io/library/node:22 AS rollouts-ui\n"
                                    "FROM --platform=$BUILDPLATFORM builder AS rollouts-build\n"
                                    "COPY --from=rollouts-ui /src/dist /dist\n"
                                    "FROM gcr.io/distroless/static-debian12 AS kubectl-rollouts\n"
                                    "COPY --from=rollouts-build /bin/kubectl-rollouts /bin/\n"
                                    "FROM gcr.io/distroless/static-debian12\n"
                                    "COPY --from=rollouts-build /bin/rollouts /bin/\n")
    r = Recipe.model_validate(yaml.safe_load(onboarding.draft(src, "rollouts", "o/rollouts", "v1.10.1", "quay.io/o/rollouts:v1.10.0")))
    assert [(i.name, i.target, i.upstream) for i in r.build.images] == [
        ("rollouts", None, "quay.io/o/rollouts"),                   # the unnamed final stage = default target
        ("kubectl-rollouts", "kubectl-rollouts", "quay.io/o/kubectl-rollouts")]
    assert r.toolchain.node == "22"  # from the UI builder stage: nothing else declares it


def test_example_recipes_stay_valid():
    from pathlib import Path

    examples = Path(__file__).resolve().parents[2] / "docs" / "examples" / "recipes"
    names = sorted(p.stem for p in examples.glob("*.yaml"))
    assert names == ["jupyterhub", "k8s-hub-vendor", "spring-petclinic", "z2jh-hub"]
    for p in examples.glob("*.yaml"):
        r = Recipe.model_validate(yaml.safe_load(p.read_text()))
        assert r.name == p.stem

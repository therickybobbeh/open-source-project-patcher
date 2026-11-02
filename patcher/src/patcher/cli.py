"""`patcher` command line. Every GitHub Actions job is a thin wrapper around one of these."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from pydantic import ValidationError

from . import pipeline
from .build import native_platform
from .config import Repo, find_repo_root, line_key, load_model
from .models import GlobalConfig, Inventory, LineState, Recipe, SkipFile, State, VexFile
from .proc import log

app = typer.Typer(add_completion=False, no_args_is_help=True, help=__doc__)

RepoOpt = typer.Option(None, "--repo", help="support-images checkout (default: search upward from cwd)")


def _repo(root: Optional[Path]) -> Repo:
    return Repo(root.resolve() if root else find_repo_root())


def _emit(data) -> None:
    typer.echo(json.dumps(data, indent=2, default=str))


@app.command()
def validate(repo: Optional[Path] = RepoOpt) -> None:
    """Validate _global.yaml, every recipe, skip file, VEX file and state file."""
    r = _repo(repo)
    errors = 0
    checks = [(r.recipes_dir / "_global.yaml", GlobalConfig)]
    checks += [(p, Recipe) for p in r.recipe_paths()]
    checks += [(p, SkipFile) for p in sorted((r.root / "skips").glob("*.yaml"))]
    checks += [(p, VexFile) for p in sorted((r.root / "vex").glob("*.yaml"))]
    checks += [(p, State) for p in sorted((r.root / "state").glob("*.yaml"))]
    checks += [(p, LineState) for p in sorted((r.root / "state").glob("*/*.yaml"))]
    if (r.root / "inventory.yaml").exists():
        checks.append((r.root / "inventory.yaml", Inventory))
    names = {p.stem for p in r.recipe_paths()}
    for path, model in checks:
        try:
            load_model(path, model)
            if model is Recipe:
                r.load_recipe(path.stem)  # merge with _global too
            if model in (SkipFile, VexFile, State) and path.stem not in names and path.name != "inventory.yaml":
                raise ValueError(f"no recipe named {path.stem!r}")
            if model is LineState and path.parent.name not in names:
                raise ValueError(f"no recipe named {path.parent.name!r}")
            typer.echo(f"ok    {path.relative_to(r.root)}")
        except (ValidationError, ValueError) as e:
            errors += 1
            typer.echo(f"FAIL  {path.relative_to(r.root)}\n{e}", err=True)
    for d in sorted((r.root / "patches").glob("*/")):
        if d.name not in names:
            errors += 1
            typer.echo(f"FAIL  patches/{d.name}: no recipe named {d.name!r}", err=True)
    raise typer.Exit(1 if errors else 0)


@app.command()
def schema(out: Path = typer.Option(Path("schema"), help="Directory for the JSON schemas")) -> None:
    """Write JSON schemas for recipes, skip files, VEX files and state (for editor validation)."""
    out.mkdir(parents=True, exist_ok=True)
    for name, model in [("global", GlobalConfig), ("recipe", Recipe), ("skips", SkipFile), ("vex", VexFile), ("state", LineState),
                        ("inventory", Inventory)]:
        (out / f"{name}.schema.json").write_text(json.dumps(model.model_json_schema(), indent=2) + "\n")
        typer.echo(f"wrote {out / f'{name}.schema.json'}")


@app.command()
def plan(
    recipe: list[str] = typer.Option([], "--recipe", "-r", help="Only these recipes (all lines)"),
    changed_files: Optional[Path] = typer.Option(None, help="File listing changed paths (push trigger); `-` = stdin"),
    before: Optional[str] = typer.Option(None, help="The commit before the push: changed config files that only differ in "
                                                    "comments, `description` or `notes` run nothing"),
    all_lines: bool = typer.Option(False, "--all", help="Every line of every recipe"),
    repo: Optional[Path] = RepoOpt,
) -> None:
    """Print the GitHub Actions matrix ({"include": [{recipe, line}]}) of lines that need a run."""
    r = _repo(repo)
    changed = None
    if changed_files:
        text = sys.stdin.read() if str(changed_files) == "-" else changed_files.read_text()
        changed = [l.strip() for l in text.splitlines() if l.strip()]
    matrix = pipeline.plan_matrix(r, recipes=recipe or None, changed_files=changed, include_all=all_lines, before=before)
    typer.echo(json.dumps({"include": matrix}))


@app.command("run")
def run_cmd(
    recipe: str = typer.Argument(..., help="Recipe name or path"),
    line: Optional[str] = typer.Option(None, help="Only this release line (key)"),
    out: Path = typer.Option(Path("out"), help="Reports/artifacts directory"),
    workdir: Path = typer.Option(Path(".work"), envvar="PATCHER_WORKDIR", help="Scratch dir for upstream checkouts"),
    platform: str = typer.Option(native_platform(), help="Platform for the local build/scan"),
    skip_tests: bool = typer.Option(False, "--skip-tests"),
    skip_build: bool = typer.Option(False, "--skip-build"),
    no_copa: bool = typer.Option(False, "--no-copa"),
    no_retry: bool = typer.Option(False, "--no-retry", help="Don't retry with patch-level bumps when tests fail"),
    no_cooldown: bool = typer.Option(False, "--no-cooldown", help="Ignore policy.minReleaseAgeDays for this run"),
    repo: Optional[Path] = RepoOpt,
) -> None:
    """PR flow for one recipe: patch, test, build, copa, report. Never pushes."""
    r = _repo(repo)
    rec = r.load_recipe(recipe)
    opts = pipeline.RunOptions(workdir=workdir.resolve(), out=out.resolve(), platform=platform, skip_tests=skip_tests,
                               skip_build=skip_build, copa=not no_copa, retry_patch_level=not no_retry, cooldown=not no_cooldown)
    lines = pipeline._lines(rec, line) if rec.source else []
    failed = False
    for ln in lines:
        s = pipeline.run_line(r, rec, ln, opts)
        log(f"{rec.name} {line_key(ln)} {s.tag}: {s.status}  (report: {opts.out / rec.name / line_key(ln) / 'generated' / 'report.md'})")
        failed |= s.status not in pipeline.RELEASABLE
    raise typer.Exit(1 if failed else 0)


@app.command()
def collect(out: Path = typer.Option(Path("out")), repo: Optional[Path] = RepoOpt) -> None:
    """Copy generated patch sets from `out/` into `generated/<recipe>/<tag>/` and print PR metadata."""
    _emit(pipeline.collect(_repo(repo), out.resolve()))


@app.command("release-plan")
def release_plan(
    recipe: Optional[str] = typer.Option(None, help="Release this recipe's line (with --line)"),
    line: Optional[str] = typer.Option(None),
    changed_files: Optional[Path] = typer.Option(None, help="File listing the paths a push changed; `-` = stdin"),
    repo: Optional[Path] = RepoOpt,
) -> None:
    """Print what release.yml runs: {"include": [{recipe, line, build, platforms, arches}], "skipped": [...],
    "errors": [...]}. Errors are per target, so the others can still be released."""
    r = _repo(repo)
    if recipe and line and not changed_files:
        targets, errors = [(recipe, line)], []
    elif changed_files and not (recipe or line):
        text = sys.stdin.read() if str(changed_files) == "-" else changed_files.read_text()
        targets, errors = pipeline.release_targets(r, [l.strip() for l in text.splitlines() if l.strip()])
    else:
        raise typer.BadParameter("give --recipe and --line, or --changed-files")
    plan = pipeline.release_plan(r, targets)
    plan["errors"] = errors + plan["errors"]
    typer.echo(json.dumps(plan))


def _platforms(value: Optional[str]) -> Optional[list[str]]:
    return [p for p in value.split(",") if p] if value else None


@app.command("release-build")
def release_build(
    recipe: str,
    line: str = typer.Option(...),
    platform: str = typer.Option(native_platform()),
    tag: Optional[str] = typer.Option(None, help="Upstream tag (default: newest generated patch set of the line)"),
    out: Path = typer.Option(Path("out")),
    workdir: Path = typer.Option(Path(".work"), envvar="PATCHER_WORKDIR", help="Scratch dir for upstream checkouts"),
    repo: Optional[Path] = RepoOpt,
) -> None:
    """Release flow, per platform: re-apply the reviewed patch set, build, and save each image to
    out/<recipe>/<line>/images/<arch>/<image>.tar. Pushes nothing and needs no credentials."""
    r = _repo(repo)
    _emit(pipeline.release_build(r, r.load_recipe(recipe), line, platform, workdir.resolve(), out.resolve(), tag))


@app.command("release-push")
def release_push(
    recipe: str,
    line: str = typer.Option(...),
    images: Optional[Path] = typer.Option(None, help="Archives from release-build (default: out/<recipe>/<line>/images)"),
    platforms: Optional[str] = typer.Option(None, help="Comma-separated subset of the recipe's platforms (default: all)"),
    tag: Optional[str] = typer.Option(None),
    out: Path = typer.Option(Path("out")),
    repo: Optional[Path] = RepoOpt,
) -> None:
    """Release flow: push release-build's archives as `<final>-<arch>` of the next free revision (never overwriting
    a tag); writes out/<recipe>/<line>/pushed.json."""
    r = _repo(repo)
    _emit(pipeline.release_push(r, r.load_recipe(recipe), line, out.resolve(), images.resolve() if images else None, tag,
                                _platforms(platforms)))


@app.command()
def publish(
    recipe: str,
    line: str = typer.Option(...),
    platforms: Optional[str] = typer.Option(None, help="Comma-separated subset of the recipe's platforms (default: all)"),
    tag: Optional[str] = typer.Option(None),
    revision: Optional[int] = typer.Option(None, help="The revision release-push pushed (default: the highest one whose "
                                                      "per-arch images all exist)"),
    finish_existing: bool = typer.Option(False, "--finish-existing", help="With --revision: keep a final tag that exists "
                                         "(a re-run of the same publish) instead of refusing it"),
    out: Path = typer.Option(Path("out")),
    repo: Optional[Path] = RepoOpt,
) -> None:
    """Release flow: merge per-arch images, Copa, push the final tags, update state/ (`promote` moves the moving ones)."""
    r = _repo(repo)
    _emit(pipeline.publish(r, r.load_recipe(recipe), line, _platforms(platforms), out.resolve(), tag, revision, finish_existing))


@app.command()
def rescan(out: Path = typer.Option(Path("out/rescan")), repo: Optional[Path] = RepoOpt) -> None:
    """Scan every published image; print {"refresh": [...], "rerun": [...]} matrices."""
    _emit(pipeline.rescan(_repo(repo), out.resolve()))


@app.command()
def promote(
    recipe: str,
    line: str = typer.Option(..., help="For the log; the images come from the release record"),
    release: Path = typer.Option(..., help="publish's or refresh's release.json"),
    repo: Optional[Path] = RepoOpt,
) -> None:
    """Move the moving tags (`<upstream tag>-patched`) to the digests in a release record. Run it after signing."""
    r = _repo(repo)
    moved = pipeline.promote(r, r.load_recipe(recipe), json.loads(release.read_text()))
    log(f"{recipe} {line}: " + (", ".join(moved) if moved else "nothing to promote"))


@app.command()
def refresh(
    recipe: str,
    line: str = typer.Option(...),
    platforms: Optional[str] = typer.Option(None, help="Only when state/ records none (default: the recipe's)"),
    out: Path = typer.Option(Path("out")),
    repo: Optional[Path] = RepoOpt,
) -> None:
    """Copa-only re-patch of a published line (new OS CVEs, no source change)."""
    r = _repo(repo)
    _emit(pipeline.refresh(r, r.load_recipe(recipe), line, _platforms(platforms), out.resolve()))


@app.command()
def init(
    repo_name: Optional[str] = typer.Argument(None, help="Upstream GitHub `owner/name` (or a git URL)"),
    image: Optional[str] = typer.Option(None, help="The image you run, e.g. quay.io/argoproj/argocd:v3.5.6"),
    name: Optional[str] = typer.Option(None, help="Recipe name (default: repo or image name)"),
    path: Optional[Path] = typer.Option(None, help="Use this existing checkout instead of cloning"),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing recipe"),
    workdir: Path = typer.Option(Path(".work"), envvar="PATCHER_WORKDIR", help="Scratch dir for the checkout"),
    repo: Optional[Path] = RepoOpt,
) -> None:
    """Draft recipes/<name>.yaml (+ skips) for a new upstream project or image."""
    import re as _re

    from . import onboarding, registry
    from . import upstream as up
    from .models import Source, Line

    r = _repo(repo)
    if not repo_name and not image:
        raise typer.BadParameter("give an upstream repo, --image, or both")
    image_repo, image_tag = (image.rsplit(":", 1) if image and ":" in image.rsplit("/", 1)[-1] else (image, None))
    if not repo_name and image:
        labels = registry.config_labels(image_repo, image_tag or "latest")
        source = labels.get("org.opencontainers.image.source", "")
        m = _re.match(r"https?://github\.com/([^/]+/[^/#?]+?)(?:\.git)?/?$", source)
        if not m:
            rec_name = name or image_repo.rsplit("/", 1)[-1]
            text = onboarding.draft_image_only(rec_name, image_repo, image_tag or "latest", ["linux/amd64", "linux/arm64"])
            _write_draft(r, rec_name, text, force)
            return
        repo_name = m.group(1)
        log(f"{image} declares its source: {repo_name}")
    rec_name = name or _re.sub(r"[^a-z0-9-]+", "-", repo_name.rsplit("/", 1)[-1].lower().removesuffix(".git")).strip("-")
    url = Source(repo=repo_name, lines=[Line(tagPattern=".")]).url
    tags = up.list_tags(url)
    tag = up.newest_tag(tags, r"^v?\d+\.\d+\.\d+$") or (image_tag or "")
    if not tag:
        raise typer.BadParameter(f"no release tags found in {url}")
    src = path
    if src is None:
        src = (workdir / "init" / rec_name).resolve()
        if src.exists():
            import shutil

            shutil.rmtree(src)
        up.checkout(url, tag, src, expected_commit=tags.get(tag))
    _write_draft(r, rec_name, onboarding.draft(src, rec_name, repo_name, tag, image), force)


def _write_draft(r: Repo, rec_name: str, text: str, force: bool) -> None:
    target = r.recipes_dir / f"{rec_name}.yaml"
    if target.exists() and not force:
        typer.echo(text)
        raise typer.BadParameter(f"{target} exists (printed the draft above; use --force to overwrite)")
    target.write_text(text)
    skips = r.root / "skips" / f"{rec_name}.yaml"
    if not skips.exists():
        skips.write_text("# yaml-language-server: $schema=../schema/skips.schema.json\nskips: []\nquarantine: []\n")
    typer.echo(f"wrote {target.relative_to(r.root)} (draft: review the TODOs)\n"
               f"next: patcher validate && patcher run {rec_name} --skip-tests --skip-build")


@app.command()
def coverage(
    json_out: bool = typer.Option(False, "--json", help="JSON instead of Markdown"),
    fail_on_uncovered: bool = typer.Option(False, "--fail-on-uncovered", help="Exit 1 if an inventory image has no recipe/line"),
    repo: Optional[Path] = RepoOpt,
) -> None:
    """Which inventory images are covered by a recipe, released patched, and what to use instead."""
    from . import inventory

    rows = inventory.coverage(_repo(repo))
    typer.echo(json.dumps(inventory.as_json(rows), indent=2) if json_out else inventory.render_markdown(rows))
    if fail_on_uncovered and any(x.status in ("no recipe", "version not tracked") for x in rows):
        raise typer.Exit(1)


@app.command("new-lines")
def new_lines(
    json_out: bool = typer.Option(False, "--json", help="JSON instead of Markdown"),
    repo: Optional[Path] = RepoOpt,
) -> None:
    """Upstream release lines newer than every line a recipe tracks (v3.6 shipped, recipes follow v3.5)."""
    from dataclasses import asdict

    from . import inventory

    found = inventory.new_lines(_repo(repo))
    if json_out:
        typer.echo(json.dumps([asdict(x) for x in found], indent=2))
        return
    typer.echo("| Recipe | New line | Newest release | Tracked lines |\n|---|---|---|---|")
    for x in found:
        typer.echo(f"| {x.recipe} | {x.line} | `{x.tag}` | {', '.join(x.tracked)} |")
    if not found:
        typer.echo("| — | every recipe tracks the newest upstream release | | |")


@app.command("eol")
def eol_cmd(
    within_days: int = typer.Option(90, help="Also report releases whose end of life is at most this many days away"),
    json_out: bool = typer.Option(False, "--json", help="JSON instead of Markdown"),
    repo: Optional[Path] = RepoOpt,
) -> None:
    """Runtimes that are end-of-life, or soon will be (endoflife.date): base images in each tracked line's
    Dockerfiles, after `minVersions`, and the recipes' toolchains."""
    from dataclasses import asdict

    from . import eol

    found = eol.check(_repo(repo), within_days)
    typer.echo(json.dumps([asdict(x) for x in found], indent=2) if json_out else eol.render_markdown(found, within_days))


@app.command()
def pins(
    write: bool = typer.Option(False, "--write", help="Rewrite the ARGs (default: only report)"),
    min_age_days: int = typer.Option(14, help="Only releases at least this old (supply-chain cooldown)"),
    dockerfile: Optional[Path] = typer.Option(None, help="Default: patcher/Dockerfile in the repo"),
    repo: Optional[Path] = RepoOpt,
) -> None:
    """Propose updates for the version+sha256 tool pins in patcher/Dockerfile; prints a Markdown summary."""
    from . import pins as pinmod

    path = dockerfile or (_repo(repo).root / "patcher" / "Dockerfile")
    updates = pinmod.check(path, min_age_days)
    if write:
        pinmod.apply(path, updates)
    typer.echo(pinmod.summary(updates, min_age_days))


if __name__ == "__main__":
    app()

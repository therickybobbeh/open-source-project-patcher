"""Stage orchestration.

`run_line`  - PR flow: checkout -> scan -> plan/apply (rounds) -> regen -> commit -> tests ->
              build (native platform) -> smoke -> copa -> report + generated/ files.
`release_build` / `publish` - release flow from the reviewed generated/ patch set.
`rescan` / `refresh` - nightly re-scan of published images and the Copa-only fast path.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import adapters, components, reach, releases, toolchain, upstream
from .adapters.base import Ctx, Result
from .build import BuiltImage, arch_of, build_image, image_digest, native_platform, smoke_test, template_ctx
from .config import Repo, line_key, render
from .ecosystems import CVE_ECOSYSTEMS
from . import copa
from .models import RELEASABLE_STATUSES, Level, Line, LineState, Recipe, ReleasedImage
from .planner import Plan, Unresolved, build_plan
from .proc import CommandError, first_error, log, output, run
from .report import BASE_TOOLING, GLOBAL_NODE_PREFIX, ImageOutcome, Summary, render_markdown
from .scan import ScanReport, scan_fs, scan_image
from .tests_runner import TestOutcome, only_preexisting, run_tests, same_setup_failure, setup_error
from .versions import parse_semver, try_parse
from .vex import oci_purl, openvex

# statuses whose patch set may be merged and released (tests-preexisting: upstream's own failures)
RELEASABLE = RELEASABLE_STATUSES
LOCAL_PREFIX = "patcher.local"


@dataclass
class RunOptions:
    workdir: Path
    out: Path
    platform: str = field(default_factory=native_platform)
    skip_tests: bool = False
    skip_build: bool = False
    copa: bool = True
    retry_patch_level: bool = True
    cooldown: bool = True  # the minimum-release-age rule (policy.minReleaseAgeDays)


@dataclass
class Attempt:
    label: str
    src: Path
    env: dict[str, str]
    first_plan: Plan
    result: Result
    unresolved: list[Unresolved]
    requires: dict[str, str]
    fs_after: ScanReport | None
    patch: str
    tests: TestOutcome | None
    malicious: list[dict] = field(default_factory=list)
    install_env: dict[str, str] = field(default_factory=dict)  # release-age cutoff for test installs


def _lines(recipe: Recipe, only: str | None) -> list[Line]:
    assert recipe.source
    lines = [l for l in recipe.source.lines if only is None or line_key(l) == only]
    if not lines:
        raise LookupError(f"{recipe.name}: no line {only!r} (have {[line_key(l) for l in recipe.source.lines]})")
    return lines


def _base_env(recipe: Recipe, out: Path) -> dict[str, str]:
    env = dict(recipe.env)
    if recipe.gitIdentity:
        cfg = out / "gitconfig"
        # git's own default branch (master), as on CI runners: upstream suites create repos and check it out
        cfg.write_text("[user]\n\tname = patcher\n\temail = patcher@localhost\n[commit]\n\tgpgsign = false\n[tag]\n\tgpgsign = false\n"
                       "[advice]\n\tdetachedHead = false\n\tdefaultBranchName = false\n")
        env["GIT_CONFIG_GLOBAL"] = str(cfg)
    return env


def _by_commit(recipe: Recipe, key: str) -> bool:
    return any(l.branch and line_key(l) == key for l in recipe.source.lines) if recipe.source else False


def _capped(recipe: Recipe, cap: Level | None) -> Recipe:
    if cap is None:
        return recipe
    pol = recipe.policy
    ecos = {k: (v if v.rank <= cap.rank else cap) for k, v in pol.ecosystems.items()}
    default = pol.default if pol.default.rank <= cap.rank else cap
    return recipe.model_copy(update={"policy": pol.model_copy(update={"default": default, "ecosystems": ecos})})


def _ecosystem_types(recipe: Recipe) -> set[str]:
    return {e.type for e in recipe.ecosystems}


def _scan_fs(repo: Repo, recipe: Recipe, src: Path, out: Path) -> ScanReport:
    if not recipe.scan.source:
        return ScanReport(artifact=str(src))
    g = repo.global_config()
    return scan_fs(src, out, severities=g.scan.severities, skip_dirs=g.scan.skipDirs + recipe.scan.skipDirs,
                   skip_files=recipe.scan.skipFiles, offline=recipe.scan.offline)


def _attempt(repo: Repo, recipe: Recipe, tag: str, commit: str, out: Path, opts: RunOptions, cap: Level | None,
             fs_before: ScanReport | None, extra: ScanReport | None = None) -> tuple[Attempt, ScanReport]:
    key = out.name
    label = ("full plan" if cap is None else f"capped at {cap.value}") + (" + image findings" if extra else "")
    log(f"== {recipe.name} {tag}: attempt ({label})")
    # one checkout per attempt, so the tree on disk always matches the attempt that is kept
    src = opts.workdir / recipe.name / key / ("src" + ("" if cap is None else f"-{cap.value}") + ("-image" if extra else ""))
    if src.exists():
        shutil.rmtree(src)
    upstream.checkout(recipe.source.url, tag, src, expected_commit=commit, by_commit=_by_commit(recipe, key))
    upstream.apply_patches(src, repo.patches(recipe.name), repo.overlay_dir(recipe.name))
    log_file = out / "patcher.log"
    env = toolchain.activate(recipe.toolchain, _base_env(recipe, out), src=src, recipe=recipe)
    for cmd in recipe.prepare:
        run(cmd, cwd=src, env=env, log_file=log_file, capture=False, clean=True)
    if fs_before is None:
        fs_before = _scan_fs(repo, recipe, src, out / "scan-fs-before.json")

    eff = _capped(recipe, cap)
    ctx = Ctx(src=src, recipe=eff, plan=Plan(), env=env, log=log_file)
    total = Result()
    report = _merge(fs_before, extra) if extra else fs_before
    first_plan: Plan | None = None
    plan = Plan()
    max_rounds = repo.global_config().scan.maxRounds
    gate = releases.gate_for(eff.policy) if opts.cooldown else None
    for rnd in range(1, max_rounds + 1):
        plan = build_plan(report, eff, _ecosystem_types(recipe), gate)
        first_plan = first_plan or plan
        if plan.toolchain.get("go"):
            ctx.requires["go"] = max(plan.toolchain["go"], ctx.requires.get("go", "0"), key=lambda v: parse_semver(v))
        ctx.plan = plan
        deferred = sum(1 for u in plan.unresolved if u.why.startswith("cooldown:"))
        if deferred:
            log(f"round {rnd}: {deferred} fix(es) deferred by the {eff.policy.minReleaseAgeDays}-day release-age rule")
        if not plan.bumps:
            break
        log(f"round {rnd}: {len(plan.bumps)} bump(s)")
        res = Result()
        for eco in recipe.ecosystems:
            if eco.type in CVE_ECOSYSTEMS:
                res.extend(adapters.apply(ctx, eco))
        total.extend(res)
        if not res.changes:
            break
        report = _scan_fs(repo, recipe, src, out / f"scan-fs-round{rnd}.json")
    unresolved = list(plan.unresolved)
    if plan.bumps and total.changes:
        # still planned after the last round: the bump didn't take (MVS/lock constraints)
        applied = {(c.name, c.new) for c in total.changes}
        for b in plan.bumps:
            if (b.name, b.to) not in applied:
                unresolved.append(Unresolved(b.ecosystem, b.target, b.name, b.installed, ",".join(b.reasons), "", b.to,
                                             f"still at {b.installed} after {max_rounds} round(s)"))

    for eco in recipe.ecosystems:  # one-shot refreshes, now that toolchain requirements are known
        if eco.type not in CVE_ECOSYSTEMS:
            total.extend(adapters.apply(ctx, eco))

    env = toolchain.activate(recipe.toolchain, env, ctx.requires, src=src, recipe=recipe)
    for rg in recipe.regen:
        if rg.when == "always" or (rg.when == "replaceGroupMoved" and "replaceGroupMoved" in total.flags):
            for cmd in rg.run:
                run(cmd, cwd=src, env=env, log_file=log_file, capture=False, clean=True)

    fs_after = _scan_fs(repo, recipe, src, out / "scan-fs-after.json")
    upstream.commit_all(src, f"patcher: dependency updates for {tag}", retag=tag)
    patch = upstream.diff(src, commit)

    # the versions we just introduced must not be known-malicious (OSV MAL-* advisories)
    changed = [l for l in output(["git", "-C", str(src), "diff", "--name-only", commit, "HEAD"]).splitlines() if l]
    malicious, mal_note = reach.malicious(src, changed, env)
    if mal_note:
        (first_plan or Plan()).notes.append(mal_note)
    if malicious:
        log(f"MALICIOUS package advisories for bumped versions: {malicious}")
        att = Attempt(label, src, env, first_plan or Plan(), total, unresolved, dict(ctx.requires), fs_after, patch, None, malicious)
        return att, fs_before

    tests = None
    install_env = _install_cutoff(gate, src, commit)
    if recipe.tests and not opts.skip_tests:
        test_dir = "tests" + ("" if cap is None else f"-{cap.value}") + ("-image" if extra else "")
        tests = run_tests(src, recipe.tests, repo.skips(recipe.name), out / test_dir, {**env, **install_env},
                          grace_days=repo.global_config().skipGraceDays)
    total.changes = _collapse(total.changes)
    plan_notes = set((first_plan or Plan()).notes) | {r.degraded for r in (fs_before, fs_after) if r and r.degraded}
    if gate is not None:
        plan_notes |= gate.notes
    (first_plan or Plan()).notes = sorted(plan_notes)
    att = Attempt(label, src, env, first_plan or Plan(), total, unresolved, dict(ctx.requires), fs_after, patch, tests,
                  install_env=install_env)
    return att, fs_before


def _install_cutoff(gate: releases.AgeGate | None, src: Path, commit: str) -> dict[str, str]:
    """The release-age rule, applied to what test setups install from ranges (see releases.install_cutoff_env)."""
    if gate is None or gate.bypassed_fresh:  # a CRITICAL/KEV fix younger than the rule must stay installable
        return {}
    try:
        released = dt.datetime.fromisoformat(output(["git", "-C", str(src), "log", "-1", "--format=%cI", commit]).strip())
    except (CommandError, ValueError):
        released = None
    cut = releases.install_cutoff_env(gate.min_days, released, now=gate.now)
    log(f"test installs (uv, pip, npm) resolve only releases published before {cut['UV_EXCLUDE_NEWER']}")
    return cut


def _collapse(changes: list) -> list:
    """Chain a package's moves across rounds into one row (first `old`, last `new`, all reasons).
    Only consecutive moves of the same copy are chained: a lockfile can hold several versions of a
    package (brace-expansion 1.x and 2.x), and those stay separate rows."""
    rows: list = []
    by_head: dict[tuple, object] = {}  # (eco, file, name, current version) -> row
    for c in changes:
        row = by_head.pop((c.ecosystem, c.target, c.name, c.old), None)
        if row is None:
            row = type(c)(**{**c.__dict__})
            rows.append(row)
        else:
            row.new = c.new
            row.note = ", ".join(n for n in dict.fromkeys(row.note.split(", ") + c.note.split(", ")) if n)
        by_head[(c.ecosystem, c.target, c.name, row.new)] = row
    return [r for r in rows if r.old != r.new]


def run_line(repo: Repo, recipe: Recipe, line: Line, opts: RunOptions) -> Summary:
    key = line_key(line)
    out = opts.out / recipe.name / key
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    g = repo.global_config()

    if recipe.mode == "image-only":
        return _run_image_only(repo, recipe, line, out, opts)

    tag, commit = upstream.resolve_line(recipe.source, line)
    log(f"{recipe.name} line {key}: {tag} @ {commit[:12]}")
    tctx = template_ctx(tag, commit)

    images_before: dict[str, tuple[str, ScanReport | None]] = {}
    for spec in recipe.build.images if recipe.build else []:
        if not spec.upstream:
            continue
        ref = f"{spec.upstream}:{render(spec.upstreamTag, tctx)}"
        try:
            images_before[spec.key] = (ref, scan_image(ref, out / f"scan-image-before-{spec.key}.json", severities=g.scan.severities,
                                                        platform=opts.platform, src="remote"))
        except CommandError as e:
            log(f"warning: could not scan upstream image {ref}: {e.tail[-300:]}")
            images_before[spec.key] = (ref, None)

    att, fs_before, attempts = _attempt_with_retry(repo, recipe, tag, commit, out, opts, None)
    summary = _summarize(repo, recipe, key, tag, commit, fs_before, att, attempts)
    summary.images = _build_and_scan(repo, recipe, att, summary, out, opts, tctx, images_before)
    if summary.status in ("build-failed", "smoke-failed") and opts.retry_patch_level and att.label.startswith("full plan") \
            and any(c.ecosystem in CVE_ECOSYSTEMS and _level(c) != "patch" for c in att.result.changes):
        # a bump broke the image build (lodash 4.18.0 broke a webpack UI build) or the image: the same retry as for tests
        failed_as = summary.status
        log(f"== {recipe.name} {tag}: {failed_as} with the full plan; retrying with patch-level bumps")
        retry, _ = _attempt(repo, recipe, tag, commit, out, opts, Level.patch, fs_before)
        retry_attempts = attempts + [f"{failed_as} → {retry.label}: {_test_word(retry.tests)}"]
        if retry.tests is None or not retry.tests.ran or retry.tests.passed or retry.tests.preexisting:
            s2 = _summarize(repo, recipe, key, tag, commit, fs_before, retry, retry_attempts)
            s2.images = _build_and_scan(repo, recipe, retry, s2, out, opts, tctx, images_before)
            if s2.status not in ("build-failed", "smoke-failed"):
                s2.notes.append(f"The full plan's image {failed_as.split('-')[0]} failed; this patch set has patch-level bumps "
                                "only. The bumps above patch level are listed as not applied.")
                summary, att = s2, retry

    # also (especially) after `no-changes`: a Gradle build without lockfiles shows the source scan nothing
    if _image_planning(recipe) and summary.status in RELEASABLE and summary.images:
        extra = image_derived(recipe, summary.images, att.fs_after, att.src)
        summary_first_images = list(summary.images)
        if extra.findings:
            log(f"{len(extra.findings)} finding(s) in the image's own artifacts that the source scan missed: second pass")
            att2, _, attempts2 = _attempt_with_retry(repo, recipe, tag, commit, out, opts, fs_before, extra)
            if att2.tests is None or not att2.tests.ran or att2.tests.passed or att2.tests.preexisting:
                summary = _summarize(repo, recipe, key, tag, commit, fs_before, att2, attempts + attempts2)
                # images without an upstream to compare with are compared with the first pass's build
                for o in summary_first_images:
                    if images_before.get(o.name, (None, None))[1] is None:
                        images_before[o.name] = (f"{o.ref} (first pass)", o.after)
                summary.images = _build_and_scan(repo, recipe, att2, summary, out, opts, tctx, images_before)
                att = att2
            else:
                summary.notes.append("Bumps planned from image findings broke the upstream tests; the first pass is kept "
                                     f"({len(extra.findings)} image finding(s) remain).")

    if recipe.scan.reachability and summary.status != "malicious-dependency":
        summary.vex_suggestions = _reachability(recipe, att)

    summary.src = str(att.src)
    _write_outputs(repo, summary, att, out)
    return summary


def _reachability(recipe: Recipe, att: Attempt) -> list[dict]:
    """govulncheck evidence for the Go findings that remain after patching (draft VEX, human-reviewed)."""
    gomod = [e for e in recipe.ecosystems if e.type == "gomod"]
    remaining = [f for f in (att.fs_after.findings if att.fs_after else []) if f.ecosystem == "gomod" and f.name != "stdlib"]
    if not gomod or not remaining:
        return []
    from .adapters.base import expand_dirs

    dirs = [d for e in gomod for d in expand_dirs(att.src, e.dirs, "go.mod")]
    levels = reach.go_reachability(att.src, dirs, att.env)
    return reach.vex_suggestions(remaining, levels)


def _attempt_with_retry(repo: Repo, recipe: Recipe, tag: str, commit: str, out: Path, opts: RunOptions,
                        fs_before: ScanReport | None, extra: ScanReport | None = None):
    att, fs_before = _attempt(repo, recipe, tag, commit, out, opts, None, fs_before, extra)
    attempts = [f"{att.label}: {_test_word(att.tests)}"]
    if not (att.tests and att.tests.ran and not att.tests.passed):
        return att, fs_before, attempts
    if not att.result.changes and not att.requires:
        # nothing was changed (any change can matter: Redis tests the tarball a `files` edit picks, the maven
        # image's bats suite builds the Dockerfiles), so this run *is* the unpatched source
        att.tests.preexisting = list(att.tests.failed)
        attempts.append("no dependency changes, so the failures are upstream's")
        return att, fs_before, attempts
    # failing tests: which of them already fail on the unpatched source?
    baseline = _baseline_tests(repo, recipe, tag, commit, out, opts, att.install_env)
    attempts.append(f"unpatched baseline: {_test_word(baseline)}")
    if only_preexisting(att.tests, baseline):
        att.tests.preexisting = list(att.tests.failed)
        return att, fs_before, attempts
    if same_setup_failure(att.tests, baseline):
        # no test ran on either side: the environment, not the bumps; a patch-level retry would fail the same way
        att.tests.note = ("The suite stopped before any test ran, with the same error on the unpatched source: an "
                          f"environment problem (patcher image or recipe), not these bumps. Error: {setup_error(att.tests.tail)}")
        attempts.append("the suite fails the same way on the unpatched source: environment problem")
        return att, fs_before, attempts
    if opts.retry_patch_level and any(c.ecosystem in CVE_ECOSYSTEMS and _level(c) != "patch" for c in att.result.changes):
        retry, _ = _attempt(repo, recipe, tag, commit, out, opts, Level.patch, fs_before, extra)
        attempts.append(f"{retry.label}: {_test_word(retry.tests)}")
        if retry.tests and retry.tests.passed:
            att = retry
        elif only_preexisting(retry.tests, baseline):
            retry.tests.preexisting = list(retry.tests.failed)
            att = retry
    return att, fs_before, attempts


def _baseline_tests(repo: Repo, recipe: Recipe, tag: str, commit: str, out: Path, opts: RunOptions,
                    install_env: dict[str, str] | None = None) -> TestOutcome | None:
    """The same tests on the unpatched source (upstream tag + patches/, no bumps), so failures that
    upstream already has aren't blamed on the bumps."""
    key = out.name
    src = opts.workdir / recipe.name / key / "baseline-src"
    if src.exists():
        shutil.rmtree(src)
    log(f"== {recipe.name} {tag}: tests on the unpatched source (baseline)")
    try:
        upstream.checkout(recipe.source.url, tag, src, expected_commit=commit, by_commit=_by_commit(recipe, key))
        upstream.apply_patches(src, repo.patches(recipe.name), repo.overlay_dir(recipe.name))
        env = toolchain.activate(recipe.toolchain, _base_env(recipe, out), src=src, recipe=recipe)
        for cmd in recipe.prepare:
            run(cmd, cwd=src, env=env, log_file=out / "patcher.log", capture=False, clean=True)
        return run_tests(src, recipe.tests, repo.skips(recipe.name), out / "tests-baseline", {**env, **(install_env or {})},
                         grace_days=repo.global_config().skipGraceDays)
    except (CommandError, RuntimeError) as e:
        log(f"baseline test run failed to start: {str(e)[:300]}")
        return None


def _summarize(repo: Repo, recipe: Recipe, key: str, tag: str, commit: str, fs_before: ScanReport, att: Attempt,
               attempts: list[str]) -> Summary:
    summary = Summary(recipe=recipe, line=key, tag=tag, commit=commit, status="success", fs_before=fs_before, fs_after=att.fs_after,
                      changes=att.result.changes, failures=att.result.failures, unresolved=att.unresolved, tests=att.tests,
                      attempts=attempts if len(attempts) > 1 else [], vex=repo.vex(recipe.name),
                      notes=list(att.first_plan.notes))
    summary.malicious = list(att.malicious)
    if att.malicious:
        summary.status = "malicious-dependency"
    elif att.tests and not att.tests.passed:
        summary.status = "tests-preexisting" if att.tests.preexisting else "tests-failed"
    elif not att.result.changes:
        summary.status = "no-changes"
    return summary


def _build_and_scan(repo: Repo, recipe: Recipe, att: Attempt, summary: Summary, out: Path, opts: RunOptions,
                    tctx: dict[str, str], images_before: dict) -> list[ImageOutcome]:
    g = repo.global_config()
    built: list[BuiltImage] = []
    if recipe.build and not opts.skip_build and summary.status not in ("tests-failed", "malicious-dependency"):
        upstream.reset_tree(att.src)
        try:
            for cmd in recipe.build.setup:
                run(render(cmd, tctx), cwd=att.src, env={**att.env, **recipe.build.env}, log_file=out / "build.log", capture=False, clean=True,
                    timeout=recipe.build.timeoutMinutes * 60)
            cache: dict = {}
            chosen: dict[str, str] = {}  # component -> the one version this line ships
            for spec in recipe.build.images:
                ref = f"{LOCAL_PREFIX}/{spec.name}:{render(spec.upstreamTag, tctx)}-patched.dev"
                img = build_image(att.src, recipe.build, spec, ref, opts.platform, tctx, att.env, out / "build.log", push=False)
                refs = components.applicable(recipe, spec.key)
                if refs:
                    built_scan = scan_image(img.ref, out / f"scan-image-built-{spec.key}.json", severities=g.scan.severities,
                                            platform=opts.platform)
                    comps = components.prepare(repo, refs, built_scan, opts, out, cache, src=att.src, image=img.ref)
                    usable = components.swappable(comps, chosen, spec.key, summary.notes)
                    if usable:
                        components.overlay(img.ref, usable, out / f"overlay-{spec.key}", platforms=[opts.platform], tag_ref=img.ref,
                                           push=False, local_base=True)
                    summary.components += [components.image_row(c, spec.key, usable) for c in comps]
                    summary.component_runs += [c for c in comps if c not in summary.component_runs]
                if not smoke_test(img, out / "build.log"):
                    summary.status = "smoke-failed"
                built.append(img)
        except (CommandError, ValueError) as e:
            summary.status = "build-failed"
            summary.notes.append(f"build failed: {str(e).splitlines()[0][:300]}")

    outcomes = []
    for img in built:
        before_ref, before = images_before.get(img.spec.key, (None, None))
        final_ref = img.ref
        copa_note = "disabled"
        cr = copa.for_image(img.spec, img.ref, img.ref.rsplit(":", 1)[1] + "-copa", out, platforms=[opts.platform],
                            severities=g.scan.severities) if opts.copa else None
        if cr:
            copa_note = cr.note()
            final_ref = cr.patched_ref or img.ref
        after = scan_image(final_ref, out / f"scan-image-after-{img.spec.key}.json", severities=g.scan.severities, platform=opts.platform)
        outcomes.append(ImageOutcome(img.spec.key, final_ref, before_ref, before, after, img.smoke, copa_note, img.spec.ownBinaries))
    return outcomes


# --- planning from image findings --------------------------------------------------------------

def _is_own(location: str, own: list[str]) -> bool:
    """`ownBinaries` entries are paths or directory prefixes inside the image."""
    return any(location == p.strip("/") or location.startswith(p.strip("/") + "/") for p in own)


def _image_planning(recipe: Recipe) -> bool:
    if recipe.scan.image is not None:
        return recipe.scan.image
    return any(e.type in ("gradle", "python") for e in recipe.ecosystems)


def _merge(a: ScanReport, b: ScanReport) -> ScanReport:
    return ScanReport(artifact=a.artifact, findings=a.findings + b.findings, packages=a.packages + b.packages, os=a.os)


def image_derived(recipe: Recipe, images: list[ImageOutcome], fs_after: ScanReport | None, src: Path | None = None) -> ScanReport:
    """Fixable findings in the built image's own jars / Python packages / node_modules that the source
    scan didn't see (Gradle builds without lockfiles, unpinned installs), re-targeted to the ecosystem
    that can fix them."""
    from dataclasses import replace

    from .adapters.node import LOCKFILES
    from .adapters.python import MARKERS, detect_tool
    from .scan import Package

    ecos = {e.type: e for e in recipe.ecosystems}
    java = ecos.get("gradle") or ecos.get("maven")
    java_target = None
    if java is not None:
        java_target = (java.dirs[0].rstrip("/") + "/build.gradle") if java.type == "gradle" else java.poms[0]
        java_target = java_target.removeprefix("./")
    node = next((ecos[t] for t in ("pnpm", "yarn", "npm") if t in ecos), None)
    python = ecos.get("python")
    python_target = None
    if python is not None:
        d = python.dirs[0]
        marker = dict(MARKERS).get(detect_tool((src or Path(".")) / d) or "", "requirements.txt")
        python_target = marker if d in (".", "") else f"{d}/{marker}"
    # packages the source scan already sees are planned there
    seen = {(f.name, f.installed) for f in (fs_after.findings if fs_after else [])}
    seen |= {(p.name, p.version) for p in (fs_after.packages if fs_after else [])}
    found: set[tuple[str, str, str]] = set()
    added: set[tuple[str, str]] = set()
    out = ScanReport(artifact="image-derived")
    for img in images:
        if not img.after:
            continue
        for f in img.after.fixable():
            loc = f.location
            if img.own_binaries and not _is_own(loc, img.own_binaries):
                continue
            if f.name in BASE_TOOLING.get(f.ecosystem, set()) or loc.startswith(GLOBAL_NODE_PREFIX):
                continue
            if f.ecosystem == "jar" and java is not None:
                eco, target = java.type, java_target
            elif f.ecosystem == "python-pkg" and python is not None:
                eco, target = "python", python_target
            elif f.ecosystem == "node-pkg" and node is not None:
                eco, target = node.type, f"{node.dirs[0].rstrip('/')}/{LOCKFILES[node.type]}".removeprefix("./")
            else:
                continue
            # every CVE of a package, so the planner picks a version that fixes all of them
            if (f.name, f.installed) in seen or (f.name, f.installed, f.vuln_id) in found:
                continue
            found.add((f.name, f.installed, f.vuln_id))
            out.findings.append(replace(f, ecosystem=eco, target=target, relationship=None))
            if (f.name, f.installed) not in added:
                added.add((f.name, f.installed))
                out.packages.append(Package(target, eco, f.name, f.installed, f"{f.name}@{f.installed}"))
    return out


def _level(change) -> str:
    a, b = try_parse(change.ecosystem, change.old), try_parse(change.ecosystem, change.new)
    if not a or not b:
        return "patch"
    from .versions import level_between

    return level_between(a, b, change.ecosystem).value


def _test_word(t: TestOutcome | None) -> str:
    if t is None or not t.ran:
        return "tests not run"
    return "tests passed" if t.passed else "tests failed"


def _write_outputs(repo: Repo, s: Summary, att: Attempt | None, out: Path) -> None:
    gen = out / "generated"
    gen.mkdir(exist_ok=True)
    md = render_markdown(s)
    (gen / "report.md").write_text(md)
    (out / "pr-body.md").write_text(md[:60000])
    if att is not None:
        (gen / "deps.patch").write_text(att.patch)
    plan_doc = {
        "recipe": s.recipe.name,
        "line": s.line,
        "tag": s.tag,
        "commit": s.commit,
        "status": s.status,
        "requires": att.requires if att else {},
        "plan": att.first_plan.to_json() if att else {},
        "changes": [asdict(c) for c in s.changes],
        "failures": [asdict(f) for f in s.failures],
        "unresolved": [asdict(u) for u in s.unresolved],
        "skips": [e.model_dump(mode="json") for e in (s.tests.skipped if s.tests else [])],
    }
    (gen / "bump-plan.json").write_text(json.dumps(plan_doc, indent=2, sort_keys=False) + "\n")
    for c in s.component_runs:
        if c.out and (c.out / "generated").is_dir() and c.recipe is not None:
            shutil.copytree(c.out / "generated", gen / "components" / c.recipe.name, dirs_exist_ok=True)
    if s.vex_suggestions:
        import yaml as _yaml

        (gen / "vex-suggestions.yaml").write_text(
            "# Draft VEX statements from govulncheck reachability. Review each one, then copy the ones you\n"
            f"# accept into vex/{s.recipe.name}.yaml. Nothing here is applied automatically.\n"
            + _yaml.safe_dump({"statements": s.vex_suggestions}, sort_keys=False))
    summary = {
        "recipe": s.recipe.name,
        "line": s.line,
        "tag": s.tag,
        "status": s.status,
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "images": [{"name": i.name, "ref": i.ref, "upstream": i.upstream_ref,
                    "after": i.after.to_json() if i.after else None} for i in s.images],
        "draft": s.status not in RELEASABLE,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    findings = [f for i in s.images if i.after for f in i.after.findings]
    for i in s.images:
        doc = openvex(s.vex, i.ref, findings, extra_docs=sorted((out / f"copa-{i.name}").glob("copa.vex.json")))
        (out / f"vex-{i.name}.openvex.json").write_text(json.dumps(doc, indent=2) + "\n")


def _image_only_targets(recipe: Recipe, line: Line) -> list[tuple]:
    """(spec, upstream tag) per image: each image's newest tag matching its own `tagPattern`
    (or the line's), read from its registry."""
    from .registry import list_tags as reg_tags

    assert recipe.build and recipe.source
    out = []
    for spec in recipe.build.images:
        pattern = spec.tagPattern or line.tagPattern or ""
        tag = line.tag if (line.tag and not spec.tagPattern) else upstream.newest_tag(list(reg_tags(spec.upstream or "")), pattern,
                                                                                         recipe.source.exclude)
        if not tag:
            raise LookupError(f"{recipe.name}: no {spec.upstream} tag matches {pattern!r}")
        out.append((spec, tag))
    return out


def _spec_platform(spec, wanted: str) -> str:
    return wanted if not spec.platforms or wanted in spec.platforms else spec.platforms[0]


def _run_image_only(repo: Repo, recipe: Recipe, line: Line, out: Path, opts: RunOptions) -> Summary:
    """Closed-source images: scan the upstream image, try Copa, report. No source changes."""
    g = repo.global_config()
    targets = _image_only_targets(recipe, line)
    s = Summary(recipe=recipe, line=line_key(line), tag=targets[0][1], commit="n/a", status="success", vex=repo.vex(recipe.name))
    cache: dict = {}
    chosen: dict[str, str] = {}  # component -> the one version this line ships
    for spec, tag in targets:
        ref = f"{spec.upstream}:{render(spec.upstreamTag, template_ctx(tag, ''))}"
        platform = _spec_platform(spec, opts.platform)
        try:
            before = scan_image(ref, out / f"scan-image-before-{spec.key}.json", severities=g.scan.severities, platform=platform, src="remote")
        except CommandError as e:
            s.notes.append(f"could not scan {ref} ({platform}): {first_error(e.tail)}")
            s.status = "scan-failed"
            continue
        copa_note, after = "disabled", before
        local = f"{LOCAL_PREFIX}/{spec.name}:{tag}"
        refs = components.applicable(recipe, spec.key)
        overlaid = False
        if refs:
            comps = components.prepare(repo, refs, before, opts, out, cache, image=ref)
            usable = components.swappable(comps, chosen, spec.key, s.notes)
            if usable:
                components.overlay(ref, usable, out / f"overlay-{spec.key}", platforms=[platform], tag_ref=local, push=False,
                                   local_base=False)
                overlaid = True
                after = scan_image(local, out / f"scan-image-after-{spec.key}.json", severities=g.scan.severities, platform=platform)
            s.components += [components.image_row(c, spec.key, usable) for c in comps]
            s.component_runs += [c for c in comps if c not in s.component_runs]
        if opts.copa and spec.copa_enabled:
            if not overlaid:
                run(["docker", "pull", "--platform", platform, ref])
                run(["docker", "tag", ref, local])
            cr = copa.for_image(spec, local, f"{tag}-copa", out, platforms=[platform], severities=g.scan.severities)
            copa_note = cr.note()
            if cr.patched_ref:
                after = scan_image(cr.patched_ref, out / f"scan-image-after-{spec.key}.json", severities=g.scan.severities, platform=platform)
        s.images.append(ImageOutcome(f"{spec.key} {tag}", ref, ref, before, after, [], copa_note))
    if (s.status == "success" and not any(c["status"] in RELEASABLE for c in s.components)
            and all(i.copa in ("disabled", "no fixable OS packages", "no fixable packages") for i in s.images)):
        s.status = "no-changes"
    _write_outputs(repo, s, None, out)
    return s


# --- release flow -------------------------------------------------------------


def find_generated(repo: Repo, recipe: Recipe, key: str, tag: str | None = None) -> tuple[Path, dict]:
    base = repo.root / "generated" / recipe.name
    best: tuple | None = None
    for plan_file in base.glob("*/bump-plan.json"):
        doc = json.loads(plan_file.read_text())
        if doc.get("line") != key or (tag and doc.get("tag") != tag):
            continue
        v = try_parse("semver", doc["tag"].lstrip("v")) or parse_semver("0")
        if best is None or v > best[0]:
            best = (v, plan_file.parent, doc)
    if not best:
        raise LookupError(f"no generated patch set for {recipe.name} line {key}" + (f" tag {tag}" if tag else ""))
    return best[1], best[2]


def next_revision(repo: Repo, recipe: Recipe, key: str, tag: str) -> int:
    """Next free revision. Also probes the registry: the state/ PR of an earlier release may not be
    merged yet, and published tags are never overwritten."""
    st = repo.state(recipe.name).lines.get(key)
    rev = st.revision + 1 if st and st.upstreamTag == tag else 1
    if recipe.build:
        spec = recipe.build.images[0]
        base = f"{repo.global_config().registry}/{spec.name}"
        up_tag = render(spec.upstreamTag, template_ctx(tag, ""))
        while _tag_exists(f"{base}:{final_tag(repo, up_tag, rev)}"):
            rev += 1
    return rev


def built_revision(repo: Repo, recipe: Recipe, key: str, tag: str, platforms: list[str]) -> int:
    """Revision `publish` should merge: the highest one whose per-arch builds all exist. A retried
    publish therefore finishes its own revision, while a fresh release-build always gets a new one."""
    st = repo.state(recipe.name).lines.get(key)
    rev = st.revision + 1 if st and st.upstreamTag == tag else 1
    spec = recipe.build.images[0]
    base = f"{repo.global_config().registry}/{spec.name}"
    up_tag = render(spec.upstreamTag, template_ctx(tag, ""))
    best = None
    while all(_tag_exists(f"{base}:{final_tag(repo, up_tag, rev)}-{arch_of(p)}") for p in platforms):
        best, rev = rev, rev + 1
    if best is None:
        raise LookupError(f"no per-arch builds of {base}:{final_tag(repo, up_tag, rev)}-<arch> for {platforms}; run release-build first")
    return best


def _tag_exists(ref: str) -> bool:
    # uses the docker credential store, so private GHCR packages are visible too
    return run(["docker", "buildx", "imagetools", "inspect", ref], check=False, quiet=True).code == 0


def final_tag(repo: Repo, upstream_tag: str, revision: int) -> str:
    return render(repo.global_config().tagFormat, {"upstream_tag": upstream_tag, "revision": revision})


def upstream_tag_of(repo: Repo, tag: str) -> str:
    """Inverse of `final_tag`: `v2.46.1-distroless-patched.3` -> `v2.46.1-distroless`."""
    import re

    fmt = re.escape(repo.global_config().tagFormat)
    fmt = fmt.replace(re.escape("{{upstream_tag}}"), "(?P<u>.+)").replace(re.escape("{{revision}}"), r"\d+")
    m = re.fullmatch(fmt, tag)
    if not m:
        raise ValueError(f"tag {tag!r} does not match tagFormat {repo.global_config().tagFormat!r}")
    return m.group("u")


def prepare_release_source(repo: Repo, recipe: Recipe, key: str, workdir: Path, out: Path, tag: str | None = None):
    gen, doc = find_generated(repo, recipe, key, tag)
    if doc.get("status") not in RELEASABLE:
        raise RuntimeError(f"generated patch set {gen} has status {doc.get('status')!r}; only successful runs are released")
    src = workdir / recipe.name / key / "release-src"
    if src.exists():
        shutil.rmtree(src)
    upstream.checkout(recipe.source.url, doc["tag"], src, expected_commit=doc["commit"], by_commit=_by_commit(recipe, key))
    patch = gen / "deps.patch"
    if patch.stat().st_size:
        run(["git", "-C", str(src), "apply", "--binary", "--whitespace=nowarn", str(patch.resolve())])
    upstream.commit_all(src, f"patcher: release {doc['tag']}", retag=doc["tag"])
    out.mkdir(parents=True, exist_ok=True)
    env = toolchain.activate(recipe.toolchain, _base_env(recipe, out), doc.get("requires") or {}, src=src, recipe=recipe)
    return src, doc, env


def release_build(repo: Repo, recipe: Recipe, key: str, platform: str, workdir: Path, out: Path, tag: str | None = None) -> list[dict]:
    """Build + push every image of a line for one platform as `<final>-<arch>` (merged by `publish`)."""
    if recipe.mode == "image-only":
        return []  # nothing to build: `publish` mirrors the upstream image
    out = out / recipe.name / key
    g = repo.global_config()
    assert recipe.build
    src, doc, env = prepare_release_source(repo, recipe, key, workdir, out, tag)
    tctx = template_ctx(doc["tag"], doc["commit"])
    rev = next_revision(repo, recipe, key, doc["tag"])
    for cmd in recipe.build.setup:
        run(render(cmd, tctx), cwd=src, env={**env, **recipe.build.env}, log_file=out / "build.log", capture=False, clean=True,
            timeout=recipe.build.timeoutMinutes * 60)
    gen, _ = find_generated(repo, recipe, key, tag)
    comps = components.from_generated(repo, recipe, gen, workdir / recipe.name / key) if recipe.components else {}
    pushed = []
    for spec in recipe.build.images:
        tag_base = final_tag(repo, render(spec.upstreamTag, tctx), rev)
        ref = f"{g.registry}/{spec.name}:{tag_base}-{arch_of(platform)}"
        mine = [comps[c.recipe] for c in components.applicable(recipe, spec.key) if c.recipe in comps]
        if mine:  # build locally, then push the overlay with the rebuilt components
            base = build_image(src, recipe.build, spec, f"{LOCAL_PREFIX}/{spec.name}:{tag_base}-base", platform, tctx, env,
                               out / "build.log", push=False)
            components.overlay(base.ref, mine, out / f"overlay-{spec.key}", platforms=[platform], tag_ref=ref, push=True, local_base=True)
        else:
            build_image(src, recipe.build, spec, ref, platform, tctx, env, out / "build.log", push=True)
        pushed.append({"image": spec.key, "ref": ref, "platform": platform, "components": [c.ref.recipe for c in mine]})
    return pushed


def publish(repo: Repo, recipe: Recipe, key: str, platforms: list[str], out: Path, tag: str | None = None) -> list[dict]:
    """Merge per-arch builds, Copa the result, push the immutable + moving tags, update state."""
    g = repo.global_config()
    out = out / recipe.name / key
    out.mkdir(parents=True, exist_ok=True)
    if recipe.mode == "image-only":
        return _publish_image_only(repo, recipe, key, platforms, out)
    gen, doc = find_generated(repo, recipe, key, tag)
    tctx = template_ctx(doc["tag"], doc["commit"])
    rev = built_revision(repo, recipe, key, doc["tag"], platforms)
    released: list[dict] = []
    images: list[ReleasedImage] = []
    for spec in recipe.build.images:
        up_tag = render(spec.upstreamTag, tctx)
        final = final_tag(repo, up_tag, rev)
        repo_ref = f"{g.registry}/{spec.name}"
        build_ref = f"{repo_ref}:{final}-build"
        run(["docker", "buildx", "imagetools", "create", "-t", build_ref, *[f"{repo_ref}:{final}-{arch_of(p)}" for p in platforms]])
        cr = copa.for_image(spec, build_ref, final, out, platforms=platforms, severities=g.scan.severities, push=True, src="remote")
        if not (cr and cr.patched_ref):
            run(["docker", "buildx", "imagetools", "create", "-t", f"{repo_ref}:{final}", build_ref])
        run(["docker", "buildx", "imagetools", "create", "-t", f"{repo_ref}:{up_tag}-patched", f"{repo_ref}:{final}"])
        digest = image_digest(f"{repo_ref}:{final}")
        after = scan_image(f"{repo_ref}@{digest}", out / f"scan-release-{spec.key}.json", severities=g.scan.severities,
                           platform=platforms[0], src="remote")
        vexdoc = openvex(repo.vex(recipe.name), oci_purl(repo_ref, digest), after.findings,
                         extra_docs=[cr.vex] if cr and cr.vex else [])
        vex_path = out / f"vex-{spec.key}.openvex.json"
        vex_path.write_text(json.dumps(vexdoc, indent=2) + "\n")
        images.append(ReleasedImage(name=spec.key, ref=f"{repo_ref}:{final}", digest=digest, knownFixable=_fixable_keys(after)))
        released.append({"image": spec.key, "repository": repo_ref, "tag": final, "digest": digest, "vex": str(vex_path),
                         "copa": (cr.skipped or "patched") if cr else "disabled"})
    st = repo.state(recipe.name)
    st.lines[key] = LineState(upstreamTag=doc["tag"], commit=doc["commit"], revision=rev,
                              releasedAt=dt.datetime.now(dt.timezone.utc).replace(microsecond=0), platforms=platforms, images=images)
    repo.save_state(recipe.name, st)
    (out / "release.json").write_text(json.dumps(released, indent=2) + "\n")
    return released


def _publish_image_only(repo: Repo, recipe: Recipe, key: str, platforms: list[str], out: Path) -> list[dict]:
    """Closed-source images: copy upstream into our registry, Copa what can be patched, record state."""
    g = repo.global_config()
    line = next(l for l in recipe.source.lines if line_key(l) == key)
    st = repo.state(recipe.name)
    released, images = [], []
    targets = _image_only_targets(recipe, line)
    prev = st.lines.get(key)
    rev = prev.revision + 1 if prev and prev.upstreamTag == targets[0][1] else 1
    comps = {}
    if recipe.components:
        gen, _ = find_generated(repo, recipe, key)
        comps = components.from_generated(repo, recipe, gen, out / "work")
    for spec, tag in targets:
        repo_ref = f"{g.registry}/{spec.name}"
        up_ref = f"{spec.upstream}:{render(spec.upstreamTag, template_ctx(tag, ''))}"
        final = final_tag(repo, tag, rev)
        plats = [p for p in platforms if not spec.platforms or p in spec.platforms] or spec.platforms
        mine = [comps[c.recipe] for c in components.applicable(recipe, spec.key) if c.recipe in comps]
        if mine:  # vendor image + our rebuilt helpers, all platforms in one cross-compiling build
            components.overlay(up_ref, mine, out / f"overlay-{spec.key}", platforms=plats, tag_ref=f"{repo_ref}:{final}-build",
                               push=True, local_base=False)
        else:
            run(["docker", "buildx", "imagetools", "create", "-t", f"{repo_ref}:{final}-build", up_ref])
        cr = copa.for_image(spec, f"{repo_ref}:{final}-build", final, out, platforms=plats, severities=g.scan.severities, push=True,
                            src="remote")
        if not (cr and cr.patched_ref):
            run(["docker", "buildx", "imagetools", "create", "-t", f"{repo_ref}:{final}", f"{repo_ref}:{final}-build"])
        run(["docker", "buildx", "imagetools", "create", "-t", f"{repo_ref}:{tag}-patched", f"{repo_ref}:{final}"])
        digest = image_digest(f"{repo_ref}:{final}")
        after = scan_image(f"{repo_ref}@{digest}", out / f"scan-release-{spec.key}.json", severities=g.scan.severities,
                           platform=plats[0], src="remote")
        vex_path = out / f"vex-{spec.key}.openvex.json"
        vex_path.write_text(json.dumps(openvex(repo.vex(recipe.name), oci_purl(repo_ref, digest), after.findings,
                                               extra_docs=[cr.vex] if cr and cr.vex else []), indent=2) + "\n")
        images.append(ReleasedImage(name=spec.key, ref=f"{repo_ref}:{final}", digest=digest, knownFixable=_fixable_keys(after)))
        released.append({"image": spec.key, "repository": repo_ref, "tag": final, "digest": digest, "vex": str(vex_path),
                         "copa": (cr.skipped or "patched") if cr else "disabled"})
    st.lines[key] = LineState(upstreamTag=targets[0][1], commit="n/a", revision=rev, platforms=platforms,
                              releasedAt=dt.datetime.now(dt.timezone.utc).replace(microsecond=0), images=images)
    repo.save_state(recipe.name, st)
    (out / "release.json").write_text(json.dumps(released, indent=2) + "\n")
    return released


# --- rescan / refresh / plan ---------------------------------------------------------------


def _fixable_keys(report: ScanReport) -> list[str]:
    return sorted({"|".join(f.key) for f in report.fixable()})


def rescan(repo: Repo, out: Path) -> dict:
    """Scan every published image; act only on fixable findings that are new since the release
    (known leftovers, e.g. in bundled binaries, are already explained in the release PR).
    New OS-only findings -> Copa refresh; new language findings -> source re-run."""
    g = repo.global_config()
    result = {"refresh": [], "rerun": []}
    out.mkdir(parents=True, exist_ok=True)
    for path in repo.recipe_paths():
        recipe = repo.load_recipe(path.stem)
        vexf = repo.vex(recipe.name)
        from .vex import match as vex_match

        for key, ls in repo.state(recipe.name).lines.items():
            kinds = set()
            platform = (ls.platforms or (recipe.build.platforms if recipe.build else ["linux/amd64"]))[0]
            for img in ls.images:
                rep = scan_image(f"{img.ref.rsplit(':', 1)[0]}@{img.digest}", out / f"rescan-{recipe.name}-{key}-{img.name}.json",
                                 severities=g.scan.severities, platform=platform, src="remote")
                known = set(img.knownFixable)
                for f in rep.fixable():
                    if "|".join(f.key) not in known and not vex_match(vexf, f):
                        kinds.add("os" if f.ecosystem == "os" else "lang")
            entry = {"recipe": recipe.name, "line": key}
            if "lang" in kinds:
                result["rerun"].append(entry)
            elif "os" in kinds:
                result["refresh"].append(entry)
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def refresh(repo: Repo, recipe: Recipe, key: str, platforms: list[str], out: Path) -> list[dict]:
    """Copa-only re-patch of the currently published images to the next revision."""
    g = repo.global_config()
    st = repo.state(recipe.name)
    ls = st.lines.get(key)
    if not ls:
        raise LookupError(f"{recipe.name} line {key} has never been released")
    out = out / recipe.name / key
    out.mkdir(parents=True, exist_ok=True)
    platforms = ls.platforms or platforms  # patch exactly what was released
    rev = ls.revision + 1
    released, images = [], []
    specs = {s.key: s for s in recipe.build.images}
    for img in ls.images:
        spec = specs.get(img.name)
        if spec is None or not spec.copa_enabled:  # removed from the recipe since, or `copa: false`
            images.append(img)
            continue
        repo_ref, cur_tag = img.ref.rsplit(":", 1)
        up_tag = upstream_tag_of(repo, cur_tag)
        final = final_tag(repo, up_tag, rev)
        cr = copa.for_image(spec, f"{repo_ref}@{img.digest}", final, out, platforms=platforms, severities=g.scan.severities,
                            push=True, src="remote")
        if not (cr and cr.patched_ref):
            images.append(img)
            continue
        run(["docker", "buildx", "imagetools", "create", "-t", f"{repo_ref}:{up_tag}-patched", f"{repo_ref}:{final}"])
        digest = image_digest(f"{repo_ref}:{final}")
        after = scan_image(f"{repo_ref}@{digest}", out / f"scan-refresh-{spec.key}.json", severities=g.scan.severities,
                           platform=platforms[0], src="remote")
        images.append(ReleasedImage(name=spec.key, ref=f"{repo_ref}:{final}", digest=digest, knownFixable=_fixable_keys(after)))
        released.append({"image": spec.key, "repository": repo_ref, "tag": final, "digest": digest, "copa": "patched"})
    if released:
        st.lines[key] = ls.model_copy(update={"revision": rev, "images": images,
                                               "releasedAt": dt.datetime.now(dt.timezone.utc).replace(microsecond=0)})
        repo.save_state(recipe.name, st)
    (out / "release.json").write_text(json.dumps(released, indent=2) + "\n")
    return released


def plan_matrix(repo: Repo, *, recipes: list[str] | None = None, changed_files: list[str] | None = None,
                include_all: bool = False) -> list[dict]:
    names = [p.stem for p in repo.recipe_paths()]
    selected: dict[str, set[str] | None] = {}  # recipe -> line keys (None = all)
    if recipes:
        for r in recipes:
            selected[r] = None
    elif changed_files is not None:
        for f in changed_files:
            parts = f.split("/")
            if f == "recipes/_global.yaml":  # org-wide policy: every line. (patcher/ code changes run nothing here:
                return plan_matrix(repo, include_all=True)  # patcher-image.yml tests them; dispatch `all` on purpose)
            if parts[0] in ("recipes", "skips", "vex") and len(parts) == 2 and f.endswith(".yaml"):
                selected[Path(parts[1]).stem] = None
            elif parts[0] == "patches" and len(parts) > 2:
                selected[parts[1]] = None
        # a changed component re-runs every recipe that bundles it; components never run on their own
        parents: dict[str, list[str]] = {}
        for n in names:
            for c in repo.load_recipe(n).components:
                parents.setdefault(c.recipe, []).append(n)
        for comp in [n for n in list(selected) if n in parents]:
            for parent in parents[comp]:
                selected.setdefault(parent, None)
    else:
        for name in names:
            recipe = repo.load_recipe(name)
            if not recipe.source or recipe.mode == "component":
                continue
            state = repo.state(name)
            if recipe.mode == "image-only":  # new upstream image tag -> run
                for line in recipe.source.lines:
                    key = line_key(line)
                    cur = state.lines.get(key)
                    if include_all or cur is None or cur.upstreamTag != _image_only_targets(recipe, line)[0][1]:
                        selected.setdefault(name, set()).add(key)
                continue
            tags = upstream.list_tags(recipe.source.url) if any(not l.branch for l in recipe.source.lines) else {}
            for line in recipe.source.lines:
                key = line_key(line)
                tag, commit = upstream.resolve_line(recipe.source, line, tags)
                cur = state.lines.get(key)
                if include_all or cur is None or cur.upstreamTag != tag or (line.branch and cur.commit != commit):
                    selected.setdefault(name, set()).add(key)
    matrix = []
    for name, keys in sorted(selected.items()):
        if name not in names:
            continue
        recipe = repo.load_recipe(name)
        if recipe.mode == "component":
            continue
        lines = recipe.source.lines if recipe.source else []
        for line in lines:
            k = line_key(line)
            if keys is None or k in keys:
                matrix.append({"recipe": name, "line": k})
    return matrix


def collect(repo: Repo, out: Path) -> list[dict]:
    """Copy out/<recipe>/<line>/generated -> generated/<recipe>/<tag>/ and describe each for the PR step."""
    items = []
    for summary_file in sorted(out.glob("*/*/summary.json")):
        s = json.loads(summary_file.read_text())
        gen = summary_file.parent / "generated"
        if not gen.is_dir() or s["status"] == "no-changes":
            continue  # nothing to review or release
        dest = repo.generated_dir(s["recipe"], s["tag"])
        if dest.exists():
            shutil.rmtree(dest)
        # one patch set per line: drop the line's older tags (git history keeps them)
        for old_plan in (repo.root / "generated" / s["recipe"]).glob("*/bump-plan.json"):
            if old_plan.parent != dest and json.loads(old_plan.read_text()).get("line") == s["line"]:
                shutil.rmtree(old_plan.parent)
        shutil.copytree(gen, dest)
        items.append({**{k: s[k] for k in ("recipe", "line", "tag", "status", "draft")}, "path": str(dest.relative_to(repo.root)),
                      "body": str((summary_file.parent / "pr-body.md").resolve())})
    return items


os.environ.setdefault("TRIVY_NO_PROGRESS", "true")

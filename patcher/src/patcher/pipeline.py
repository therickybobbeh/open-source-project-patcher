"""Stage orchestration.

`run_line`  - PR flow: checkout -> scan -> plan/apply (rounds) -> regen -> commit -> tests ->
              build (native platform) -> components + bundled-jar overlay -> smoke -> copa ->
              report + generated/ files.
`release_plan` / `release_build` / `release_push` / `publish` - release flow from the reviewed generated/ patch set.
`rescan` / `refresh` - nightly re-scan of published images and the Copa-only fast path.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import adapters, archive, components, jars, reach, releases, toolchain, upstream
from .adapters.base import Ctx, Result
from .build import BuiltImage, arch_of, build_image, image_digest, native_platform, smoke_test, template_ctx
from .config import Repo, line_key, render
from .ecosystems import CVE_ECOSYSTEMS
from . import copa
from .models import RELEASABLE_STATUSES, ImageSpec, Level, Line, LineState, Recipe, ReleasedImage
from .planner import Plan, Unresolved, build_plan
from .proc import CommandError, first_error, log, output, retry_on_network, run
from .report import BASE_TOOLING, GLOBAL_NODE_PREFIX, ImageOutcome, Summary, bundled_paths, render_markdown
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
    settled: bool = False  # nothing a test run or a rebuild could change (see _settled): tests didn't run


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
             fs_before: ScanReport | None, extra: ScanReport | None = None,
             upstream_images: dict | None = None) -> tuple[Attempt, ScanReport]:
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
    settled = upstream_images is not None and _settled(recipe, upstream_images, total.changes, ctx.requires, unresolved, fs_after)
    if recipe.tests and not opts.skip_tests and not settled:
        test_dir = "tests" + ("" if cap is None else f"-{cap.value}") + ("-image" if extra else "")
        tests = run_tests(src, recipe.tests, repo.skips(recipe.name), out / test_dir, {**env, **install_env},
                          grace_days=repo.global_config().skipGraceDays)
    total.changes = _collapse(total.changes)
    plan_notes = set((first_plan or Plan()).notes) | {r.degraded for r in (fs_before, fs_after) if r and r.degraded}
    if gate is not None:
        plan_notes |= gate.notes
    (first_plan or Plan()).notes = sorted(plan_notes)
    att = Attempt(label, src, env, first_plan or Plan(), total, unresolved, dict(ctx.requires), fs_after, patch, tests,
                  install_env=install_env, settled=settled)
    return att, fs_before


def _settled(recipe: Recipe, upstream_images: dict, changes: list, requires: dict, unresolved: list[Unresolved],
             fs: ScanReport | None) -> bool:
    """Nothing a test run or a rebuild could change: no dependency changes, and every fixable finding in upstream's
    images is a dependency of the project's own binaries that the source plan left unresolved (held, deferred by the
    release-age rule, no fix in range), so the rebuilt image would ship it again. OS packages (Copa, a newer base),
    Go's stdlib (the toolchain), bundled binaries (components) and Copa library patching keep the full run."""
    specs = recipe.build.images if recipe.build else []
    if changes or requires or not specs:
        return False
    left = {(u.name, u.vuln_id, u.installed.lstrip("v")) for u in unresolved}
    for spec in specs:
        ref, scan = upstream_images.get(spec.key, (None, None))
        if scan is None:
            return False
        fixable = scan.fixable()
        if fixable and spec.copa_enabled and spec.copa_options.libraries:
            return False
        bundled = bundled_paths(ImageOutcome(spec.key, ref, ref, scan, scan, own_binaries=spec.ownBinaries), fs)
        if any(f.ecosystem == "os" or f.name == "stdlib" or f.location in bundled
               or (f.name, f.vuln_id, f.installed.lstrip("v")) not in left for f in fixable):
            return False
    return True


def _rebuild_delta(images: list[ImageOutcome]) -> tuple[int, int]:
    """(fixed, new): fixable findings in upstream's images that ours don't have, and the reverse (the report's columns).
    A binary at another path than in upstream's image counts as both, so only fixed > new means a better image."""
    fixed = new = 0
    for i in images:
        if i.before and i.after:
            b, a = {f.key for f in i.before.fixable()}, {f.key for f in i.after.fixable()}
            fixed, new = fixed + len(b - a), new + len(a - b)
    return fixed, new


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

    att, fs_before, attempts = _attempt_with_retry(repo, recipe, tag, commit, out, opts, None, upstream_images=images_before)
    summary = _summarize(repo, recipe, key, tag, commit, fs_before, att, attempts)
    if att.settled:
        # the nightly run re-checks a line with nothing to change every night: this keeps that to a clone and the scans
        summary.notes.append("Nothing to change: no dependency bumps, and upstream's images have no fixable findings except "
                             "ones the source plan left unresolved, so the tests and the image build were skipped.")
        summary.images = [ImageOutcome(k, ref, ref, scan, scan, copa="not run: nothing to fix") for k, (ref, scan) in images_before.items()]
        summary.src = str(att.src)
        _write_outputs(repo, summary, att, out)
        return summary
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

    fixed, new = _rebuild_delta(summary.images)
    if summary.status == "no-changes" and fixed > new:
        # no dependency bumps, but our images are better than upstream's (Copa, rebuilt components, a newer base):
        # released like an image-only line's Copa patch set, instead of dropped
        summary.status = "success"
        summary.notes.append(f"No dependency bumps: this patch set is a rebuild of upstream's source, whose image(s) fix "
                             f"{fixed} finding(s) that upstream's have" + (f" (and have {new} that upstream's don't)." if new else "."))

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
                        fs_before: ScanReport | None, extra: ScanReport | None = None, upstream_images: dict | None = None):
    att, fs_before = _attempt(repo, recipe, tag, commit, out, opts, None, fs_before, extra, upstream_images)
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
            gate = releases.gate_for(recipe.policy) if opts.cooldown else None
            for spec in recipe.build.images:
                ref = f"{LOCAL_PREFIX}/{spec.name}:{render(spec.upstreamTag, tctx)}-patched.dev"
                img = build_image(att.src, recipe.build, spec, ref, opts.platform, tctx, att.env, out / "build.log", push=False)
                refs = components.applicable(recipe, spec.key)
                usable, swaps = [], []
                built_scan = scan_image(img.ref, out / f"scan-image-built-{spec.key}.json", severities=g.scan.severities,
                                        platform=opts.platform) if refs or spec.bundledJars else None
                if refs:
                    comps = components.prepare(repo, refs, built_scan, opts, out, cache, src=att.src, image=img.ref)
                    usable = components.swappable(comps, chosen, spec.key, summary.notes)
                    summary.components += [components.image_row(c, spec.key, usable) for c in comps]
                    summary.component_runs += [c for c in comps if c not in summary.component_runs]
                if spec.bundledJars:
                    swaps, unresolved = jars.prepare(img.ref, opts.platform, spec, built_scan, recipe, gate, out / f"overlay-{spec.key}")
                    summary.jars += swaps
                    summary.jar_unresolved += unresolved
                if usable or swaps:  # one overlay for both, before the smoke tests
                    components.overlay(img.ref, usable, out / f"overlay-{spec.key}", platforms=[opts.platform], tag_ref=img.ref,
                                       push=False, local_base=True, files=jars.copies(swaps), labels=jars.labels(swaps))
                if not smoke_test(img, out / "build.log"):
                    summary.status = "smoke-failed"
                built.append(img)
            if gate is not None:
                summary.notes += [n for n in sorted(gate.notes) if n not in summary.notes]
            if summary.jars and summary.status == "no-changes":  # the images changed, so there is a patch set to release
                summary.status = "success"
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
    bundled_jars = {s.key: s.bundledJars.paths for s in (recipe.build.images if recipe.build else []) if s.bundledJars}
    for img in images:
        if not img.after:
            continue
        for f in img.after.fixable():
            loc = f.location
            if img.own_binaries and not _is_own(loc, img.own_binaries):
                continue
            if f.ecosystem == "jar" and jars.under(loc, bundled_jars.get(img.name, [])):
                continue  # a bundled distribution's jar: swapped in the image (`bundledJars`), not bumped in the source
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
    if s.jars or s.jar_unresolved:  # the release re-applies exactly these swaps
        (gen / "jars.json").write_text(json.dumps(jars.to_json(s.jars, s.jar_unresolved), indent=2) + "\n")
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
    gate = releases.gate_for(recipe.policy) if opts.cooldown else None
    for spec, tag in targets:
        ref = f"{spec.upstream}:{render(spec.upstreamTag, template_ctx(tag, ''))}"
        platform = _spec_platform(spec, opts.platform)
        try:
            before = scan_image(ref, out / f"scan-image-before-{spec.key}.json", severities=g.scan.severities, platform=platform, src="remote")
        except CommandError as e:
            s.notes.append(f"could not scan {ref} ({platform}): {first_error(e.tail)}")
            s.status = "scan-failed"
            continue
        copa_note, after, smoke = "disabled", before, []
        local = f"{LOCAL_PREFIX}/{spec.name}:{tag}"
        refs = components.applicable(recipe, spec.key)
        usable, swaps = [], []
        if refs:
            comps = components.prepare(repo, refs, before, opts, out, cache, image=ref)
            usable = components.swappable(comps, chosen, spec.key, s.notes)
            s.components += [components.image_row(c, spec.key, usable) for c in comps]
            s.component_runs += [c for c in comps if c not in s.component_runs]
        if spec.bundledJars:
            swaps, unresolved = jars.prepare(ref, platform, spec, before, recipe, gate, out / f"overlay-{spec.key}")
            s.jars += swaps
            s.jar_unresolved += unresolved
        overlaid = bool(usable or swaps)
        if overlaid:
            components.overlay(ref, usable, out / f"overlay-{spec.key}", platforms=[platform], tag_ref=local, push=False,
                               local_base=False, files=jars.copies(swaps), labels=jars.labels(swaps))
            img = BuiltImage(spec, local, platform)  # the vendor image changed: its smoke tests (if any) must still pass
            if not smoke_test(img, out / "build.log"):
                s.status = "smoke-failed"
            smoke = img.smoke
            after = scan_image(local, out / f"scan-image-after-{spec.key}.json", severities=g.scan.severities, platform=platform)
        if opts.copa and spec.copa_enabled:
            if not overlaid:
                run(["docker", "pull", "--platform", platform, ref])
                run(["docker", "tag", ref, local])
            cr = copa.for_image(spec, local, f"{tag}-copa", out, platforms=[platform], severities=g.scan.severities)
            copa_note = cr.note()
            if cr.patched_ref:
                after = scan_image(cr.patched_ref, out / f"scan-image-after-{spec.key}.json", severities=g.scan.severities, platform=platform)
        s.images.append(ImageOutcome(f"{spec.key} {tag}", ref, ref, before, after, smoke, copa_note))
    if gate is not None:
        s.notes += sorted(gate.notes)
    if (s.status == "success" and not any(c["status"] in RELEASABLE for c in s.components) and not s.jars
            and all(i.copa in ("disabled", "no fixable OS packages", "no fixable packages") for i in s.images)):
        s.status = "no-changes"
    _write_outputs(repo, s, None, out)
    return s


# --- release flow -------------------------------------------------------------
#
# release.yml runs each stage in its own job, so upstream code never shares a job with registry credentials:
#   plan     release_plan    which line, on which platforms and runners             no upstream code, no credentials
#   build    release_build   per platform: rebuild the reviewed patch set, save      upstream code, no credentials,
#                            each image as an archive (archive.py)                   pushes nothing
#   push     release_push    pick the revision, push the archives as <final>-<arch>  credentials, no upstream code
#   publish  publish         merge the platforms, Copa, final + moving tags, state   credentials, no upstream code

# the native GitHub-hosted runner each platform is built on (release.yml's build matrix)
RUNNERS = {"linux/amd64": "ubuntu-24.04", "linux/arm64": "ubuntu-24.04-arm"}


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


def _releasable(gen: Path, doc: dict) -> None:
    if doc.get("status") not in RELEASABLE:
        raise RuntimeError(f"generated patch set {gen} has status {doc.get('status')!r}; only successful runs are released")


def image_platforms(recipe: Recipe, spec: ImageSpec, only: list[str] | None = None) -> list[str]:
    """The platforms one image is released for: `build.platforms`, narrowed to the image's own `platforms` if it lists
    any (and to `only` for a partial run, e.g. one platform locally)."""
    assert recipe.build
    return [p for p in recipe.build.platforms if (not spec.platforms or p in spec.platforms) and (only is None or p in only)]


def release_platforms(recipe: Recipe, only: list[str] | None = None) -> list[str]:
    """The platforms a release builds: those of `build.platforms` at least one image is released for."""
    assert recipe.build
    used = {p for s in recipe.build.images for p in image_platforms(recipe, s, only)}
    return [p for p in recipe.build.platforms if p in used]


def release_targets(repo: Repo, changed_files: list[str]) -> list[tuple[str, str]]:
    """(recipe, line) of every patch set a push added or changed: generated/<recipe>/<tag>/bump-plan.json at exactly
    that depth. A component's own plan (generated/<recipe>/<tag>/components/<name>/bump-plan.json) is not a release."""
    targets = []
    for f in changed_files:
        parts = f.split("/")
        path = repo.root / f
        if len(parts) == 4 and parts[0] == "generated" and parts[3] == "bump-plan.json" and path.is_file():
            doc = json.loads(path.read_text())
            targets.append((doc["recipe"], doc["line"]))
    return list(dict.fromkeys(targets))


def release_plan(repo: Repo, targets: list[tuple[str, str]]) -> dict:
    """What release.yml runs for each (recipe, line): `include` rows with whether anything is built, and the platforms
    with their native runners; `skipped` rows for what is never released, with the reason."""
    include, skipped = [], []
    for name, key in dict.fromkeys(targets):
        recipe = repo.load_recipe(name)
        why = ("a component: it ships inside its parents' images" if recipe.mode == "component"
               else "publish: false" if not recipe.publish else "")
        if why:
            skipped.append({"recipe": name, "line": key, "reason": why})
            continue
        _lines(recipe, key)  # an unknown line is an error, not a silent no-op
        if not recipe.build:
            raise ValueError(f"{name}: no `build` section, nothing to release")
        build = recipe.mode != "image-only"  # image-only: `publish` overlays the vendor image itself, in one cross build
        plats = release_platforms(recipe)
        if build and (missing := [p for p in plats if p not in RUNNERS]):
            raise ValueError(f"{name}: no native runner for {', '.join(missing)}; release builds run on {', '.join(RUNNERS)}")
        include.append({"recipe": name, "line": key, "build": build, "platforms": plats,
                        "arches": [{"platform": p, "arch": arch_of(p), "runner": RUNNERS[p]} for p in plats if p in RUNNERS]})
    return {"include": include, "skipped": skipped}


@dataclass
class ReleaseImage:
    """One image of a release revision, with its tags."""

    spec: ImageSpec
    repository: str  # <registry>/<name>
    upstream_tag: str  # what its tags start with, e.g. v2.46.1-distroless
    final: str  # the immutable tag, e.g. v2.46.1-distroless-patched.3
    platforms: list[str]

    @property
    def ref(self) -> str:
        return f"{self.repository}:{self.final}"

    @property
    def moving(self) -> str:
        return f"{self.repository}:{self.upstream_tag}-patched"

    def staging(self, platform: str) -> str:
        """`<final>-<arch>`: what `release_push` pushes and `publish` merges."""
        return f"{self.ref}-{arch_of(platform)}"

    @property
    def staged(self) -> list[str]:
        return [self.staging(p) for p in self.platforms]


def release_images(repo: Repo, recipe: Recipe, tctx: dict[str, str], rev: int, only: list[str] | None = None) -> list[ReleaseImage]:
    """Every image of revision `rev` with its tags. The one place release tags are made: what `release_push` may push,
    what `publish` merges and tags, and what `next_revision` / `built_revision` look for."""
    assert recipe.build
    g = repo.global_config()
    images = []
    for spec in recipe.build.images:
        plats = image_platforms(recipe, spec, only)
        if not plats:
            raise ValueError(f"{recipe.name}: image {spec.key} is released for none of {only}")
        up_tag = render(spec.upstreamTag, tctx)
        images.append(ReleaseImage(spec, f"{g.registry}/{spec.name}", up_tag, final_tag(repo, up_tag, rev), plats))
    return images


def _first_revision(repo: Repo, recipe: Recipe, key: str, tag: str) -> int:
    """The revision after the one state/ records for upstream `tag` (1 for a new tag)."""
    st = repo.state(recipe.name).lines.get(key)
    return st.revision + 1 if st and st.upstreamTag == tag else 1


def next_revision(repo: Repo, recipe: Recipe, key: str, tag: str, commit: str = "") -> int:
    """The revision `release_push` takes: the first after the released one (state/) of which no tag exists in the
    registry yet, final or per-arch, for any image. Nothing is ever overwritten: neither a published revision whose
    state/ PR isn't merged yet, nor the per-arch images an attempt left behind when it failed later (a new build takes
    a new revision, so revision numbers can skip)."""
    tctx = template_ctx(tag, commit)
    rev = _first_revision(repo, recipe, key, tag)
    while any(_tag_exists(ref) for i in release_images(repo, recipe, tctx, rev) for ref in (i.ref, *i.staged)):
        rev += 1
    return rev


def built_revision(repo: Repo, recipe: Recipe, key: str, tag: str, commit: str = "", only: list[str] | None = None) -> int:
    """The revision `publish` finishes when its run built nothing (release.yml with `rebuild: false`): the highest
    after the released one (state/) whose per-arch images all exist. `next_revision` hands revisions out in order and
    each one gets a tag, so the search ends at the first revision without any."""
    tctx = template_ctx(tag, commit)
    first = rev = _first_revision(repo, recipe, key, tag)
    best = None
    while True:
        images = release_images(repo, recipe, tctx, rev, only)
        exists = {ref: _tag_exists(ref) for i in images for ref in (i.ref, *i.staged)}
        if not any(exists.values()):
            break
        if all(exists[ref] for i in images for ref in i.staged):
            best = rev
        rev += 1
    if best is None:
        raise LookupError(f"{recipe.name} {key}: no revision of {tag} from {first} on has all its per-arch images "
                          f"({', '.join(release_images(repo, recipe, tctx, first, only)[0].staged)}, ...); "
                          "nothing to finish: release with `rebuild: true`")
    return best


_NOT_FOUND = re.compile(r"^ERROR: \S+: not found$", re.M)


def _tag_exists(ref: str) -> bool:
    """Whether `ref` is in the registry. Uses the docker credentials if there are any; our packages are public, so
    anonymous reads work too. Only a clear "not found" means no: anything else (network, authentication) raises, so a
    revision is never taken as free because the registry couldn't be asked."""

    def probe() -> bool:
        r = run(["docker", "buildx", "imagetools", "inspect", ref], check=False, quiet=True)
        if r.code and not _NOT_FOUND.search(r.out):
            raise CommandError(f"docker buildx imagetools inspect {ref}", r.code, r.out[-2000:])
        return r.code == 0

    return retry_on_network(probe)


def final_tag(repo: Repo, upstream_tag: str, revision: int) -> str:
    return render(repo.global_config().tagFormat, {"upstream_tag": upstream_tag, "revision": revision})


def upstream_tag_of(repo: Repo, tag: str) -> str:
    """Inverse of `final_tag`: `v2.46.1-distroless-patched.3` -> `v2.46.1-distroless`."""
    fmt = re.escape(repo.global_config().tagFormat)
    fmt = fmt.replace(re.escape("{{upstream_tag}}"), "(?P<u>.+)").replace(re.escape("{{revision}}"), r"\d+")
    m = re.fullmatch(fmt, tag)
    if not m:
        raise ValueError(f"tag {tag!r} does not match tagFormat {repo.global_config().tagFormat!r}")
    return m.group("u")


def prepare_release_source(repo: Repo, recipe: Recipe, key: str, workdir: Path, out: Path, tag: str | None = None):
    gen, doc = find_generated(repo, recipe, key, tag)
    _releasable(gen, doc)
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
    """Rebuild every image of a line released for `platform`, from the reviewed patch set, and save each one as an
    archive (`out/<recipe>/<line>/images/<arch>/<image key>.tar`) for `release_push`. Pushes nothing and needs no
    credentials: this job runs upstream code (build commands, Dockerfile RUN steps), so it never gets any. Component
    overlays and bundled-jar swaps happen here too, so the archives hold the finished per-arch images."""
    if not recipe.publish:
        log(f"{recipe.name}: publish: false, nothing is built or pushed")
        return []
    if recipe.mode == "image-only":
        return []  # nothing to build: `publish` overlays the upstream image
    out = out / recipe.name / key
    assert recipe.build
    specs = [s for s in recipe.build.images if platform in image_platforms(recipe, s)]
    if not specs:
        raise ValueError(f"{recipe.name}: no image is released for {platform} (build.platforms: {recipe.build.platforms})")
    src, doc, env = prepare_release_source(repo, recipe, key, workdir, out, tag)
    tctx = template_ctx(doc["tag"], doc["commit"])
    images = out / "images"
    shutil.rmtree(images / arch_of(platform), ignore_errors=True)  # only this build's archives get uploaded
    for cmd in recipe.build.setup:
        run(render(cmd, tctx), cwd=src, env={**env, **recipe.build.env}, log_file=out / "build.log", capture=False, clean=True,
            timeout=recipe.build.timeoutMinutes * 60)
    gen, _ = find_generated(repo, recipe, key, tag)
    comps = components.from_generated(repo, recipe, gen, workdir / recipe.name / key) if recipe.components else {}
    swaps = jars.from_generated(gen)
    built = []
    for spec in specs:
        local = f"{LOCAL_PREFIX}/{spec.name}:{render(spec.upstreamTag, tctx)}-release-{arch_of(platform)}"
        mine = [comps[c.recipe] for c in components.applicable(recipe, spec.key) if c.recipe in comps]
        mine_jars = swaps.get(spec.key, [])
        if mine or mine_jars:  # build, then overlay the rebuilt components and the reviewed jar swaps
            base = build_image(src, recipe.build, spec, f"{local}-base", platform, tctx, env, out / "build.log", push=False)
            jars.restage(base.ref, [platform], mine_jars, out / f"overlay-{spec.key}")
            components.overlay(base.ref, mine, out / f"overlay-{spec.key}", platforms=[platform], tag_ref=local, push=False,
                               local_base=True, files=jars.copies(mine_jars), labels=jars.labels(mine_jars))
        else:
            build_image(src, recipe.build, spec, local, platform, tctx, env, out / "build.log", push=False)
        path = archive.path_for(images, platform, spec.key)
        archive.export(local, path, out / "build.log")
        built.append({"image": spec.key, "platform": platform, "archive": str(path.relative_to(out)),
                      "components": [c.ref.recipe for c in mine], "jars": [f"/{s.path}: {s.name} {s.new}" for s in mine_jars]})
    return built


def release_push(repo: Repo, recipe: Recipe, key: str, out: Path, images: Path | None = None, tag: str | None = None,
                 platforms: list[str] | None = None) -> dict:
    """Push the archives `release_build` saved, as `<final>-<arch>` of the next free revision; writes pushed.json.

    release.yml's push job: credentials, no upstream code. The archives come from jobs that ran upstream code, so they
    are data. Every tag is computed here from the recipe and the reviewed patch set (`release_images`); each archive
    must hold exactly one image, of the platform its path names; only the archives at the expected paths are read;
    every archive is checked before anything is pushed; and no tag that exists is ever overwritten."""
    if not recipe.publish or recipe.mode != "source" or not recipe.build:
        raise ValueError(f"{recipe.name}: nothing to push (only source recipes with `publish: true` build images)")
    out = out / recipe.name / key
    out.mkdir(parents=True, exist_ok=True)
    images = images or out / "images"
    gen, doc = find_generated(repo, recipe, key, tag)
    _releasable(gen, doc)
    rev = next_revision(repo, recipe, key, doc["tag"], doc["commit"])
    planned = [(img, p, archive.path_for(images, p, img.spec.key))
               for img in release_images(repo, recipe, template_ctx(doc["tag"], doc["commit"]), rev, platforms) for p in img.platforms]
    for _, p, path in planned:
        archive.check(path, p)
    pushed = []
    for img, p, path in planned:
        ref = img.staging(p)
        if _tag_exists(ref):  # free when next_revision looked; another run may have pushed since
            raise RuntimeError(f"{ref} exists: it is never overwritten. Dispatch the release again: it takes a new revision")
        pushed.append({"image": img.spec.key, "platform": p, "ref": ref, "digest": archive.push(path, ref, out / "push.log")})
        log(f"pushed {ref} ({pushed[-1]['digest']})")
    result = {"recipe": recipe.name, "line": key, "tag": doc["tag"], "revision": rev, "pushed": pushed}
    (out / "pushed.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def publish(repo: Repo, recipe: Recipe, key: str, platforms: list[str] | None, out: Path, tag: str | None = None,
            revision: int | None = None) -> list[dict]:
    """Merge a revision's per-arch images, Copa the result, push the immutable and moving tags, update state.

    `revision`: the one `release_push` pushed in this run. Without it (the run built nothing: `rebuild: false`), the
    highest revision whose per-arch images all exist (`built_revision`). Never a revision state/ records. An image
    whose final tag exists already, because an earlier publish of this revision failed after pushing it, is finished
    as it is: no second merge or Copa, so its digest stays; it is tagged, scanned and recorded again, and the workflow
    signs and attests what is still missing. `platforms` narrows the release (default: the recipe's)."""
    out = out / recipe.name / key
    out.mkdir(parents=True, exist_ok=True)
    if not recipe.publish:
        log(f"{recipe.name}: publish: false, nothing is published")
        (out / "release.json").write_text("[]\n")
        return []
    if recipe.mode == "image-only":
        return _publish_image_only(repo, recipe, key, platforms or recipe.build.platforms, out)
    g = repo.global_config()
    gen, doc = find_generated(repo, recipe, key, tag)
    _releasable(gen, doc)
    tctx = template_ctx(doc["tag"], doc["commit"])
    first = _first_revision(repo, recipe, key, doc["tag"])
    if revision is None:
        rev = built_revision(repo, recipe, key, doc["tag"], doc["commit"], platforms)
    elif revision < first:
        raise ValueError(f"{recipe.name} {key}: state/ records revision {first - 1} of {doc['tag']}; revision {revision} "
                         "is released already and is never published again")
    else:
        rev = revision
    swaps = jars.from_generated(gen)  # already in the per-arch images merged here (release_build swapped them)
    released: list[dict] = []
    images: list[ReleasedImage] = []
    for img in release_images(repo, recipe, tctx, rev, platforms):
        spec, cr = img.spec, None
        if _tag_exists(img.ref):
            log(f"{img.ref} exists: an earlier publish of revision {rev} got this far; finishing it as it is")
            copa_note = "unchanged: an earlier publish of this revision pushed it"
        else:
            build_ref = f"{img.ref}-build"
            run(["docker", "buildx", "imagetools", "create", "-t", build_ref, *img.staged])
            cr = copa.for_image(spec, build_ref, img.final, out, platforms=img.platforms, severities=g.scan.severities, push=True,
                                src="remote")
            if not (cr and cr.patched_ref):
                run(["docker", "buildx", "imagetools", "create", "-t", img.ref, build_ref])
            copa_note = cr.note() if cr else "disabled"
        run(["docker", "buildx", "imagetools", "create", "-t", img.moving, img.ref])
        digest = image_digest(img.ref)
        after = scan_image(f"{img.repository}@{digest}", out / f"scan-release-{spec.key}.json", severities=g.scan.severities,
                           platform=img.platforms[0], src="remote")
        vexdoc = openvex(repo.vex(recipe.name), oci_purl(img.repository, digest), after.findings,
                         extra_docs=[cr.vex] if cr and cr.vex else [])
        vex_path = out / f"vex-{spec.key}.openvex.json"
        vex_path.write_text(json.dumps(vexdoc, indent=2) + "\n")
        images.append(ReleasedImage(name=spec.key, ref=img.ref, digest=digest, knownFixable=_fixable_keys(after)))
        released.append({"image": spec.key, "repository": img.repository, "tag": img.final, "digest": digest, "vex": str(vex_path),
                         "copa": copa_note, "jars": [f"/{s.path}: {s.name} {s.new}" for s in swaps.get(spec.key, [])]})
    st = repo.state(recipe.name)
    st.lines[key] = LineState(upstreamTag=doc["tag"], commit=doc["commit"], revision=rev,
                              releasedAt=dt.datetime.now(dt.timezone.utc).replace(microsecond=0),
                              platforms=release_platforms(recipe, platforms), images=images)
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
    comps, swaps = {}, {}
    if recipe.components or any(s.bundledJars for s in recipe.build.images):
        gen, _ = find_generated(repo, recipe, key)
        comps = components.from_generated(repo, recipe, gen, out / "work") if recipe.components else {}
        swaps = jars.from_generated(gen)
    for spec, tag in targets:
        repo_ref = f"{g.registry}/{spec.name}"
        up_ref = f"{spec.upstream}:{render(spec.upstreamTag, template_ctx(tag, ''))}"
        final = final_tag(repo, tag, rev)
        plats = [p for p in platforms if not spec.platforms or p in spec.platforms] or spec.platforms
        mine = [comps[c.recipe] for c in components.applicable(recipe, spec.key) if c.recipe in comps]
        mine_jars = swaps.get(spec.key, [])
        if mine or mine_jars:  # vendor image + our rebuilt helpers and swapped jars, all platforms in one cross-compiling build
            jars.restage(up_ref, plats, mine_jars, out / f"overlay-{spec.key}")
            components.overlay(up_ref, mine, out / f"overlay-{spec.key}", platforms=plats, tag_ref=f"{repo_ref}:{final}-build",
                               push=True, local_base=False, files=jars.copies(mine_jars), labels=jars.labels(mine_jars))
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
                         "copa": cr.note() if cr else "disabled",
                         "jars": [f"/{s.path}: {s.name} {s.new}" for s in mine_jars]})
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


def _refresh_revision(repo: Repo, ls: LineState, platforms: list[str]) -> int:
    """The revision a Copa refresh publishes: as for a release (`next_revision`), the first after the recorded one with
    no tag yet, final or per-arch. So a refresh never lands on a revision a failed release attempt left images for,
    which `rebuild: false` would then finish as that release."""

    def refs(rev: int):
        for img in ls.images:
            repository, current = img.ref.rsplit(":", 1)
            final = f"{repository}:{final_tag(repo, upstream_tag_of(repo, current), rev)}"
            yield final
            yield from (f"{final}-{arch_of(p)}" for p in platforms)

    rev = ls.revision + 1
    while any(_tag_exists(ref) for ref in refs(rev)):
        rev += 1
    return rev


def refresh(repo: Repo, recipe: Recipe, key: str, platforms: list[str] | None, out: Path) -> list[dict]:
    """Copa-only re-patch of the currently published images to the next revision."""
    if not recipe.publish:
        log(f"{recipe.name}: publish: false, nothing to refresh")
        return []
    g = repo.global_config()
    st = repo.state(recipe.name)
    ls = st.lines.get(key)
    if not ls:
        raise LookupError(f"{recipe.name} line {key} has never been released")
    out = out / recipe.name / key
    out.mkdir(parents=True, exist_ok=True)
    platforms = ls.platforms or platforms or recipe.build.platforms  # patch exactly what was released
    rev = _refresh_revision(repo, ls, platforms)
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
        plats = [p for p in platforms if not spec.platforms or p in spec.platforms] or spec.platforms  # what this image has
        cr = copa.for_image(spec, f"{repo_ref}@{img.digest}", final, out, platforms=plats, severities=g.scan.severities,
                            push=True, src="remote")
        if not (cr and cr.patched_ref):
            images.append(img)
            continue
        run(["docker", "buildx", "imagetools", "create", "-t", f"{repo_ref}:{up_tag}-patched", f"{repo_ref}:{final}"])
        digest = image_digest(f"{repo_ref}:{final}")
        after = scan_image(f"{repo_ref}@{digest}", out / f"scan-refresh-{spec.key}.json", severities=g.scan.severities,
                           platform=plats[0], src="remote")
        images.append(ReleasedImage(name=spec.key, ref=f"{repo_ref}:{final}", digest=digest, knownFixable=_fixable_keys(after)))
        released.append({"image": spec.key, "repository": repo_ref, "tag": final, "digest": digest, "copa": "patched"})
    if released:
        st.lines[key] = ls.model_copy(update={"revision": rev, "images": images,
                                               "releasedAt": dt.datetime.now(dt.timezone.utc).replace(microsecond=0)})
        repo.save_state(recipe.name, st)
    (out / "release.json").write_text(json.dumps(released, indent=2) + "\n")
    return released


def plan_matrix(repo: Repo, *, recipes: list[str] | None = None, changed_files: list[str] | None = None,
                include_all: bool = False, before: str | None = None) -> list[dict]:
    names = [p.stem for p in repo.recipe_paths()]
    selected: dict[str, set[str] | None] = {}  # recipe -> line keys (None = all)
    if recipes:
        for r in recipes:
            selected[r] = None
    elif changed_files is not None:
        for f in changed_files:
            if before and _same_meaning(repo, f, before):
                continue  # comments, `description` or `notes` only: the next run picks the text up
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
                    tag = _image_only_targets(recipe, line)[0][1]
                    if include_all or ((cur is None or cur.upstreamTag != tag) and not _pr_pending(repo, name, key, tag)
                                       and not _merged(repo, name, key, tag)):
                        selected.setdefault(name, set()).add(key)
                continue
            tags = upstream.list_tags(recipe.source.url) if any(not l.branch for l in recipe.source.lines) else {}
            for line in recipe.source.lines:
                key = line_key(line)
                tag, commit = upstream.resolve_line(recipe.source, line, tags)
                cur = state.lines.get(key)
                new = cur is None or cur.upstreamTag != tag or (line.branch and cur.commit != commit)
                if include_all or (new and not _pr_pending(repo, name, key, tag) and not _merged(repo, name, key, tag, commit)):
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


def _same_meaning(repo: Repo, path: str, before: str) -> bool:
    """A recipes/, skips/ or vex/ file whose parsed content is unchanged since `before`, apart from a recipe's
    `description` and `notes`: comments, formatting or prose only. Re-running a line (an hour of tests for
    some) can't change its outcome."""
    import yaml

    if not path.endswith(".yaml") or path.split("/")[0] not in ("recipes", "skips", "vex"):
        return False
    old = run(["git", "-C", str(repo.root), "show", f"{before}:{path}"], check=False, quiet=True)
    new = repo.root / path
    if old.code != 0 or not new.is_file():
        return False  # added or deleted

    def meaning(text: str):
        doc = yaml.safe_load(text)
        if path.startswith("recipes/") and isinstance(doc, dict):
            doc = {k: v for k, v in doc.items() if k not in ("description", "notes")}
        return doc

    try:
        return meaning(old.out) == meaning(new.read_text())
    except yaml.YAMLError:
        return False


def _pr_pending(repo: Repo, name: str, key: str, tag: str) -> bool:
    """A patch PR for exactly this upstream tag is already waiting for review (its branch holds the tag's patch set),
    so the nightly run doesn't redo it. Needs the PR branches fetched (patch.yml checks out with fetch-depth 0)."""
    ref = f"refs/remotes/origin/patch/{name}/{key}:generated/{name}/{tag}/bump-plan.json"
    return run(["git", "-C", str(repo.root), "cat-file", "-e", ref], check=False, quiet=True).code == 0


def _merged(repo: Repo, name: str, key: str, tag: str, commit: str = "n/a") -> bool:
    """This tag's patch set is merged already: its release ran, failed (re-run release.yml for it) or never runs
    (`publish: false`). Re-running the line would only open the same PR again, and the PR branch that `_pr_pending`
    sees may be gone. A branch line's new head commit is a new patch set."""
    plan_file = repo.root / "generated" / name / tag / "bump-plan.json"
    if not plan_file.is_file():
        return False
    doc = json.loads(plan_file.read_text())
    return doc.get("line") == key and doc.get("commit") == commit


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

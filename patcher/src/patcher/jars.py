"""Bundled jars: an image that unpacks a third-party Java distribution (Apache Maven in the official maven
image, Kafka's libs/ in Strimzi's broker images) ships jars its own build doesn't control, so no recipe bump
reaches them, and the distribution may have no fixed release yet. A fixable finding in a jar under
`bundledJars.paths` is fixed by swapping that jar for the fixed release from Maven Central:

1. planned like a source bump (`planner.build_plan`): the smallest fix within `bundledJars.level`, the
   release-age rule with its CRITICAL/KEV bypass, the withdrawn-release check (a no-op on Maven Central,
   which never withdraws a release), and holds under the `maven` key;
2. downloaded and checked against the checksum Central publishes; its sha256 becomes the pin;
3. copied over the old jar in an overlay build on the built image (`components.overlay`);
4. recorded in generated/<recipe>/<tag>/jars.json, which the release flow re-applies exactly."""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
import tempfile
import time
import urllib.error
from dataclasses import asdict, dataclass, field, fields, replace
from pathlib import Path

from . import releases
from .models import ImageSpec, Recipe
from .planner import Unresolved, build_plan
from .proc import CommandError, log, output, retry_on_network, run
from .scan import ScanReport
from .versions import split_fixed

CENTRAL = "https://repo1.maven.org/maven2"
LABEL = "patcher.swapped-jars"  # image label listing the swaps: each jar keeps its old file name (see `copies`)


@dataclass
class Swap:
    """One jar replaced in one image: a row of jars.json."""

    image: str  # image key
    path: str  # the jar in the image (no leading slash); the new release is written here, under the old name
    name: str  # groupId:artifactId
    old: str
    new: str
    vuln_ids: list[str] = field(default_factory=list)
    classifier: str = ""  # e.g. guice-5.1.0-classes.jar in Maven's lib/
    url: str = ""
    sha256: str = ""  # of the new jar: the pin the release flow checks the download against
    old_sha256: str = ""  # of the jar it replaces: the release only overwrites that exact file
    checksum: str = ""  # Central's published checksum the download matched (sha256 or sha1); "" if Central has none

    @property
    def context_file(self) -> str:
        """Its file in the overlay's build context."""
        return f"jars/{self.sha256[:12]}-{posixpath.basename(self.url)}"


def under(location: str, paths: list[str]) -> bool:
    """`bundledJars.paths` entries are directory prefixes or jar paths inside the image."""
    loc = location.strip("/")
    return any(loc == p.strip("/") or loc.startswith(p.strip("/") + "/") for p in paths)


def artifact_url(name: str, version: str, classifier: str = "") -> str:
    group, artifact = name.split(":", 1)
    return f"{CENTRAL}/{group.replace('.', '/')}/{artifact}/{version}/{artifact}-{version}{'-' + classifier if classifier else ''}.jar"


@dataclass
class Central:
    """Maven Central: version lists and checksum-verified downloads, cached for the run (a fake `fetch` in tests)."""

    fetch: object = field(default=releases._get, repr=False)  # (url, method) -> (headers, body), as in releases.ReleaseAges
    _versions: dict = field(default_factory=dict, repr=False)
    _files: dict = field(default_factory=dict, repr=False)

    def _get(self, url: str) -> bytes:
        try:
            return self.fetch(url)[1]
        except urllib.error.HTTPError as e:
            if e.code < 500 and e.code != 429:  # a 404 is an answer; a rate limit or a server error is worth one more try
                raise
        except OSError:  # network blips: resets, timeouts, DNS
            pass
        log(f"{url}: fetch failed; retrying in 10s")
        time.sleep(10)
        return self.fetch(url)[1]

    def versions(self, name: str) -> set[str] | None:
        """Every release Central lists for `group:artifact` (maven-metadata.xml); None when it can't be read."""
        if name not in self._versions:
            group, artifact = name.split(":", 1)
            try:
                body = self._get(f"{CENTRAL}/{group.replace('.', '/')}/{artifact}/maven-metadata.xml").decode()
                block = re.search(r"<versions>(.*?)</versions>", body, re.S)
                self._versions[name] = set(re.findall(r"<version>\s*([^<\s]+)\s*</version>", block.group(1))) if block else None
            except (urllib.error.URLError, OSError, ValueError):
                self._versions[name] = None
        return self._versions[name]

    def download(self, url: str) -> tuple[bytes, str]:
        """The file at `url`, checked against the checksum Central publishes next to it (sha256 where it has one, else
        sha1): (content, which checksum matched, or "" when Central publishes none)."""
        if url not in self._files:
            body = self._get(url)
            matched = ""
            for algo in ("sha256", "sha1"):
                try:
                    want = self._get(f"{url}.{algo}").decode().split()
                except urllib.error.HTTPError as e:
                    if e.code == 404:
                        continue
                    raise
                got = hashlib.new(algo, body).hexdigest()
                if not want or want[0].lower() != got:
                    raise ValueError(f"{algo} {got} does not match the {algo} Maven Central publishes ({want[0] if want else 'empty'})")
                matched = algo
                break
            self._files[url] = (body, matched)
        return self._files[url]


_central = Central()


def _prerelease(qualifier: str) -> bool:
    return any(re.fullmatch(r"(alpha|beta|milestone|rc|cr|snapshot|[abm])\d*", t, re.I) for t in re.findall(r"[A-Za-z]+\d*", qualifier))


def _flavor(version: str) -> str:
    """The variant every release of an artifact carries, e.g. `-jre`/`-android` (Guava) or `.Final` (Netty)."""
    m = re.search(r"[-.][A-Za-z]+$", version)
    return m.group(0) if m and not _prerelease(m.group(0)) else ""


def central_fixes(fixed: str | None, installed: str, versions: set[str] | None) -> str:
    """Advisory fix versions as releases on Central, in the installed jar's flavor. Guava's advisories say `33.7.2` (or
    `32.0.0-android`), while Central has `33.7.2-jre` and `33.7.2-android`, and a -jre jar must stay -jre. A single
    release with a suffix the advisory leaves out is matched too (Jetty 9's `9.4.54.v20240208` for `9.4.54`). Versions
    Central doesn't have are dropped when its version list is known; otherwise the flavored guess stands and the
    download decides."""
    flavor = _flavor(installed)
    out = []
    for v in split_fixed(fixed):
        base = v.removesuffix(_flavor(v))
        candidates = ([base + flavor] if flavor else []) + [v]
        if versions is None:
            out.append(candidates[0])
            continue
        hit = next((c for c in candidates if c in versions), None)
        if hit is None:
            suffixed = [p for p in versions if re.fullmatch(re.escape(base) + r"[.-][A-Za-z][\w.-]*", p) and not _prerelease(p[len(base):])]
            hit = suffixed[0] if len(suffixed) == 1 else None
        if hit:
            out.append(hit)
    return ", ".join(dict.fromkeys(out))


def _classifier(path: str, name: str, installed: str) -> str | None:
    """The classifier ("" for none) when `path` is `name`'s own jar, `artifact-version[-classifier].jar`. None when the jar
    only contains it (shaded, an uber-jar) or was renamed: swapping that file for the artifact would drop the rest of it."""
    artifact = name.split(":", 1)[-1]
    m = re.fullmatch(re.escape(f"{artifact}-{installed}") + r"(?:-(?P<c>[\w.-]+))?\.jar", posixpath.basename(path))
    return (m.group("c") or "") if m else None


def plan(scan: ScanReport | None, spec: ImageSpec, recipe: Recipe, gate=None,
         central: Central | None = None) -> tuple[list[Swap], list[Unresolved]]:
    """Swaps for one image: its fixable jar findings under `bundledJars.paths`, planned as Maven bumps of the jar itself,
    capped at `bundledJars.level`, so the release-age gate, its CRITICAL/KEV bypass and the withdrawn-release check
    apply exactly as for the source. Also returns why the others aren't swapped (for the report)."""
    central = central or _central
    cfg = spec.bundledJars
    if not cfg or scan is None:
        return [], []
    findings, unresolved, classifiers = [], [], {}
    for f in scan.findings:
        if f.ecosystem != "jar" or not f.fixable or not under(f.location, cfg.paths):
            continue
        loc = f.location.strip("/")
        classifier = _classifier(loc, f.name, f.installed)
        if classifier is None:
            why = f"`{f.name}` is packaged inside `{posixpath.basename(loc)}` (shaded or renamed), so it can't be swapped on its own"
        elif not (fixed := central_fixes(f.fixed, f.installed, central.versions(f.name))):
            why = f"the advisory's fix ({f.fixed}) is not a release of `{f.name}` on Maven Central"
        else:
            classifiers[loc] = classifier
            findings.append(replace(f, ecosystem="maven", target=loc, fixed=fixed))
            continue
        unresolved.append(Unresolved("jar", loc, f.name, f.installed, f.vuln_id, f.severity, f.fixed, why))
    pol = recipe.policy
    capped = recipe.model_copy(update={"policy": pol.model_copy(update={"ecosystems": {**pol.ecosystems, "maven": cfg.level}})})
    p = build_plan(ScanReport("bundled-jars", findings=findings), capped, {"maven"}, gate)
    for u in p.unresolved:
        if u.why.startswith("needs-human: fix requires a bump beyond"):  # the cap here is the jar setting, not `policy`
            u.why = f"needs-human: fix requires a bump beyond `bundledJars.level: {cfg.level.value}`"
        unresolved.append(replace(u, ecosystem="jar"))
    swaps = [Swap(spec.key, b.target, b.name, b.installed, b.to, list(b.reasons), classifiers[b.target]) for b in p.bumps]
    return swaps, unresolved


def image_sha256(image: str, platform: str, paths: list[str], work: Path) -> dict[str, str | None]:
    """sha256 of files in `image` (None if missing), read without starting it: `docker create` + `docker cp` work for
    images without a shell and for any platform, with no emulation."""
    if not paths:
        return {}
    work.mkdir(parents=True, exist_ok=True)
    # `true` is never run; it only satisfies images without an entrypoint or command
    cid = retry_on_network(lambda: output(["docker", "create", "--platform", platform, image, "true"])).strip()
    try:
        with tempfile.TemporaryDirectory(dir=work) as tmp:
            out = {}
            for i, p in enumerate(paths):
                dest = Path(tmp) / str(i)
                ok = run(["docker", "cp", f"{cid}:/{p.strip('/')}", str(dest)], check=False, quiet=True).code == 0
                out[p] = hashlib.sha256(dest.read_bytes()).hexdigest() if ok and dest.is_file() and not dest.is_symlink() else None
            return out
    finally:
        run(["docker", "rm", "-f", cid], check=False, quiet=True)


def _stage(s: Swap, ctx: Path, central: Central) -> None:
    """Download `s`'s jar into the overlay context `ctx`; without a pin yet, its sha256 becomes the pin."""
    body, s.checksum = central.download(s.url)
    digest = hashlib.sha256(body).hexdigest()
    if s.sha256 and digest != s.sha256:
        raise RuntimeError(f"{s.url}: sha256 {digest} does not match the pin in jars.json ({s.sha256})")
    s.sha256 = digest
    (ctx / s.context_file).parent.mkdir(parents=True, exist_ok=True)
    (ctx / s.context_file).write_bytes(body)


def prepare(image: str, platform: str, spec: ImageSpec, scan: ScanReport | None, recipe: Recipe, gate, ctx: Path,
            central: Central | None = None) -> tuple[list[Swap], list[Unresolved]]:
    """PR flow for one built image: plan the swaps, put each pinned jar into the overlay context `ctx`, and record the
    sha256 of the jar each one replaces. A jar that can't be fetched or read stays as it is, with the reason."""
    central = central or _central
    swaps, unresolved = plan(scan, spec, recipe, gate, central)
    try:
        old = image_sha256(image, platform, [s.path for s in swaps], ctx)
    except CommandError as e:
        log(f"could not read the jars to swap from {image}: {e.tail[-300:]}")
        old = {}
    kept = []
    for s in swaps:
        s.url = artifact_url(s.name, s.new, s.classifier)
        why = "" if old.get(s.path) else f"could not read `/{s.path}` from the built image"
        try:
            if not why:
                _stage(s, ctx, central)
        except (urllib.error.URLError, OSError, ValueError) as e:
            why = f"download of {s.new} from Maven Central failed: {str(e).splitlines()[0][:160]}"
        if why:
            unresolved += [Unresolved("jar", s.path, s.name, s.old, v, "", s.new, why) for v in s.vuln_ids]
            continue
        s.old_sha256 = old[s.path]
        log(f"bundled jar /{s.path}: {s.name} {s.old} -> {s.new} (sha256 {s.sha256})")
        kept.append(s)
    return kept, unresolved


def restage(image: str, platforms: list[str], swaps: list[Swap], ctx: Path, central: Central | None = None) -> None:
    """Release flow: check that `image` still has, on every platform, exactly the jars the reviewed patch set replaced
    (otherwise the COPY would add a second, unreviewed jar next to a renamed one), then put the pinned jars into the
    overlay context `ctx`."""
    if not swaps:
        return
    central = central or _central
    for p in platforms:
        have = image_sha256(image, p, [s.path for s in swaps], ctx)
        for s in swaps:
            if have.get(s.path) != s.old_sha256:
                raise RuntimeError(f"{image} ({p}): /{s.path} is not the jar the reviewed patch set replaced (sha256 "
                                   f"{have.get(s.path) or 'missing'}, expected {s.old_sha256}); re-run the patch flow for this line")
    for s in swaps:
        _stage(s, ctx, central)


def copies(swaps: list[Swap]) -> list[tuple[str, str]]:
    """(context file, image path) for the overlay: each new jar overwrites the old one *at its old path*.

    Why not remove the old jar and add the new one under its own name: a Dockerfile only deletes a file from a lower
    layer with a RUN (`rm`), and a RUN executes the image's own userland for the target platform. Distroless images
    have no shell or rm, and other platforms would need QEMU (`_publish_image_only` builds every platform at once). A
    COPY is a plain file layer that BuildKit writes for any platform. Keeping the name also keeps working whatever
    refers to the jar by name (a manifest Class-Path, a launcher script). The cost is a file name that shows the old
    version; scanners read the version from the jar's own pom.properties (Trivy reports the new one). The swap is
    recorded in jars.json, the report and the image's `patcher.swapped-jars` label."""
    return [(s.context_file, "/" + s.path) for s in swaps]


def labels(swaps: list[Swap]) -> dict[str, str]:
    """The image's own record of the swaps, for whoever finds `guava-33.7.1-jre.jar` holding 33.7.2-jre."""
    if not swaps:
        return {}
    return {LABEL: json.dumps([{"path": "/" + s.path, "name": s.name, "from": s.old, "to": s.new, "sha256": s.sha256} for s in swaps],
                              separators=(",", ":"))}


def to_json(swaps: list[Swap], unresolved: list[Unresolved]) -> dict:
    return {"swaps": [asdict(s) for s in swaps], "unresolved": [asdict(u) for u in unresolved]}


def from_generated(gen: Path) -> dict[str, list[Swap]]:
    """Release flow: the swaps the reviewed patch set recorded (generated/<recipe>/<tag>/jars.json), per image key."""
    path = gen / "jars.json"
    if not path.exists():
        return {}
    known = {f.name for f in fields(Swap)}
    out: dict[str, list[Swap]] = {}
    for row in json.loads(path.read_text()).get("swaps", []):
        s = Swap(**{k: v for k, v in row.items() if k in known})
        out.setdefault(s.image, []).append(s)
    return out

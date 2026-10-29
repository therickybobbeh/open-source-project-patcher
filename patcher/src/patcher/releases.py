"""Minimum release age for dependency bumps: when a fix version was published, and whether a CVE is
exempt (CRITICAL severity, or on CISA's Known Exploited Vulnerabilities list).

A version released minutes ago is how hijacked releases spread (Trivy, March 2026; npm/PyPI incidents),
so bumps only take versions at least `policy.minReleaseAgeDays` old. The rule applies to dependency
bumps only; overrides are explicit human decisions and Go toolchain releases are exempt."""

from __future__ import annotations

import datetime as dt
import email.utils
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from .proc import log

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
UA = {"User-Agent": "support-images-patcher (release-age check)"}


def _get(url: str, method: str = "GET") -> tuple[dict[str, str], bytes]:
    req = urllib.request.Request(url, method=method, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return {k.lower(): v for k, v in resp.headers.items()}, resp.read()


def _iso(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def go_escape(path: str) -> str:
    """Module proxy case-encoding: uppercase -> `!` + lowercase."""
    return re.sub(r"[A-Z]", lambda m: "!" + m.group(0).lower(), path)


@dataclass
class ReleaseAges:
    """Publish time and withdrawal status of `name@version` per ecosystem, cached for the run."""

    fetch: object = field(default=_get, repr=False)
    _cache: dict = field(default_factory=dict, repr=False)
    _docs: dict = field(default_factory=dict, repr=False)  # whole-package registry documents

    def _doc(self, url: str) -> dict:
        if url not in self._docs:
            _, body = self.fetch(url)
            self._docs[url] = json.loads(body)
        return self._docs[url]

    def releases(self, eco: str, name: str) -> dict[str, str | None] | None:
        """Every release of a package -> why the registry withdrew it (npm `deprecated`, PyPI/crates.io yanked), or
        None if it stands. None when the registry can't say (Go, Maven: no withdrawal metadata to read here)."""
        try:
            if eco in ("npm", "pnpm", "yarn"):
                doc = self._doc("https://registry.npmjs.org/" + name.replace("/", "%2f"))
                return {v: (m.get("deprecated") or None) for v, m in doc.get("versions", {}).items()}
            if eco == "python":
                doc = self._doc(f"https://pypi.org/pypi/{urllib.parse.quote(name)}/json")
                out = {}
                for v, files in doc.get("releases", {}).items():
                    yanked = files and all(f.get("yanked") for f in files)
                    out[v] = (files[0].get("yanked_reason") or "yanked") if yanked else None
                return out
            if eco == "cargo":
                doc = self._doc(f"https://crates.io/api/v1/crates/{name}")
                return {v["num"]: ("yanked" if v.get("yanked") else None) for v in doc.get("versions", [])}
        except (urllib.error.URLError, OSError, ValueError, KeyError, json.JSONDecodeError):
            return None
        return None

    def withdrawn(self, eco: str, name: str, version: str) -> str | None:
        rel = self.releases(eco, name)
        return rel.get(version.lstrip("v")) if rel else None

    def published(self, eco: str, name: str, version: str) -> dt.datetime | None:
        key = (eco, name, version)
        if key not in self._cache:
            try:
                self._cache[key] = self._lookup(eco, name, version)
            except (urllib.error.URLError, OSError, ValueError, KeyError, json.JSONDecodeError):
                self._cache[key] = None
        return self._cache[key]

    def _lookup(self, eco: str, name: str, version: str) -> dt.datetime | None:
        get = self.fetch
        if eco == "gomod":
            v = version if version.startswith("v") else f"v{version}"
            _, body = get(f"https://proxy.golang.org/{go_escape(name)}/@v/{go_escape(v)}.info")
            return _iso(json.loads(body)["Time"])
        if eco in ("npm", "pnpm", "yarn"):
            t = self._doc("https://registry.npmjs.org/" + name.replace("/", "%2f")).get("time", {}).get(version)
            return _iso(t) if t else None
        if eco == "python":
            _, body = get(f"https://pypi.org/pypi/{urllib.parse.quote(name)}/{urllib.parse.quote(version)}/json")
            times = [_iso(u["upload_time_iso_8601"]) for u in json.loads(body).get("urls", [])]
            return min(times) if times else None
        if eco in ("maven", "gradle"):
            group, artifact = name.split(":", 1)
            headers, _ = get(f"https://repo1.maven.org/maven2/{group.replace('.', '/')}/{artifact}/{version}/{artifact}-{version}.pom",
                             "HEAD")
            lm = headers.get("last-modified")
            return email.utils.parsedate_to_datetime(lm) if lm else None
        if eco == "cargo":
            _, body = get(f"https://crates.io/api/v1/crates/{name}/{version}")
            return _iso(json.loads(body)["version"]["created_at"])
        return None


def load_kev(fetch=_get) -> set[str]:
    try:
        _, body = fetch(KEV_URL)
        kev = {v["cveID"] for v in json.loads(body).get("vulnerabilities", [])}
    except (urllib.error.URLError, OSError, ValueError, KeyError, json.JSONDecodeError) as e:
        log(f"CISA KEV feed unavailable ({str(e)[:120]}): only the severity bypass applies to the release-age rule")
        return set()
    log(f"CISA KEV feed: {len(kev)} known-exploited CVEs (these bypass the release-age rule)")
    return kev


@dataclass
class AgeGate:
    min_days: int
    bypass_severities: set[str]
    kev: set[str]
    ages: ReleaseAges
    now: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))
    notes: set[str] = field(default_factory=set)
    bypassed_fresh: bool = False  # a bypass let in a version younger than min_days (test installs must see it too)

    def check(self, eco: str, name: str, version: str, severity: str, vuln_id: str) -> tuple[bool, str]:
        why = self.ages.withdrawn(eco, name, version)
        if why:  # never, whatever the severity: the registry itself says don't use it
            return False, f"{version} was withdrawn by its registry: {why[:120]}"
        if severity in self.bypass_severities or vuln_id in self.kev:
            published = self.ages.published(eco, name, version)
            if published is None or self.now - published < dt.timedelta(days=self.min_days):
                self.bypassed_fresh = True
            return True, ""
        published = self.ages.published(eco, name, version)
        if published is None:
            self.notes.add(f"release date of {name} {version} unknown; bumped without the {self.min_days}-day age check")
            return True, ""
        age = self.now - published
        if age >= dt.timedelta(days=self.min_days):
            return True, ""
        eligible = published + dt.timedelta(days=self.min_days)
        return False, f"cooldown: {version} released {age.days} day(s) ago (eligible {eligible:%Y-%m-%d})"

    def replacement(self, eco: str, name: str, version: str) -> str | None:
        """For a withdrawn fix version: the next release in the same major line that stands (lodash 4.18.0, marked
        "Bad release" on npm, -> 4.18.1). None when `version` stands or nothing replaces it."""
        from .versions import try_parse

        rel = self.ages.releases(eco, name)
        if not rel or not rel.get(version.lstrip("v")):
            return None
        base = try_parse(eco, version.lstrip("v"))
        later = sorted((p, v) for v, why in rel.items() if not why and (p := try_parse(eco, v)) is not None
                       and base is not None and p > base and p.major == base.major and not _prerelease(v))
        if not later:
            return None
        self.notes.add(f"{name} {version} was withdrawn by its registry ({rel[version.lstrip('v')][:80]}); "
                       f"{later[0][1]} considered instead")
        return later[0][1]


def install_cutoff_env(days: int, released: dt.datetime | None, now: dt.datetime | None = None) -> dict[str, str]:
    """Environment that makes uv, pip and npm resolve only releases published before a cutoff, for the
    installs a test setup does from version ranges (`pip install -e '.[test]'`, `npm install x`): a
    release from yesterday can break the suite or be malicious. The cutoff is `days` ago, or the
    upstream release time if that is later, so its own lockfiles always resolve."""
    cutoff = (now or dt.datetime.now(dt.timezone.utc)) - dt.timedelta(days=days)
    if released and released > cutoff:
        cutoff = released
    ts = cutoff.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    # pip >= 26.0 reads PIP_UPLOADED_PRIOR_TO; older pips ignore it
    return {"UV_EXCLUDE_NEWER": ts, "PIP_UPLOADED_PRIOR_TO": ts, "npm_config_before": ts}


def _prerelease(v: str) -> bool:
    return bool(re.search(r"-|(?:a|b|rc|alpha|beta|dev|pre)\.?\d*$", v, re.I))


_ages = ReleaseAges()
_kev: set[str] | None = None


def gate_for(policy) -> AgeGate | None:
    """The run's age gate for `policy` (shared caches), or None when the rule is off."""
    global _kev
    if not policy.minReleaseAgeDays:
        return None
    if _kev is None:
        _kev = load_kev() if policy.cooldownBypass.kev else set()
    return AgeGate(policy.minReleaseAgeDays, set(policy.cooldownBypass.severities), _kev, _ages)

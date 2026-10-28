"""Keep the tool downloads pinned in patcher/Dockerfile current.

Dependabot can't update them (they are `ARG <TOOL>_VERSION` + per-arch `ARG <TOOL>_SHA256_*` pairs),
so this picks each tool's newest stable GitHub release that is at least `min_age_days` old, reads
both sha256 values from the release's *own* checksum file, and rewrites the ARGs. The age rule is
the same supply-chain policy as Dependabot's cooldown: a compromised release (Trivy, March 2026)
has time to be caught before we pick it up.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from .versions import InvalidVersion, Version, parse_semver

API = "https://api.github.com"
ARCHES = ("amd64", "arm64")


@dataclass(frozen=True)
class Tool:
    arg: str  # ARG prefix in the Dockerfile, e.g. TRIVY -> TRIVY_VERSION, TRIVY_SHA256_AMD64
    repo: str
    assets: dict[str, str]  # arch -> release asset name; {v} = version without the leading v
    checksums: str  # regex for the checksum asset
    fmt: str = "sha256sum"  # or "yq" (one line per file, many hashes, order in checksums_hashes_order)


TOOLS = (
    Tool("MISE", "jdx/mise", {"amd64": "mise-v{v}-linux-x64.tar.gz", "arm64": "mise-v{v}-linux-arm64.tar.gz"}, r"^SHASUMS256\.txt$"),
    Tool("TRIVY", "aquasecurity/trivy", {"amd64": "trivy_{v}_Linux-64bit.tar.gz", "arm64": "trivy_{v}_Linux-ARM64.tar.gz"},
         r"^trivy_.*_checksums\.txt$"),
    Tool("COPA", "project-copacetic/copacetic", {"amd64": "copa_{v}_linux_amd64.tar.gz", "arm64": "copa_{v}_linux_arm64.tar.gz"},
         r"^copacetic_checksums\.txt$"),
    Tool("COSIGN", "sigstore/cosign", {"amd64": "cosign-linux-amd64", "arm64": "cosign-linux-arm64"}, r"^cosign_checksums\.txt$"),
    Tool("YQ", "mikefarah/yq", {"amd64": "yq_linux_amd64", "arm64": "yq_linux_arm64"}, r"^checksums$", fmt="yq"),
)


@dataclass
class Release:
    tag: str
    version: Version
    published: dt.datetime
    url: str
    assets: dict[str, str] = field(default_factory=dict)  # name -> download URL


@dataclass
class Update:
    tool: Tool
    current: str
    release: Release | None
    sha256: dict[str, str] = field(default_factory=dict)
    note: str = ""

    @property
    def changed(self) -> bool:
        return self.release is not None and bool(self.sha256)


# --- GitHub ---------------------------------------------------------------------------------


def _get(url: str, *, api: bool) -> bytes:
    headers = {"User-Agent": "support-images-patcher"}
    token = os.environ.get("GITHUB_TOKEN")
    if api:
        headers["Accept"] = "application/vnd.github+json"
        if token:
            headers["Authorization"] = f"Bearer {token}"
    # asset downloads redirect to signed storage URLs, which reject an extra Authorization header
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as resp:
        return resp.read()


def releases(repo: str) -> list[Release]:
    data = json.loads(_get(f"{API}/repos/{repo}/releases?per_page=100", api=True))
    out = []
    for r in data:
        if r.get("draft") or r.get("prerelease") or not r.get("published_at"):
            continue
        try:
            version = parse_semver(r["tag_name"].lstrip("v"))
        except InvalidVersion:
            continue
        out.append(Release(r["tag_name"], version, dt.datetime.fromisoformat(r["published_at"].replace("Z", "+00:00")),
                           r["html_url"], {a["name"]: a["browser_download_url"] for a in r.get("assets") or []}))
    return out


def pick(candidates: list[Release], min_age_days: int, now: dt.datetime | None = None) -> Release | None:
    """Highest version among stable releases at least `min_age_days` old. Highest *version*, not
    newest date: projects publish backports (e.g. trivy v0.74.3 after v0.75.0)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    old_enough = [r for r in candidates if now - r.published >= dt.timedelta(days=min_age_days) and _stable(r.version)]
    return max(old_enough, key=lambda r: r.version) if old_enough else None


def _stable(v: Version) -> bool:
    """No semver prerelease part (some projects don't flag `-rc` tags as GitHub prereleases)."""
    return "-" not in v.raw.split("+", 1)[0]


# --- checksum files ------------------------------------------------------------------------


def parse_sha256sum(text: str) -> dict[str, str]:
    """`<hex>  <name>` / `<hex> *<name>` / `<hex>  ./<name>` -> {name: hex}."""
    out = {}
    for line in text.splitlines():
        m = re.match(r"^([0-9a-fA-F]{64})\s+\*?(?:\./)?(\S+)\s*$", line.strip())
        if m:
            out[m.group(2)] = m.group(1).lower()
    return out


def parse_yq(text: str, order: str) -> dict[str, str]:
    """yq's `checksums`: `<name> <hash1> <hash2> ...`, hash order listed in `checksums_hashes_order`."""
    names = [l.strip() for l in order.splitlines() if l.strip()]
    idx = names.index("SHA-256") + 1  # parts[0] is the file name
    out = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) > idx:
            out[parts[0]] = parts[idx].lower()
    return out


def checksums_for(tool: Tool, rel: Release) -> dict[str, str]:
    """{arch: sha256} for `rel`, read from the release's own checksum file."""
    name = next((n for n in rel.assets if re.search(tool.checksums, n)), None)
    if not name:
        raise LookupError(f"{tool.repo} {rel.tag}: no checksum asset matching {tool.checksums}")
    text = _get(rel.assets[name], api=False).decode()
    if tool.fmt == "yq":
        order = rel.assets.get("checksums_hashes_order")
        if not order:
            raise LookupError(f"{tool.repo} {rel.tag}: missing checksums_hashes_order")
        sums = parse_yq(text, _get(order, api=False).decode())
    else:
        sums = parse_sha256sum(text)
    v = rel.tag.lstrip("v")
    out = {}
    for arch, template in tool.assets.items():
        asset = template.format(v=v)
        if asset not in rel.assets:
            raise LookupError(f"{tool.repo} {rel.tag}: no release asset {asset}")
        if asset not in sums:
            raise LookupError(f"{tool.repo} {rel.tag}: {asset} missing from {name}")
        out[arch] = sums[asset]
    return out


# --- Dockerfile ----------------------------------------------------------------------------


def read_pins(dockerfile: str) -> dict[str, str]:
    """ARG name -> value for every `ARG NAME=value` line."""
    return dict(re.findall(r"(?m)^ARG\s+([A-Z0-9_]+)=(\S+)\s*$", dockerfile))


def write_pins(dockerfile: str, values: dict[str, str]) -> str:
    for name, value in values.items():
        dockerfile, n = re.subn(rf"(?m)^(ARG\s+{re.escape(name)}=)\S+(\s*)$", lambda m, v=value: m.group(1) + v + m.group(2), dockerfile)
        if n != 1:
            raise ValueError(f"expected exactly one `ARG {name}=` line, found {n}")
    return dockerfile


# --- orchestration -------------------------------------------------------------------------


def check(dockerfile: Path, min_age_days: int, tools=TOOLS) -> list[Update]:
    pins = read_pins(dockerfile.read_text())
    updates = []
    for tool in tools:
        current = pins.get(f"{tool.arg}_VERSION")
        if not current:
            updates.append(Update(tool, "", None, note=f"no ARG {tool.arg}_VERSION in {dockerfile.name}"))
            continue
        try:
            best = pick(releases(tool.repo), min_age_days)
        except OSError as e:
            updates.append(Update(tool, current, None, note=f"GitHub lookup failed: {e}"))
            continue
        if best is None or best.version <= parse_semver(current):
            updates.append(Update(tool, current, None, note="up to date"))
            continue
        try:
            updates.append(Update(tool, current, best, checksums_for(tool, best)))
        except (LookupError, OSError) as e:
            updates.append(Update(tool, current, None, note=f"{best.tag} found but not usable: {e}"))
    return updates


def apply(dockerfile: Path, updates: list[Update]) -> None:
    values = {}
    for u in updates:
        if u.changed:
            values[f"{u.tool.arg}_VERSION"] = u.release.tag.lstrip("v")
            values.update({f"{u.tool.arg}_SHA256_{arch.upper()}": sha for arch, sha in u.sha256.items()})
    if values:
        dockerfile.write_text(write_pins(dockerfile.read_text(), values))


def summary(updates: list[Update], min_age_days: int) -> str:
    lines = [f"Tool pins in `patcher/Dockerfile`: newest stable releases at least {min_age_days} days old, "
             "checksums from each release's own checksum file.", "",
             "| Tool | Pinned | Proposed | Released | Notes |", "|---|---|---|---|---|"]
    for u in updates:
        if u.changed:
            r = u.release
            lines.append(f"| {u.tool.arg.lower()} | `{u.current}` | [`{r.tag.lstrip('v')}`]({r.url}) | {r.published:%Y-%m-%d} | |")
        else:
            lines.append(f"| {u.tool.arg.lower()} | `{u.current}` | | | {u.note} |")
    return "\n".join(lines) + "\n"

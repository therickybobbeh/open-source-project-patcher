"""`patcher coverage`: for every image in inventory.yaml (what you actually run), which recipe covers it,
whether a patched release exists, and what to switch to."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from . import registry
from .config import Repo, line_key, load_model
from .models import Inventory


@dataclass
class Row:
    image: str
    recipe: str = ""
    line: str = ""
    status: str = ""
    use: str = ""
    note: str = ""
    usedBy: str = ""


def _norm(image_repo: str) -> str:
    ref = registry.parse_ref(image_repo)
    return f"{ref.registry}/{ref.repository}"


def _split(image: str) -> tuple[str, str]:
    ref = registry.parse_ref(image)
    return ref.original_name, (ref.tag or "latest")


def _template_regex(template: str) -> re.Pattern[str]:
    parts = re.split(r"(\{\{\s*(?:tag|version)\s*\}\})", template)
    rx = ""
    for p in parts:
        m = re.fullmatch(r"\{\{\s*(tag|version)\s*\}\}", p)
        rx += f"(?P<{m.group(1)}>[^/]+?)" if m else re.escape(p)
    return re.compile(rx + "$")


def coverage(repo: Repo) -> list[Row]:
    inv_path = repo.root / "inventory.yaml"
    inv = load_model(inv_path, Inventory) if inv_path.exists() else Inventory()
    recipes = [repo.load_recipe(p.stem) for p in repo.recipe_paths()]
    by_upstream = {}
    for r in recipes:
        for spec in (r.build.images if r.build else []):
            if spec.upstream:
                by_upstream.setdefault(_norm(spec.upstream), []).append((r, spec))
    rows = []
    for item in inv.images:
        name, tag = _split(item.image)
        row = Row(image=item.image, usedBy=", ".join(item.usedBy))
        matches = by_upstream.get(_norm(name), [])
        if not matches:
            row.status = "no recipe"
            row.note = f"`patcher init --image {item.image}`"
            rows.append(row)
            continue
        hit = None
        for r, spec in matches:
            m = _template_regex(spec.upstreamTag).match(tag)
            if not m:
                continue
            upstream_tag = m.groupdict().get("tag") or m.groupdict().get("version") or tag
            candidates = [upstream_tag] if "tag" in m.groupdict() else [upstream_tag, "v" + upstream_tag]
            for line in (r.source.lines if r.source else []):
                for cand in candidates:
                    if (line.tagPattern and re.search(line.tagPattern, cand)) or line.tag == cand or line.branch:
                        hit = (r, spec, line, cand)
                        break
                if hit:
                    break
            if hit:
                break
        if not hit:
            r, spec = matches[0]
            row.recipe, row.status = r.name, "version not tracked"
            row.note = f"add a release line matching {tag!r} to recipes/{r.name}.yaml"
            rows.append(row)
            continue
        r, spec, line, upstream_tag = hit
        key = line_key(line)
        row.recipe, row.line = r.name, key
        state = repo.state(r.name).lines.get(key)
        released = next((i for i in (state.images if state else []) if i.name == spec.key), None)
        if not r.publish:
            row.status = "scanned only"
            row.note = "publish: false: patched and reported, never pushed; keep running the vendor image"
        elif not state or not released:
            row.status = "pending first release"
        elif state.upstreamTag == upstream_tag or (line.branch and state.upstreamTag == upstream_tag.lstrip("v")):
            row.status = "patched"
            row.use = f"{released.ref.rsplit(':', 1)[0]}@{released.digest}"
            row.note = f"{len(released.knownFixable)} known fixable finding(s) at release" if released.knownFixable else ""
        else:
            row.status = "newer release patched"
            row.use = released.ref
            row.note = f"you run {upstream_tag}; patched {state.upstreamTag} is available"
        rows.append(row)
    return rows


def render_markdown(rows: list[Row]) -> str:
    counts = {}
    for r in rows:
        counts[r.status] = counts.get(r.status, 0) + 1
    out = ["## Image coverage", "", " · ".join(f"**{v}** {k}" for k, v in sorted(counts.items())) or "inventory.yaml is empty", "",
           "| Image | Recipe / line | Status | Use instead | Notes | Used by |", "|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| `{r.image}` | {r.recipe + (' / ' + r.line if r.line else '') or '-'} | {r.status} | "
                   f"{('`' + r.use + '`') if r.use else '-'} | {r.note or ''} | {r.usedBy} |")
    return "\n".join(out) + "\n"


def as_json(rows: list[Row]) -> list[dict]:
    return [asdict(r) for r in rows]

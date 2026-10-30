"""Loading recipes/skips/vex/state from the repo and merging `_global.yaml`."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel

from .models import Build, Gate, GlobalConfig, Hold, Line, LineState, Override, Recipe, SkipFile, State, VexFile

M = TypeVar("M", bound=BaseModel)

_TEMPLATE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")


def render(template: str, ctx: dict[str, Any]) -> str:
    """Replace `{{name}}` placeholders; unknown names are an error (catches recipe typos)."""

    def sub(m: re.Match[str]) -> str:
        key = m.group(1)
        if key not in ctx:
            raise KeyError(f"unknown template variable {{{{{key}}}}} in {template!r} (known: {sorted(ctx)})")
        return str(ctx[key])

    return _TEMPLATE.sub(sub, template)


def load_yaml(path: Path) -> Any:
    with path.open() as f:
        return yaml.safe_load(f) or {}


def load_model(path: Path, model: type[M]) -> M:
    return model.model_validate(load_yaml(path))


def line_key(line: Line) -> str:
    """Stable short key for a release line: explicit name, else a slug of the pattern (`^v3\\.5\\.\\d+$` -> `v3.5`)."""
    if line.name:
        return line.name
    if line.tag:
        return line.tag
    pat = (line.tagPattern or "").strip("^$")
    pat = re.sub(r"\\d\+|\\d\*|\[0-9\]\+|\.\*|\(\.\*\)", "", pat)
    pat = pat.replace("\\.", ".").replace("\\", "")
    pat = re.sub(r"[^A-Za-z0-9.\-]+", "", pat).strip(".-")
    return pat or "default"


def wanted_platforms() -> list[str] | None:
    """PATCHER_PLATFORMS: build and release only these of each recipe's platforms, e.g. `linux/arm64` (or `arm64`)
    where one is enough. Comma-separated; unset or empty means every platform a recipe lists."""
    wanted = []
    for p in re.split(r"[\s,]+", os.environ.get("PATCHER_PLATFORMS", "").strip().lower()):
        if not p:
            continue
        p = p if "/" in p else f"linux/{p}"
        if not re.fullmatch(r"[a-z0-9]+/[a-z0-9]+(/v[0-9]+)?", p):
            raise ValueError(f"PATCHER_PLATFORMS: {p!r} is not a platform; use e.g. linux/arm64")
        wanted.append(p)
    return wanted or None


def _only(build: Build, wanted: list[str]) -> Build:
    """`build` narrowed to `wanted`, without the images that exist for none of those platforms. A recipe can be left
    with no platform at all: it isn't built or released here (`patcher plan` and `release-plan` skip it)."""
    plats = [p for p in build.platforms if p in wanted]
    images = [i for i in build.images if plats and (not i.platforms or set(i.platforms) & set(plats))]
    return build.model_copy(update={"platforms": plats, "images": images})


def _deep_merge(base: dict, over: dict) -> dict:
    return {**base, **{k: _deep_merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
                       for k, v in over.items()}}


def _merge_rules(global_rules: dict[str, list], recipe_rules: dict[str, list]) -> dict[str, list]:
    merged: dict[str, list] = {}
    for eco in set(global_rules) | set(recipe_rules):
        local = recipe_rules.get(eco, [])
        local_names = {r.name for r in local}
        merged[eco] = [r for r in global_rules.get(eco, []) if r.name not in local_names] + list(local)
    return merged


@dataclass
class Repo:
    """The support-images repository layout."""

    root: Path

    @property
    def recipes_dir(self) -> Path:
        return self.root / "recipes"

    def global_config(self) -> GlobalConfig:
        g = load_model(self.recipes_dir / "_global.yaml", GlobalConfig)
        if os.environ.get("PATCHER_REGISTRY"):  # CI sets ghcr.io/<owner>
            g.registry = os.environ["PATCHER_REGISTRY"].lower()
        return g

    def recipe_paths(self) -> list[Path]:
        return sorted(p for p in self.recipes_dir.glob("*.yaml") if not p.name.startswith("_"))

    def recipe_path(self, name_or_path: str) -> Path:
        p = Path(name_or_path)
        if p.suffix in (".yaml", ".yml") and p.exists():
            return p.resolve()
        candidate = self.recipes_dir / f"{name_or_path}.yaml"
        if not candidate.exists():
            raise FileNotFoundError(f"no recipe {name_or_path!r} (looked for {candidate})")
        return candidate

    def load_recipe(self, name_or_path: str) -> Recipe:
        """Load a recipe with `_global.yaml` overrides/holds/policy merged in (recipe values win), and its platforms
        narrowed to PATCHER_PLATFORMS if that is set."""
        path = self.recipe_path(name_or_path)
        recipe = load_model(path, Recipe)
        if recipe.name != path.stem:  # skips/, vex/, state/ and patches/ are keyed by the name
            raise ValueError(f"{path.name}: `name: {recipe.name}` must match the file name ({path.stem})")
        g = self.global_config()
        recipe.overrides = _merge_rules(g.overrides, recipe.overrides)
        recipe.holds = _merge_rules(g.holds, recipe.holds)
        if "policy" not in recipe.model_fields_set:
            recipe.policy = g.policy
        else:  # fields the recipe sets win; the rest (e.g. the age rule) come from _global.yaml
            recipe.policy = g.policy.model_copy(update=recipe.policy.model_dump(exclude_unset=True))
        # the gate's fields the recipe sets win, down to `failOn.fixable` and `failOn.unfixed`
        recipe.gate = Gate.model_validate(_deep_merge(g.gate.model_dump(), recipe.gate.model_dump(exclude_unset=True)))
        if recipe.build and (wanted := wanted_platforms()):
            recipe.build = _only(recipe.build, wanted)
        return recipe

    def skips(self, name: str) -> SkipFile:
        path = self.root / "skips" / f"{name}.yaml"
        return load_model(path, SkipFile) if path.exists() else SkipFile()

    def vex(self, name: str) -> VexFile:
        path = self.root / "vex" / f"{name}.yaml"
        return load_model(path, VexFile) if path.exists() else VexFile()

    def patches(self, name: str) -> list[Path]:
        d = self.root / "patches" / name
        return sorted(d.glob("*.patch")) if d.is_dir() else []

    def overlay_dir(self, name: str) -> Path:
        return self.root / "patches" / name / "files"

    def state_path(self, name: str, key: str) -> Path:
        return self.root / "state" / name / f"{key}.yaml"

    def state(self, name: str) -> State:
        """One file per release line (`state/<recipe>/<line>.yaml`): lines released together each open a state PR,
        and those would conflict if they all edited one file. A whole-recipe `state/<recipe>.yaml` still counts."""
        legacy = self.root / "state" / f"{name}.yaml"
        state = load_model(legacy, State) if legacy.exists() else State()
        for path in sorted((self.root / "state" / name).glob("*.yaml")):
            state.lines[path.stem] = load_model(path, LineState)
        return state

    def save_state(self, name: str, state: State) -> None:
        for key, line in state.lines.items():
            path = self.state_path(name, key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(yaml.safe_dump(line.model_dump(mode="json"), sort_keys=False))

    def generated_dir(self, name: str, tag: str) -> Path:
        return self.root / "generated" / name / tag


def find_repo_root(start: Path | None = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for p in [cur, *cur.parents]:
        if (p / "recipes" / "_global.yaml").exists():
            return p
    raise FileNotFoundError("could not find repo root (a directory containing recipes/_global.yaml)")


__all__ = [
    "Hold",
    "Override",
    "Repo",
    "find_repo_root",
    "line_key",
    "load_model",
    "load_yaml",
    "render",
]

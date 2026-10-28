"""Loading recipes/skips/vex/state from the repo and merging `_global.yaml`."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel

from .models import GlobalConfig, Hold, Line, Override, Recipe, SkipFile, State, VexFile

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
        """Load a recipe with `_global.yaml` overrides/holds/policy merged in (recipe values win)."""
        recipe = load_model(self.recipe_path(name_or_path), Recipe)
        g = self.global_config()
        recipe.overrides = _merge_rules(g.overrides, recipe.overrides)
        recipe.holds = _merge_rules(g.holds, recipe.holds)
        if "policy" not in recipe.model_fields_set:
            recipe.policy = g.policy
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

    def state_path(self, name: str) -> Path:
        return self.root / "state" / f"{name}.yaml"

    def state(self, name: str) -> State:
        path = self.state_path(name)
        return load_model(path, State) if path.exists() else State()

    def save_state(self, name: str, state: State) -> None:
        path = self.state_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(state.model_dump(mode="json"), sort_keys=False))

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

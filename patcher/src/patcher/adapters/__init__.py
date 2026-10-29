"""Per-ecosystem adapters. `apply(ctx, eco)` dispatches on the recipe ecosystem type."""

from __future__ import annotations

from ..models import CargoEco, DockerfileEco, FilesEco, GoModEco, GradleEco, MavenEco, NodeEco, PythonEco
from . import cargo, dockerfile, files, gomod, gradle, maven, node, python
from .base import Ctx, Result


def apply(ctx: Ctx, eco) -> Result:
    if isinstance(eco, GoModEco):
        return gomod.apply(ctx, eco)
    if isinstance(eco, CargoEco):
        return cargo.apply(ctx, eco)
    if isinstance(eco, MavenEco):
        return maven.apply(ctx, eco)
    if isinstance(eco, NodeEco):
        return node.apply(ctx, eco)
    if isinstance(eco, PythonEco):
        return python.apply(ctx, eco)
    if isinstance(eco, GradleEco):
        return gradle.apply(ctx, eco)
    if isinstance(eco, DockerfileEco):
        return dockerfile.apply(ctx, eco)
    if isinstance(eco, FilesEco):
        return files.apply(ctx, eco)
    raise TypeError(f"unsupported ecosystem {eco!r}")

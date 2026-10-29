"""What the pipeline knows about each ecosystem, in one table.

Adding an ecosystem starts here: give it a row, then an adapter in `adapters/` (dispatched from
`adapters/__init__.py`), its recipe model in `models.py`, a publish-time lookup in `releases.py` if it
has a public registry, and detection in `detect.py` for `patcher init`. Everything else (scan type
mapping, overrides/holds keys, the malicious-package check, toolchain needs, version-level rules) reads
this table."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EcosystemInfo:
    key: str  # recipe `type:`, and the key of overrides/holds
    trivy: tuple[str, ...] = ()  # Trivy result types (source manifests and lockfiles) that belong to it
    lockfiles: tuple[str, ...] = ()  # read by the malicious-package check after a bump
    toolchain: tuple[str, ...] = ()  # Toolchain fields a recipe using it needs
    zero_major_strict: bool = False  # a 0.x minor bump counts as major (caret ranges treat it as breaking)
    cve: bool = True  # planned from findings; False = refreshed on every run (base images, pinned files)


ECOSYSTEMS: dict[str, EcosystemInfo] = {e.key: e for e in (
    EcosystemInfo("gomod", trivy=("gomod",), lockfiles=("go.mod",), toolchain=("go",)),
    EcosystemInfo("cargo", trivy=("cargo",), lockfiles=("Cargo.lock",), toolchain=("rust",), zero_major_strict=True),
    EcosystemInfo("maven", trivy=("pom",), toolchain=("java", "maven")),
    EcosystemInfo("gradle", trivy=("gradle",), lockfiles=("gradle.lockfile",), toolchain=("java",)),
    EcosystemInfo("npm", trivy=("npm",), lockfiles=("package-lock.json",), toolchain=("node",), zero_major_strict=True),
    EcosystemInfo("pnpm", trivy=("pnpm",), lockfiles=("pnpm-lock.yaml",), toolchain=("node", "pnpm"), zero_major_strict=True),
    EcosystemInfo("yarn", trivy=("yarn",), lockfiles=("yarn.lock",), toolchain=("node", "yarn"), zero_major_strict=True),
    # every Python tool's files map to one ecosystem; the adapter picks the tool per directory
    EcosystemInfo("python", trivy=("pip", "pipenv", "poetry", "uv"), lockfiles=("poetry.lock", "uv.lock", "Pipfile.lock"),
                  toolchain=("python",)),
    EcosystemInfo("dockerfile", cve=False),
    EcosystemInfo("files", cve=False),
)}

# ecosystems planned from vulnerability findings, in a stable order
CVE_ECOSYSTEMS: tuple[str, ...] = tuple(k for k, e in ECOSYSTEMS.items() if e.cve)
# Trivy types of built artifacts in images: reported (and planned via scan.image), never bumped directly
ARTIFACT_TYPES = ("gobinary", "rustbinary", "jar", "node-pkg", "python-pkg", "conan")

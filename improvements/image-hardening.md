# Image hardening

**Status:** investigated on 2026-11-03; proposal, nothing built yet.

## Summary

- **We patch, we don't harden.** The pipeline removes known vulnerabilities (dependency bumps, rebuilt bundled tools,
  swapped jars, a refreshed base, Copa), and it signs and attests what it publishes (SBOM, OpenVEX, SLSA provenance).
  It doesn't reduce what an image can do: each image keeps its upstream Dockerfile's user, base and userland.
- **Where the 20 released images stand:**
  - 15 run as non-root by default.
  - 10 ship no shell or package manager (distroless or `scratch`), and 10 ship a full OS userland.
  - No secrets: the only hits are commented samples in Maven's default `settings.xml`.
- **Recommendation, smallest step first:**
  1. Measure. Trivy is already in the pipeline, and Dockle adds setuid/setgid checks.
  2. Add opt-in, low-risk hardening to the overlay build the pipeline already has.
  3. Move to minimal bases per recipe where the tests prove it works.

  Runtime hardening in the clusters (Pod Security "restricted", admitting only images we signed) protects the most,
  and needs no pipeline change.

## What hardening adds to patching

Patching removes the vulnerabilities we know about. Hardening limits what an attacker can do with one we don't:
- no root;
- no shell, package manager or downloader to pull more tools;
- no setuid binaries;
- fewer packages;
- a read-only filesystem.

The image-level controls are section 4 of the CIS Docker Benchmark.

## Where our images stand (2026-11-03)

Every released image (`state/` on `main`), linux/amd64, read from GHCR. Columns:
- **OS packages:** Trivy's OS package count.
- **Runs as:** the image config's `User`.
- **Shell** and **package manager / downloader:** found by package name. setuid binaries aren't checked yet (see
  below).

| Image | Base | OS packages | Runs as | Shell | Package manager / downloader |
|---|---|---|---|---|---|
| `router` `v2.19.0-patched.2` | debian 12.15 | 91 | `router` | bash, dash | apt, dpkg |
| `argocd` `v3.4.12-patched.4`, `v3.5.6-patched.4` | ubuntu 26.04 | 139 | `999` | bash, dash | apt, dpkg |
| `argo-rollouts` `v1.10.1-patched.3` | debian 12.15 | 5 | `999` | – | – |
| `kubectl-argo-rollouts` `v1.10.1-patched.3` | debian 12.15 | 5 | `999` | – | – |
| `workflow-controller` `v4.1.6-patched.4` | debian 13.7 | 6 | `8737` | – | – |
| `argocli` `v4.1.6-patched.4` | debian 13.7 | 6 | `8737` | – | – |
| `argoexec` `v4.1.6-patched.4` | debian 13.7 | 6 | **root** (`USER 0`) | – | – |
| `copa` `v0.15.0-patched.5` | debian 13.7 | 80 | **root** (no `USER`) | bash, dash | apt, dpkg |
| `copacetic-frontend` `v0.15.0-patched.5` | debian 12.15 | 5 | `65532` | – | – |
| `dex` `v2.46.1-patched.2` | alpine 3.24.3 | 16 | `dex:dex` | busybox | apk-tools |
| `dex-distroless` `v2.46.1-distroless-patched.2` | debian 13.7 | 6 | `dex:dex` | – | – |
| `maven-temurin-21-noble` `3.10.0-eclipse-temurin-21-noble-patched.4` | ubuntu 24.04 | 159 | **root** (no `USER`) | bash, dash | apt, dpkg, curl, wget |
| `maven-temurin-17-noble` `3.10.0-eclipse-temurin-17-noble-patched.4` | ubuntu 24.04 | 159 | **root** (no `USER`) | bash, dash | apt, dpkg, curl, wget |
| `opentelemetry-collector-contrib` `0.164.0-patched.1`, `0.153.0-patched.1` | none (`scratch`) | 0 | `10001:10001` | – | – |
| `splunk-otel-collector` `0.163.1-patched.1` | none (`scratch`) | 0 | `splunk-otel-collector` | – | – |
| `strimzi-maven-builder` `1.3.0-patched.4` | redhat 9.8 (UBI) | 184 | `1001` | bash | libdnf, microdnf, rpm |
| `strimzi-operator` `1.3.0-patched.5` | redhat 9.8 (UBI) | 132 | `1001` | bash | libdnf, microdnf, rpm |
| `trivy` `0.76.1-patched.4` | alpine 3.24.3 | 29 | **root** (no `USER`) | busybox | apk-tools |

What stands out:
- **Root by default:** `argoexec`, `copa`, `trivy` and both `maven` images, exactly as upstream ships them.
  - `maven` is a build image, and running builds as root is its upstream convention.
  - `copa` and `trivy` are single Go binaries that run as CLIs, and may well work unprivileged.
  - `argoexec` sets `USER 0` explicitly upstream.
  - Pods can still run them as non-root (`runAsNonRoot` with a `runAsUser`) where the program allows it.
- **A full userland where some images need it and some don't:**
  - **Need it:** `argocd` runs git, ssh, gpg, helm and kustomize. `maven` and `strimzi-maven-builder` are build images.
    Strimzi's operator is started by bash scripts. The `router` image's entrypoint is a shell script.
  - **Don't need it:** `copa`, `trivy` and the alpine `dex` are single binaries. `dex` already has a distroless
    variant.
- **Trivy's image-config checks** (`DS-*`):
  - **DS-0002 "image user should not be root":** on the 5 images above.
  - **DS-0026 "no HEALTHCHECK":** on all 20. That's expected, because Kubernetes uses probes instead.
  - **DS-0029:** on `router`. Upstream's Dockerfile runs `apt-get install` without `--no-install-recommends`.
- **Secrets:** none. Trivy's 3 hits in `strimzi-maven-builder` are the commented examples in Maven's default
  `/etc/maven/settings.xml` (`proxypass`, `repopwd`, `optional; leave empty if not used.`). Their masked lengths
  match.
- **Not checked yet: setuid/setgid binaries.** Trivy doesn't look for them, Dockle does (phase 1).

## Open-source options

| Option | What it does | License | Fit here |
|---|---|---|---|
| Trivy image-config scanning (`--image-config-scanners misconfig,secret`) | Checks the image config (root user, secrets in env, risky instructions) and the filesystem for secrets | Apache-2.0 | Already in the patcher image: one flag. Phase 1 |
| [Dockle](https://github.com/goodwithtech/dockle) | CIS Docker Benchmark image checks, including setuid/setgid files and credential files | Apache-2.0 | One more pinned tool (`tool-pins.yml` keeps it current). Phase 1 |
| A hardening overlay of our own | Strip setuid/setgid bits; set a non-root `USER` | – | One more layer in the overlay build that already adds rebuilt components and swapped jars. Phase 2 |
| [distroless](https://github.com/GoogleContainerTools/distroless) | Minimal Debian bases (`static`, `base`, `cc`, `java`) with no shell or package manager | Apache-2.0 | Upstream already uses it for 7 of our images. For single-binary images whose upstream doesn't, through `patches/`. Phase 3 |
| [Wolfi](https://github.com/wolfi-dev) + [apko](https://github.com/chainguard-dev/apko) (+ [melange](https://github.com/chainguard-dev/melange)) | Build minimal bases from a frequently patched package repository, declaratively, ourselves | Apache-2.0 | The open-source way to get hardened minimal bases without depending on a vendor's image catalog (the role Docker Hardened Images played for Strimzi). Phase 3 |
| UBI micro (`registry.access.redhat.com/ubi9/ubi-micro`) | UBI without `microdnf` or `rpm` | Red Hat UBI terms (freely redistributable) | The Strimzi images, if Strimzi's scripts run on it. Phase 3 |
| [SlimToolkit](https://github.com/slimtoolkit/slim) | Watches the container run and keeps only the files it used | Apache-2.0 | **Not for automation.** It removes whatever the probe didn't touch, which the tests here can't rule out |
| [OpenSCAP](https://www.open-scap.org/) + SCAP Security Guide | STIG and CIS profiles for RHEL/UBI images (`oscap-podman`) | LGPL-2.1 / BSD-3 | Only if an organization needs STIG evidence for the UBI-based images |
| Kubernetes Pod Security Admission (`restricted`), with [Kyverno](https://kyverno.io/) or [Gatekeeper](https://open-policy-agent.github.io/gatekeeper/) | Non-root, no privilege escalation, all capabilities dropped, seccomp `RuntimeDefault`, read-only root filesystem | Apache-2.0 | Runtime, in the clusters: no pipeline change. Kyverno's `verifyImages` or Sigstore's policy-controller can also admit only images signed by `release.yml` on `main` |

## Proposed plan

**Phase 1: measure (images unchanged).** Small: the work is a few flags, a report section and some Rego.
- Scan each final image with `--image-config-scanners misconfig,secret` as well.
- Pass these facts to the release gate's input:
  - whether the image runs as root;
  - whether it has a shell or a package manager;
  - its setuid/setgid files, from Dockle.
- The Rego policy in `policy/` then reports them as `warn` (report-only, like the gate today).
- The patch PR gets a short "Hardening" section, so every image's posture is visible before it's released.

**Phase 2: opt-in hardening in the overlay build.** Medium.
- **The setting:** a recipe sets it per image, for example `harden: {stripSetuid: true, user: "65532:65532"}`.
- **Where it runs:** the overlay that already adds components and bundled jars applies it as the last layer.
- **Checks:** smoke tests, the before/after scan and the gate check the result.
- **Rollout:**
  - Start with `stripSetuid` on the images with a full userland: low risk, since application containers don't need
    setuid.
  - Set a non-root `user` only where the program works unprivileged. Check `copa` and `trivy` first.

**Phase 3: minimal bases, one recipe at a time, through `patches/`.** Per recipe; each one is a normal patch run, with
upstream tests, smoke tests and the before/after scan.
- **Candidates:** the single-binary images whose upstream base carries a full userland (`copa`, `trivy`, the alpine
  `dex`). Each moves to distroless `static` or an apko-built Wolfi base.
- **Strimzi:** UBI micro, if its scripts run there.
- **Keep the upstream base** where the image needs its userland: `argocd`, `maven`, `strimzi-maven-builder`, `router`.

**Runtime guidance (for consumers; no pipeline change).** Document a recommended `securityContext` for each image. The
user IDs in the table above are a start. Add an admission policy example that enforces Pod Security "restricted" and
our signature (`release.yml@refs/heads/main`; [verification](../docs/runbook.md#verifying-an-image)).

| Phase | Changes images | Effort | Risk |
|---|---|---|---|
| 1. Measure | No | Small | None (report-only) |
| 2. Overlay hardening | Opt-in, per image | Medium | Low (setuid), medium (user), caught by smoke tests |
| 3. Minimal bases | Per recipe | Medium per recipe | Medium, caught by upstream and smoke tests |
| Runtime guidance | No | Small (docs) | None |

## Reproducing the audit

From any machine with Trivy and the released digests (`state/`, or the field guide's `releases.json`):

```bash
# packages (OS, shell, package manager): pulls the image's layers
trivy image --image-src remote --platform linux/amd64 --scanners vuln --pkg-types os --list-all-pkgs \
  --format json ghcr.io/<owner>/<image>@<digest>

# image config and secrets: user, DS-* checks
trivy image --image-src remote --platform linux/amd64 --scanners misconfig,secret \
  --image-config-scanners misconfig,secret --format json ghcr.io/<owner>/<image>@<digest>
```

The runtime user is also in the image config (`config.User`); an empty value means root.

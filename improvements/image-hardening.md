# Image hardening

**Status:** investigated on 2026-11-03; decision and plan on 2026-11-04 ([below](#decision-and-plan-2026-11-04)), nothing built yet.

## Summary

- **We patch, we don't harden.** The pipeline removes known vulnerabilities (dependency bumps, rebuilt bundled tools,
  swapped jars, a refreshed base, Copa), and it signs and attests what it publishes (SBOM, OpenVEX, SLSA provenance).
  It doesn't reduce what an image can do: each image keeps its upstream Dockerfile's user, base and userland.
- **Where the released images stand:**
  - On 2026-11-04, 17 of 22 run as non-root by default. On 11-03 it was 15 of 20; the two added since,
    external-secrets and trivy-operator, are both non-root.
  - On 11-03, 10 shipped no shell or package manager (distroless or `scratch`) and 10 shipped a full OS userland.
    external-secrets ships none; trivy-operator ships busybox and apk.
  - No secrets: the only hits are commented samples in Maven's default `settings.xml`.
- **Decided (2026-11-04):** enforce non-root in the clusters (Pod Security `restricted` and chart values) instead of
  rewriting images. Change images only where they stand in the way: release upstream's non-root `argoexec`, and write
  dex's, router's and splunk-otel-collector's users as numbers. The release gate reports how each image runs. Details
  and the PR plan are [below](#decision-and-plan-2026-11-04).

## Decision and plan (2026-11-04)

**Goal:** the images run as non-root, and a cluster can enforce it. Where an open-source component helps, use one;
where the pipeline already has what's needed, add nothing.

**Decision:**
- **Non-root is enforced where the pods run, not rewritten into every image.**
  - 17 of the 22 released images already run as non-root.
  - Most upstream Helm charts already set a non-root, restricted `securityContext`.
  - Kubernetes' built-in Pod Security Admission (`restricted`) enforces non-root, no privilege escalation, all
    capabilities dropped and seccomp, with nothing to install.
- **Image changes only where the image itself stands in the way, two cases:**
  - **`argoexec` runs as root.** Upstream already ships a non-root variant (the Dockerfile's `argoexec-nonroot`
    target, `USER 8737`, published as `argoexec:<version>-nonroot`). We release that variant too.
  - **dex, router and splunk-otel-collector run as a user name, not a number.** Kubernetes can't check that a name
    is non-root, so with `runAsNonRoot: true` and no `runAsUser` the kubelet refuses to start the container ("image
    has non-numeric user …, cannot verify user is non-root"). We write the same user as its number. It's the same
    UID, so nothing changes at runtime.
- **The pipeline reports how each image runs** and doesn't add a tool for it:
  - The release scan's Trivy JSON already records the image user (`Metadata.ImageConfig.config.User`).
  - The release gate warns on root and on non-numeric users, report-only like the rest of the gate today.
- **Not now:**
  - **Dockle and stripping setuid bits.** `allowPrivilegeEscalation: false`, which `restricted` requires, sets
    `no_new_privs`, so setuid bits grant nothing.
  - **SlimToolkit.** It removes whatever the probe didn't touch.
  - **Moving to minimal bases.** It stays a per-recipe option (phase 3 of the first proposal below). It isn't needed
    for non-root.
  - **Docker Hardened Images:** the owner doesn't want to depend on them.
- **One cluster-side component, optional:** admit only images `release.yml` on `main` signed.
  - [Kyverno](https://kyverno.io/) `verifyImages` if the org already runs Kyverno.
  - Otherwise Sigstore's [policy-controller](https://docs.sigstore.dev/policy-controller/overview/), the smaller,
    single-purpose choice.

**Every released image** (`state/` on `main`, measured 2026-11-04). *Runs as* is the image config's `User`. *Chart*
is the upstream Helm chart's default `securityContext`.

| Image | Runs as | Upstream chart | What we change | Risk |
|---|---|---|---|---|
| `argocd` (v3.4, v3.5) | `999` | argo-helm: non-root, read-only root, all capabilities dropped, seccomp, on every component | – | – |
| `argo-rollouts`, `kubectl-argo-rollouts` | `999` | argo-helm: non-root, read-only root, all dropped, seccomp | – | – |
| `workflow-controller`, `argocli` | `8737` | argo-helm: non-root, all dropped; no seccomp, so add `seccompProfile: RuntimeDefault` for `restricted` | – | – |
| `argoexec` | **`0`** (`USER 0` upstream) | argo-helm: `executor.securityContext: {}`. Workflow pods run as root unless configured | Also release upstream's `argoexec-nonroot` (`v4.1.6-nonroot` runs as `8737`). Point the controller at it (`executor.image`) and set `runAsNonRoot` and `runAsUser: 8737` in `workflowDefaults` | Medium: a workflow whose own image needs root (Argo's docs: even `mkdir /my-dir`) has to set `runAsUser: 0` |
| `copa` | **root** (no `USER`) | none: a CLI for CI | – (`copa --version` runs as `65532`; real runs need BuildKit's socket) | – |
| `copacetic-frontend` | `65532` | none: a BuildKit frontend | – | – |
| `dex`, `dex-distroless` | `dex:dex` (= `1001:1001`) | dexidp: none set; argo-cd's bundled dex sets `runAsUser: 1001` | `USER 1001:1001` | None: same UID |
| `external-secrets` | `65534` | non-root (`runAsUser: 1000`), read-only root, all dropped, seccomp | – | – |
| `maven` (temurin 17, 21) | **root** (no `USER`) | none: build images | – (non-root builds: `docker run -u` with `MAVEN_CONFIG`, as the official image documents) | – |
| `opentelemetry-collector-contrib` (0.153, 0.164) | `10001:10001` | none set | – (numeric already; the deployment sets `restricted` values) | – |
| `splunk-otel-collector` | `splunk-otel-collector` (= `999:999`) | `fsGroup: 999`. With log collection, an init container runs as root to `chown` host log directories (upstream's design) | `USER 999:999` | None: same UID |
| `router` | `router` (= `1000:1000`) | none set | `USER 1000:1000` | None: same UID |
| `strimzi-operator` | `1001` | non-root, read-only root, all dropped, seccomp. Kafka pods: set `STRIMZI_POD_SECURITY_PROVIDER_CLASS=restricted` (chart `extraEnvs`) | – | – |
| `strimzi-maven-builder` | `1001` | used by the operator for Kafka Connect builds | – | – |
| `trivy-operator` | `10000` | read-only root, all dropped; no `runAsNonRoot`/seccomp. Its scan jobs run the trivy image: set `trivyOperator.scanJobPodTemplatePodSecurityContext` (`runAsNonRoot: true`, `runAsUser: 10000`) | – | – |
| `trivy` | **root** (no `USER`) | trivy chart: `runAsNonRoot`, `runAsUser: 65534`, read-only root, cache volume | – (as `65532`, `trivy image` works with `--cache-dir /tmp/trivy`, also on a read-only root; the default cache under `/` fails. Filesystem scans need root, upstream says) | – |

Strimzi's Kafka image (recipe `strimzi-kafka`, first release pending) runs as `1001`, as upstream's does. `redis`
isn't released yet: upstream starts as root and its entrypoint drops to the `redis` user.

**Checks that ran:**
- **Users:** `docker buildx imagetools inspect` on every digest.
- **UIDs behind the user names:** `/etc/passwd` read out of each image (`docker create` and `docker cp`, which needs
  no shell).
- **Non-root runs:** `trivy` and `copa` run with `--user 65532:65532`.
- **Chart defaults:** each chart's `values.yaml` on its default branch.
- **Privileged ports:** none. Every exposed port is above 1024, so dropping all capabilities costs nothing.

**Plan, as PRs:**

| PR | What | Size | Changes images |
|---|---|---|---|
| 1 | `recipes/argo-workflows.yaml`: a 4th image, `argoexec` with `id: argoexec-nonroot`, `target: argoexec-nonroot` and `upstreamTag: "{{tag}}-nonroot"`, the way `dex-distroless` is a variant of `dex`. Released as `argoexec:v4.1.6-nonroot-patched.N` | Small (recipe only) | Adds one |
| 2 | A recipe `user` on an image (`"1001:1001"`: numeric and not 0, checked when the recipe loads), set as the last layer of the overlay build. It also runs for an image with no components or jars, and smoke tests run as that user. Then set it on dex (both), router and splunk-otel-collector | Small to medium | Same UID, written as a number |
| 3 | The release gate's input gets the image user from the scan; `policy/gate.rego` warns on root or a non-numeric user; the report shows "Runs as" per image | Small | No |
| 4 | `docs/running-non-root.md`: the namespace labels for `restricted` (`pod-security.kubernetes.io/enforce: restricted`, with `warn`/`audit` first), the chart values per project (the table above), and a signature admission example (Kyverno `verifyImages` / policy-controller) pinned to `release.yml@refs/heads/main` | Small (docs) | No |

Order: 1 and 3 are independent; 4 references 1 and 2. Rolling out `restricted` in a cluster: label namespaces with
`warn` and `audit` first, read what they report, then `enforce`.

**Later, only if needed:**
- A non-root `USER` on `trivy` and `copa`, if someone runs them as pods without their chart or trivy-operator.
- Minimal bases per recipe (phase 3 below).

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

## First proposal (2026-11-03)

Superseded by the [decision](#decision-and-plan-2026-11-04) where they differ: no Dockle, no setuid stripping, and
`user` only where an image's own user is root or not numeric.


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

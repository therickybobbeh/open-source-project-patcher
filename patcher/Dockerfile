# syntax=docker/dockerfile:1
# The portable patcher image: the `patcher` CLI plus every tool the pipeline shells out to (trivy, copa, cosign,
# osv-scanner, yq, crane, mise, the docker CLI with buildx and compose).
# Language toolchains (Go, Rust, JDK/Maven, Node/pnpm) are installed at runtime by mise from each
# recipe's `toolchain`, into /opt/mise (mount a cache volume there in CI).
#
# Every downloaded binary is pinned by version AND sha256 (taken from the project's own checksum
# file). Trivy's release channels were compromised in March 2026 (GHSA-69fq-xp46-6x23): never
# switch these to "latest" or unpinned downloads.
#
# Run (Docker socket needed for builds, Copa and tests that use Testcontainers/compose; mount the repo
# at the same path so the host daemon resolves bind mounts):
#   docker run --rm --network host -v /var/run/docker.sock:/var/run/docker.sock \
#     -v "$PWD:$PWD" -w "$PWD" ghcr.io/<owner>/patcher run dex --out out --workdir "$PWD/.work"
#
# Base images (FROM lines) are kept current by Dependabot; the ARG-pinned tools below by tool-pins.yml.

FROM ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 AS uv

FROM python:3.12-slim-bookworm@sha256:6dd8b6dab6b3adc7812bab69eca5dbdc1a5cc690ad28306d234ffb4ef8ac9753

ARG TARGETARCH

ARG MISE_VERSION=2026.10.8
ARG MISE_SHA256_AMD64=e908ea27810ae358c9a9a7d897ea10197bdc38d39839243e1b36acc31cbef868
ARG MISE_SHA256_ARM64=88aea77e41c2a3c45a9cbd64df9516ba887017442846213b3de178acbd3c9a46

ARG TRIVY_VERSION=0.75.0
ARG TRIVY_SHA256_AMD64=c6e65abddb348e25f10549df887045629cf28cc72453cd1c63acb717316b3f3f
ARG TRIVY_SHA256_ARM64=a1ee9f6ffb7d112b64ff726a2a0717c21175c1114361391f4a132956751a13b3

ARG COPA_VERSION=0.15.0
ARG COPA_SHA256_AMD64=cff3fe9320f3bd24bafcfd0ce877ef57e23acad0836da0ac6c253919f71c9cad
ARG COPA_SHA256_ARM64=2444b6109c6164beef980641ec5f2813bc42b1703add6dd73591ace23051ca8f

ARG COSIGN_VERSION=3.1.3
ARG COSIGN_SHA256_AMD64=4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71
ARG COSIGN_SHA256_ARM64=c5d324e091826b0d7a78eb16fef316450b4eb9aaec045611c08ba06f5e73220a

ARG OSV_SCANNER_VERSION=2.7.0
ARG OSV_SCANNER_SHA256_AMD64=160c6253e2922e9e0a6a9771c5c4c40a4b3c6090b34a3cdd5e80c96cc2e4218b
ARG OSV_SCANNER_SHA256_ARM64=4061ef4c021ed3c47f203b818f337e351336cc5cd67c0274fc36bd1dfc728dd7

ARG YQ_VERSION=4.54.1
ARG YQ_SHA256_AMD64=8e34fc298390875de416e6a4afcb8cabeceb25d9aa8506c1a2f9353cf702ea5f
ARG YQ_SHA256_ARM64=189088da0c6429ec5178dfaab1a114805f6cab0b61b165ab236efedf1d57a71b

# crane (go-containerregistry): the release's push job pushes the build jobs' image archives with it
ARG CRANE_VERSION=0.22.1
ARG CRANE_SHA256_AMD64=0ab7a1d6932a213aed964ce97666c3077fe691c8606413674a8b3e0b9ec4cda0
ARG CRANE_SHA256_ARM64=898c0cff975f898a33e8c4580bdafb0e7c02c7faa33374e946762f97c4ab7110
# OPA's CLI for policies over files: evaluates the release gate (policy/)
ARG CONFTEST_VERSION=0.71.1
ARG CONFTEST_SHA256_AMD64=c3f6b2a753bd56e377a1e51a95ae3e057f926f2e9139f7d5b5dfbbaf810f7985
ARG CONFTEST_SHA256_ARM64=218c682e110ae7e826dc14a746a6f9b43eb782643dbe730b771fd305634e3f47

SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

# (TARGETARCH is only set by BuildKit; the RUNs below fall back to dpkg for the legacy builder / podman.)
# Build/test prerequisites shared by the upstream projects:
#  gcc/clang (cgo, -race, jemalloc), protobuf-compiler, tcl/tclx (redis runtest), bats (docker-maven),
#  gnupg/git (argo-cd tests), sudo (argo-cd hack/install.sh), unzip/zip (strimzi), libdw-dev (apollo-router's
#  Linux test dependency rstack/dw-sys), docker CLI + plugins.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl git gnupg jq make gcc g++ clang lld pkg-config libssl-dev libdw-dev \
      unzip zip xz-utils file procps sudo bats tcl8.6 tclx protobuf-compiler \
 && ARCH="${TARGETARCH:-$(dpkg --print-architecture)}" \
 && install -m 0755 -d /etc/apt/keyrings \
 && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
 && echo "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" \
      > /etc/apt/sources.list.d/docker.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends docker-ce-cli docker-buildx-plugin docker-compose-plugin \
 && rm -rf /var/lib/apt/lists/*

RUN ARCH="${TARGETARCH:-$(dpkg --print-architecture)}" \
 && fetch() { curl -fsSL --retry 3 -o "$2" "$1"; echo "$3  $2" | sha256sum -c -; } \
 && pick() { [ "$ARCH" = arm64 ] && echo "$2" || echo "$1"; } \
 && cd /tmp \
 && fetch "https://github.com/jdx/mise/releases/download/v${MISE_VERSION}/mise-v${MISE_VERSION}-linux-$(pick x64 arm64).tar.gz" \
      mise.tgz "$(pick "$MISE_SHA256_AMD64" "$MISE_SHA256_ARM64")" \
 && tar -xzf mise.tgz && install -m 0755 mise/bin/mise /usr/local/bin/mise \
 && fetch "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-$(pick 64bit ARM64).tar.gz" \
      trivy.tgz "$(pick "$TRIVY_SHA256_AMD64" "$TRIVY_SHA256_ARM64")" \
 && tar -xzf trivy.tgz trivy && install -m 0755 trivy /usr/local/bin/trivy \
 && fetch "https://github.com/project-copacetic/copacetic/releases/download/v${COPA_VERSION}/copa_${COPA_VERSION}_linux_${ARCH}.tar.gz" \
      copa.tgz "$(pick "$COPA_SHA256_AMD64" "$COPA_SHA256_ARM64")" \
 && tar -xzf copa.tgz copa && install -m 0755 copa /usr/local/bin/copa \
 && fetch "https://github.com/sigstore/cosign/releases/download/v${COSIGN_VERSION}/cosign-linux-${ARCH}" \
      cosign "$(pick "$COSIGN_SHA256_AMD64" "$COSIGN_SHA256_ARM64")" \
 && install -m 0755 cosign /usr/local/bin/cosign \
 && fetch "https://github.com/google/osv-scanner/releases/download/v${OSV_SCANNER_VERSION}/osv-scanner_linux_${ARCH}" \
      osv-scanner "$(pick "$OSV_SCANNER_SHA256_AMD64" "$OSV_SCANNER_SHA256_ARM64")" \
 && install -m 0755 osv-scanner /usr/local/bin/osv-scanner \
 && fetch "https://github.com/mikefarah/yq/releases/download/v${YQ_VERSION}/yq_linux_${ARCH}" \
      yq "$(pick "$YQ_SHA256_AMD64" "$YQ_SHA256_ARM64")" \
 && install -m 0755 yq /usr/local/bin/yq \
 && fetch "https://github.com/google/go-containerregistry/releases/download/v${CRANE_VERSION}/go-containerregistry_Linux_$(pick x86_64 arm64).tar.gz" \
      crane.tgz "$(pick "$CRANE_SHA256_AMD64" "$CRANE_SHA256_ARM64")" \
 && tar -xzf crane.tgz crane && install -m 0755 crane /usr/local/bin/crane \
 && fetch "https://github.com/open-policy-agent/conftest/releases/download/v${CONFTEST_VERSION}/conftest_${CONFTEST_VERSION}_Linux_$(pick x86_64 arm64).tar.gz" \
      conftest.tgz "$(pick "$CONFTEST_SHA256_AMD64" "$CONFTEST_SHA256_ARM64")" \
 && tar -xzf conftest.tgz conftest && install -m 0755 conftest /usr/local/bin/conftest \
 && rm -rf /tmp/*

# MISE_GO_SET_GOBIN=false: `go install` goes to $GOPATH/bin (/opt/go/bin, on PATH and writable for the test user),
# not into mise's root-owned Go install dir (Argo CD's tests `go install` go-junit-report as the test user)
ENV MISE_DATA_DIR=/opt/mise \
    MISE_CACHE_DIR=/opt/mise/cache \
    MISE_YES=1 \
    MISE_EXPERIMENTAL=1 \
    MISE_GO_SET_GOBIN=false \
    TRIVY_CACHE_DIR=/opt/trivy-cache \
    TRIVY_NO_PROGRESS=true \
    GOPATH=/opt/go \
    GOMODCACHE=/opt/go/pkg/mod \
    CARGO_HOME=/opt/cargo \
    RUSTUP_HOME=/opt/rustup \
    PATH=/opt/cargo/bin:/opt/go/bin:$PATH

# The patcher runs with --network host, so containers that tests start (Testcontainers) publish their
# ports on localhost; otherwise Testcontainers dials the bridge gateway (172.17.0.1) and can't connect.
ENV TESTCONTAINERS_HOST_OVERRIDE=localhost

# Upstream checkouts are owned by whoever runs the container; don't let git refuse them.
RUN git config --system --add safe.directory '*'

# Unprivileged user for upstream test suites that assert permission errors (tests.runAs: nonroot);
# passwordless sudo because some test-tool installers call `sudo install`.
RUN useradd -m -u 1001 -s /bin/bash tester \
 && echo 'tester ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/tester && chmod 0440 /etc/sudoers.d/tester

# Third-party Python packages come from uv.lock (uv verifies its hashes; Dependabot keeps it current).
# The project itself isn't installed (that would fetch an unpinned build backend): the CLI runs from
# /opt/patcher/src through a small wrapper.
# uvx runs the pinned poetry / pipenv / pip-tools versions the Python adapter uses
COPY --from=uv /uv /uvx /usr/local/bin/
COPY pyproject.toml uv.lock /opt/patcher/
RUN cd /opt/patcher \
 && UV_PROJECT_ENVIRONMENT=/opt/venv UV_PYTHON_DOWNLOADS=never uv sync --frozen --no-dev --no-install-project
COPY src /opt/patcher/src
# (no PYTHONPATH/venv on PATH: upstream builds and tests run from this process and must not see them)
RUN printf '%s\n' '#!/bin/sh' \
      'exec /opt/venv/bin/python -c "import sys; sys.path.insert(0, \"/opt/patcher/src\"); from patcher.cli import app; app(prog_name=\"patcher\")" "$@"' \
      > /usr/local/bin/patcher \
 && chmod 0755 /usr/local/bin/patcher \
 && patcher --help >/dev/null

WORKDIR /work
ENTRYPOINT ["patcher"]

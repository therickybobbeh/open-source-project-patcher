#!/usr/bin/env bash
# Run one `patcher` command inside the patcher image, exactly as CI does (.github/actions/run-patcher
# calls this script):
#   - the Docker socket and host networking, for builds, Copa and test containers (Testcontainers,
#     compose services) that must be reachable on localhost;
#   - the repo mounted at the same path, so bind mounts resolve identically on host and container;
#   - toolchain, module and Trivy DB caches that survive between runs;
#   - a work dir for upstream checkouts: by default the Docker volume `patcher-work` (on macOS, bind
#     mounts don't enforce file permissions, which some upstream suites test).
#
#   scripts/patcher-docker.sh run dex --out out
#   PATCHER_IMAGE=ghcr.io/<owner>/patcher:latest scripts/patcher-docker.sh validate
#
# Environment:
#   PATCHER_IMAGE  image to run (default patcher:dev; build it with `docker build -t patcher:dev patcher`)
#   PATCHER_CACHE  host dir for caches (default ~/.cache/support-images)
#   PATCHER_WORK   work dir: a Docker volume name, or an absolute host path mounted at the same path
#                  (default: volume patcher-work)
#   PATCHER_DOCKER_CONFIG  Docker config dir with registry logins (default ~/.docker). On macOS, Docker
#                  Desktop's config uses a credential helper that doesn't exist in the container: point
#                  this at a dir whose config.json has plain `auths` (or `{}` for public images only)
#   PATCHER_REGISTRY_BASIC_AUTH, PATCHER_REGISTRY_AUTH_HOST  passed through: credentials for one private registry's
#                  base-image lookups (see the runbook)
#   PATCHER_PLATFORMS  passed through: build and release only these platforms, e.g. linux/arm64 (see the runbook)
set -euo pipefail

repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
image=${PATCHER_IMAGE:-patcher:dev}
cache=${PATCHER_CACHE:-$HOME/.cache/support-images}
work=${PATCHER_WORK:-patcher-work}
docker_config=${PATCHER_DOCKER_CONFIG:-$HOME/.docker}

mkdir -p "$cache"/{mise,go,cargo,rustup,m2,gradle,npm,uv,trivy} "$docker_config"
if [[ "$work" == /* ]]; then
  mkdir -p "$work"
  work_mount="$work:$work" workdir="$work"
else
  work_mount="$work:/work-vol" workdir=/work-vol
fi

# From a git worktree, .git is a file pointing into the main checkout's .git, outside the mounted repo: mount
# that directory too (read-only), or every git command in the container fails with "not a git repository".
git_mount=()
common=$(cd "$repo" && git rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)
if [[ -n "$common" && "$common" != "$repo"/* ]]; then git_mount=(-v "$common:$common:ro"); fi

exec docker run --rm --network host \
  -e PATCHER_REGISTRY -e PATCHER_REGISTRY_BASIC_AUTH -e PATCHER_REGISTRY_AUTH_HOST -e PATCHER_PLATFORMS -e GITHUB_ACTIONS \
  -e PATCHER_WORKDIR="$workdir" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$docker_config:/root/.docker" \
  -v "$repo:$repo" -w "$repo" ${git_mount[@]+"${git_mount[@]}"} \
  -v "$work_mount" \
  -v "$cache/mise:/opt/mise" -v "$cache/go:/opt/go" -v "$cache/cargo:/opt/cargo" -v "$cache/rustup:/opt/rustup" \
  -v "$cache/m2:/root/.m2" -v "$cache/gradle:/root/.gradle" -v "$cache/npm:/root/.npm" -v "$cache/uv:/root/.cache/uv" \
  -v "$cache/trivy:/opt/trivy-cache" \
  "$image" "$@"

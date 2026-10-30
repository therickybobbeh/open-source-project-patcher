#!/usr/bin/env bash
# check-runner-pools.sh: once the trusted jobs move to self-hosted runners, the runners for code we don't vet
# (upstream builds and tests, PR code) must be chosen explicitly. Those jobs never fall back to the trusted pool
# (PATCHER_RUNS_ON*), which holds registry, signing and GitHub App credentials. Left unset they would run on
# GitHub-hosted runners, which a self-hosted setup may not allow or want, so the run stops here instead:
#   PATCHER_RUNS_ON set, PATCHER_RUNS_ON_UPSTREAM unset              -> error
#   PATCHER_RUNS_ON_ARM64 set, PATCHER_RUNS_ON_UPSTREAM_ARM64 unset  -> error
#   an upstream pool equal to its trusted pool                      -> warning (allowed, but the pools are shared)
# Reads the four variables from the environment; patch.yml, release.yml and patcher-image.yml pass `vars`.
set -euo pipefail
status=0

check() {  # <trusted variable> <upstream variable> <GitHub-hosted label>
  local trusted=${!1:-} upstream=${!2:-}
  if [ -n "$trusted" ] && [ -z "$upstream" ]; then
    echo "::error::$1 is set but $2 is not. Jobs that run upstream code never use the $1 runners, which hold credentials: set $2 to a separate, ephemeral pool, or to '\"$3\"' to run them on GitHub-hosted runners."
    status=1
  elif [ -n "$trusted" ] && [ "$trusted" = "$upstream" ]; then
    echo "::warning::$2 equals $1: upstream builds share runners with the jobs that hold registry, signing and GitHub App credentials. Use a separate, ephemeral pool."
  fi
}

check PATCHER_RUNS_ON PATCHER_RUNS_ON_UPSTREAM ubuntu-24.04
check PATCHER_RUNS_ON_ARM64 PATCHER_RUNS_ON_UPSTREAM_ARM64 ubuntu-24.04-arm
exit $status

#!/usr/bin/env bash
# retry.sh <attempts> <command...>: run a command until it succeeds, waiting 15s, 30s, … between tries.
# For calls to flaky public services, such as cosign's Sigstore uploads. A Rekor `409 createLogEntryConflict`
# means an earlier attempt's upload landed although the client timed out; the next attempt signs with a
# fresh key, so it doesn't conflict.
set -uo pipefail
attempts=$1
shift
for ((i = 1; i <= attempts; i++)); do
  "$@" && exit 0
  status=$?
  if ((i < attempts)); then
    echo "::warning::attempt $i/$attempts failed (exit $status): $1; retrying in $((i * 15))s"
    sleep $((i * 15))
  fi
done
exit "$status"

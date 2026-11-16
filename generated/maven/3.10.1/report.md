## ❌ maven `3.10.1` — build-failed

Upstream: https://github.com/carlossg/docker-maven @ `df38874f9f3e` (line `maven3`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 0 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| dockerfile | `eclipse-temurin-17-noble/Dockerfile` | `eclipse-temurin` | `eclipse-temurin:17-jdk-noble` | `eclipse-temurin:17-jdk-noble@sha256:1bedb04434bd275ef072355e9caec2a22be5240fbe82ad51a59323f2bbcab4a6` | base image refresh |
| dockerfile | `eclipse-temurin-17-noble/Dockerfile` | `eclipse-temurin` | `eclipse-temurin:17-jdk-noble` | `eclipse-temurin:17-jdk-noble@sha256:1bedb04434bd275ef072355e9caec2a22be5240fbe82ad51a59323f2bbcab4a6` | base image refresh |
| dockerfile | `eclipse-temurin-21-noble/Dockerfile` | `eclipse-temurin` | `eclipse-temurin:21-jdk-noble` | `eclipse-temurin:21-jdk-noble@sha256:06c1f157dacf6b68198bd9a4186dd4c34ef24e65d7bbbe2a0cf8e62571ad38c9` | base image refresh |

### Upstream tests

✅ passed in 1.5 min — `for t in eclipse-temurin-21-noble eclipse-temurin-17-noble; do TAG=$t bats tests/tests.bats ; done`

### Notes

- Maven's own jars (/usr/share/maven) only change with a Maven release (upstream's update-maven-version.sh). Until then, vulnerable ones are swapped for fixed releases from Maven Central (`bundledJars`); a swapped jar keeps its old file name.
- build failed: command failed (1): docker buildx build --platform linux/amd64 -t patcher.local/maven:3.10.1-eclipse-temurin-21-noble-patched.dev --provenance=false -f /home/runner/work/_temp/work/maven/maven3/src/eclipse-temurin-21-noble/Dockerfile --label org.opencontainers.image.revision=df38874f9f3e752a3a67bfd6

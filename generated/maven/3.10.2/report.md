## ❌ maven `3.10.2` — build-failed

Upstream: https://github.com/carlossg/docker-maven @ `69c1dbbba874` (line `maven3`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 0 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| dockerfile | `eclipse-temurin-17-noble/Dockerfile` | `eclipse-temurin` | `eclipse-temurin:17-jdk-noble` | `eclipse-temurin:17-jdk-noble@sha256:bdd7eeee8f2259194d39a9525f09abfddcb97a7bdc6fcd97de6f83652e80f772` | base image refresh |
| dockerfile | `eclipse-temurin-17-noble/Dockerfile` | `eclipse-temurin` | `eclipse-temurin:17-jdk-noble` | `eclipse-temurin:17-jdk-noble@sha256:bdd7eeee8f2259194d39a9525f09abfddcb97a7bdc6fcd97de6f83652e80f772` | base image refresh |
| dockerfile | `eclipse-temurin-21-noble/Dockerfile` | `eclipse-temurin` | `eclipse-temurin:21-jdk-noble` | `eclipse-temurin:21-jdk-noble@sha256:a09e64f4976df9c4f2029c6abe64fc26f069a342ec9a7f147dce7b1933ebda16` | base image refresh |

### Upstream tests

✅ passed in 1.3 min — `for t in eclipse-temurin-21-noble eclipse-temurin-17-noble; do TAG=$t bats tests/tests.bats ; done`

### Notes

- Maven's own jars (/usr/share/maven) only change with a Maven release (upstream's update-maven-version.sh). Until then, vulnerable ones are swapped for fixed releases from Maven Central (`bundledJars`); a swapped jar keeps its old file name.
- build failed: command failed (1): docker buildx build --platform linux/amd64 -t patcher.local/maven:3.10.2-eclipse-temurin-21-noble-patched.dev --provenance=false -f /home/runner/work/_temp/work/maven/maven3/src/eclipse-temurin-21-noble/Dockerfile --label org.opencontainers.image.revision=69c1dbbba87486aff61b420f

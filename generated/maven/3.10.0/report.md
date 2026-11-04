## ✅ maven `3.10.0` — success

Upstream: https://github.com/carlossg/docker-maven @ `ac3508748c68` (line `maven3`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 0 |
| image `maven-temurin-21-noble` | 0 / 1 / 7 / 0 | 0 / 0 / 0 / 0 | 8 | 0 |
| image `maven-temurin-17-noble` | 0 / 1 / 7 / 0 | 0 / 0 / 0 / 0 | 8 | 0 |

### Release gate (reported only (`gate.enforce: false`))

- image `maven-temurin-21-noble`: ✅ passes
- image `maven-temurin-17-noble`: ✅ passes

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| dockerfile | `eclipse-temurin-17-noble/Dockerfile` | `eclipse-temurin` | `eclipse-temurin:17-jdk-noble` | `eclipse-temurin:17-jdk-noble@sha256:1c679e2dedde845115a77b5fbe41a84bfdb3a5d2d5294128edc39ccc9bd08433` | base image refresh |
| dockerfile | `eclipse-temurin-17-noble/Dockerfile` | `eclipse-temurin` | `eclipse-temurin:17-jdk-noble` | `eclipse-temurin:17-jdk-noble@sha256:1c679e2dedde845115a77b5fbe41a84bfdb3a5d2d5294128edc39ccc9bd08433` | base image refresh |
| dockerfile | `eclipse-temurin-21-noble/Dockerfile` | `eclipse-temurin` | `eclipse-temurin:21-jdk-noble` | `eclipse-temurin:21-jdk-noble@sha256:114cabb73033ca4ce7ceec3deb62396bc1b716282bae051ed3c1d82e38fcab2d` | base image refresh |

### Bundled jars swapped

Replaced with the fixed release from Maven Central, pinned by sha256 (`jars.json`; the release re-applies exactly these). Each jar keeps its old file name, with the new release as its content.

| Image | Jar | Coordinates | From → To | Fixes | sha256 |
|---|---|---|---|---|---|
| maven-temurin-21-noble, maven-temurin-17-noble | `usr/share/maven/lib/guava-33.7.1-jre.jar` | `com.google.guava:guava` | `33.7.1-jre` → `33.7.2-jre` | CVE-2026-102554 | `b530942257fb935f8b2cfaa5f8eb5bd59c555fd8e8d01b8ce98912e077ea606c` |

### Upstream tests

✅ passed in 1.4 min — `for t in eclipse-temurin-21-noble eclipse-temurin-17-noble; do TAG=$t bats tests/tests.bats ; done`

### Images

| Image | Ref | Smoke | Copa |
|---|---|---|---|
| maven-temurin-21-noble | `patcher.local/maven:3.10.0-eclipse-temurin-21-noble-patched.dev-copa` | ✅ `mvn -v`, ✅ `mvn -B -emp smoke` | patched (OS): 7 total, 7 patched, 0 skipped |
| maven-temurin-17-noble | `patcher.local/maven:3.10.0-eclipse-temurin-17-noble-patched.dev-copa` | ✅ `mvn -v`, ✅ `mvn -B -emp smoke` | patched (OS): 7 total, 7 patched, 0 skipped |

### Notes

- Maven's own jars (/usr/share/maven) only change with a Maven release (upstream's update-maven-version.sh). Until then, vulnerable ones are swapped for fixed releases from Maven Central (`bundledJars`); a swapped jar keeps its old file name.

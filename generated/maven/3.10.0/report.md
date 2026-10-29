## ✅ maven `3.10.0` — success

Upstream: https://github.com/carlossg/docker-maven @ `8ef234bed02d` (line `maven3`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 0 |
| image `maven-temurin-21-noble` | 0 / 1 / 0 / 0 | 0 / 0 / 0 / 0 | 1 | 0 |
| image `maven-temurin-17-noble` | 0 / 1 / 0 / 0 | 0 / 0 / 0 / 0 | 1 | 0 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| dockerfile | `eclipse-temurin-17-noble/Dockerfile` | `eclipse-temurin` | `eclipse-temurin:17-jdk-noble` | `eclipse-temurin:17-jdk-noble@sha256:78dde986267ae7cac62fe7ef624c2a5cee2036b6822933d39fd3870618b91526` | base image refresh |
| dockerfile | `eclipse-temurin-17-noble/Dockerfile` | `eclipse-temurin` | `eclipse-temurin:17-jdk-noble` | `eclipse-temurin:17-jdk-noble@sha256:78dde986267ae7cac62fe7ef624c2a5cee2036b6822933d39fd3870618b91526` | base image refresh |
| dockerfile | `eclipse-temurin-21-noble/Dockerfile` | `eclipse-temurin` | `eclipse-temurin:21-jdk-noble` | `eclipse-temurin:21-jdk-noble@sha256:57424b1d8eca9c4cf8a4fe226207027911f08d6758628891bf59fcfb53777029` | base image refresh |

### Bundled jars swapped

Replaced with the fixed release from Maven Central, pinned by sha256 (`jars.json`; the release re-applies exactly these). Each jar keeps its old file name, with the new release as its content.

| Image | Jar | Coordinates | From → To | Fixes | sha256 |
|---|---|---|---|---|---|
| maven-temurin-21-noble, maven-temurin-17-noble | `usr/share/maven/lib/guava-33.7.1-jre.jar` | `com.google.guava:guava` | `33.7.1-jre` → `33.7.2-jre` | CVE-2026-102554 | `b530942257fb935f8b2cfaa5f8eb5bd59c555fd8e8d01b8ce98912e077ea606c` |

### Upstream tests

✅ passed in 1.5 min — `for t in eclipse-temurin-21-noble eclipse-temurin-17-noble; do TAG=$t bats tests/tests.bats ; done`

### Images

| Image | Ref | Smoke | Copa |
|---|---|---|---|
| maven-temurin-21-noble | `patcher.local/maven:3.10.0-eclipse-temurin-21-noble-patched.dev` | ✅ `mvn -v`, ✅ `mvn -B -emp smoke` | no fixable OS packages |
| maven-temurin-17-noble | `patcher.local/maven:3.10.0-eclipse-temurin-17-noble-patched.dev` | ✅ `mvn -v`, ✅ `mvn -B -emp smoke` | no fixable OS packages |

### Notes

- Maven's own jars (/usr/share/maven) only change with a Maven release (upstream's update-maven-version.sh). Until then, vulnerable ones are swapped for fixed releases from Maven Central (`bundledJars`); a swapped jar keeps its old file name.

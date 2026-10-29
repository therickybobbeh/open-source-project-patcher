## ✅ strimzi `1.3.0` — success

Upstream: https://github.com/strimzi/strimzi-kafka-operator @ `0d138c48b936` (line `1`)
Attempts: full plan: tests passed → full plan + image findings: tests passed

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 21 / 35 / 7 | 0 / 0 / 0 / 0 | 63 | 0 |
| image `strimzi-operator` | 1 / 18 / 17 / 5 | 0 / 0 / 0 / 0 | 41 | 0 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| maven | `pom.xml` | `at.yawk.lz4:lz4-java` | `1.10.2` | `1.11.4` | CVE-2026-106449, CVE-2026-106450, CVE-2026-106451, CVE-2026-106452, CVE-2026-106453, CVE-2026-59949 |
| maven | `pom.xml` | `org.xerial.snappy:snappy-java` | `1.1.10.7` | `1.1.10.9` | CVE-2026-108106, CVE-2026-116590, CVE-2026-93451 |
| maven | `pom.xml` | `tools.jackson.core:jackson-core` | `3.1.6` | `3.1.7` | CVE-2026-89407, CVE-2026-89425 |
| maven | `pom.xml` | `tools.jackson.core:jackson-databind` | `3.1.6` | `3.1.7` | CVE-2026-91776, CVE-2026-91777 |
| dockerfile | `docker-images/base/Dockerfile` | `registry.access.redhat.com/ubi9/ubi-minimal` | `ubi-minimal:latest` | `ubi-minimal:latest@sha256:6f3a78179e0b30b930a186e7f68a4af52e51bb82406c9653be10bddd624e40f5` | base image refresh |
| dockerfile | `docker-images/base/Dockerfile` | `registry.access.redhat.com/ubi9/ubi-minimal` | `ubi-minimal:latest` | `ubi-minimal:latest@sha256:6f3a78179e0b30b930a186e7f68a4af52e51bb82406c9653be10bddd624e40f5` | base image refresh |

### Upstream tests

✅ passed in 13.8 min — `mvn -B -ntp -DskipITs -Dsurefire.rerunFailingTestsCount=2 -pl '!systemtest'  install`

### Images

| Image | Ref | Smoke | Copa |
|---|---|---|---|
| strimzi-operator | `patcher.local/strimzi-operator:1.3.0-patched.dev` | - | no fixable OS packages |

### Notes

- Kafka broker images (quay.io/strimzi/kafka) embed the Apache Kafka binary tarball; their jars can't be bumped through the POMs. Add a separate recipe line if those images need Copa/base refreshes.
- The maven-builder image is its own recipe (strimzi-maven-builder).

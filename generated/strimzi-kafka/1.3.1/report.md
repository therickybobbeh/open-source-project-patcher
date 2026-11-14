## ✅ strimzi-kafka `1.3.1` — success

Upstream: https://github.com/strimzi/strimzi-kafka-operator @ `555c3e0f07c2` (line `1`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 1 / 1 / 0 | 0 / 0 / 1 / 0 | 1 | 0 |
| image `strimzi-kafka` | 0 / 50 / 93 / 7 | 0 / 25 / 28 / 1 | 120 | 23 |

### Release gate (reported only (`gate.enforce: false`))

- image `strimzi-kafka`: ✅ passes

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| maven | `docker-images/artifacts/kafka-thirdparty-libs/4.3.2/pom.xml` | `com.google.guava:guava` | `33.5.0-android` | `33.7.2-android` | CVE-2026-102554, override: CVE-2026-102554 is fixed in 33.7.2, published as 33.7.2-android (the flavor the add-ons use) |
| dockerfile | `docker-images/base/Dockerfile` | `registry.access.redhat.com/ubi9/ubi-minimal` | `ubi-minimal:latest` | `ubi-minimal:latest@sha256:baafce2d34783a28b4a472779f304e97e00f9d35c99553bc53b068b14344d9a9` | base image refresh |
| dockerfile | `docker-images/base/Dockerfile` | `registry.access.redhat.com/ubi9/ubi-minimal` | `ubi-minimal:latest` | `ubi-minimal:latest@sha256:baafce2d34783a28b4a472779f304e97e00f9d35c99553bc53b068b14344d9a9` | base image refresh |

### Still fixable after patching

| Severity | Vulnerability | Package | Installed | Fixed in | Where | Reason |
|---|---|---|---|---|---|---|
| HIGH | CVE-2026-106451 | `at.yawk.lz4:lz4-java` | `1.10.2` | `1.11.4` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/lz4-java-1.10.2.jar` (not built from this source) |
| HIGH | CVE-2026-89407 | `com.fasterxml.jackson.core:jackson-core` | `2.21.6` | `2.18.11, 2.21.7, 2.22.3` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/jackson-core-2.21.6.jar` (not built from this source) |
| HIGH | CVE-2026-89425 | `com.fasterxml.jackson.core:jackson-core` | `2.21.6` | `2.21.7, 2.22.3, 2.18.11` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/jackson-core-2.21.6.jar` (not built from this source) |
| HIGH | CVE-2026-54512 | `com.fasterxml.jackson.core:jackson-databind` | `2.21.1` | `2.18.8, 3.1.4, 2.21.4` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/jackson-databind-2.21.1.jar` (not built from this source) |
| HIGH | CVE-2026-54513 | `com.fasterxml.jackson.core:jackson-databind` | `2.21.1` | `2.18.8, 2.21.4, 3.1.4` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/jackson-databind-2.21.1.jar` (not built from this source) |
| HIGH | CVE-2026-68497 | `com.fasterxml.jackson.core:jackson-databind` | `2.21.1` | `2.18.10, 2.21.6, 2.22.2` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/jackson-databind-2.21.1.jar` (not built from this source) |
| HIGH | CVE-2026-91776 | `com.fasterxml.jackson.core:jackson-databind` | `2.21.1` | `2.18.11, 2.21.7, 2.22.3` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/jackson-databind-2.21.1.jar` (not built from this source) |
| HIGH | CVE-2026-91777 | `com.fasterxml.jackson.core:jackson-databind` | `2.21.1` | `2.21.7, 2.18.11, 2.22.3` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/jackson-databind-2.21.1.jar` (not built from this source) |
| HIGH | CVE-2026-102554 | `com.google.guava:guava` | `32.1.3-jre` | `33.7.2` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/guava-32.1.3-jre.jar` (not built from this source) |
| HIGH | CVE-2026-107364 | `krb5-libs` | `1.21.1-10.el9_8.1` | `1.21.1-10.el9_9.2` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| HIGH | CVE-2026-112315 | `krb5-libs` | `1.21.1-10.el9_8.1` | `1.21.1-10.el9_9.2` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| HIGH | CVE-2026-112316 | `krb5-libs` | `1.21.1-10.el9_8.1` | `1.21.1-10.el9_9.2` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| HIGH | CVE-2026-112317 | `krb5-libs` | `1.21.1-10.el9_8.1` | `1.21.1-10.el9_9.2` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| HIGH | CVE-2026-112318 | `krb5-libs` | `1.21.1-10.el9_8.1` | `1.21.1-10.el9_9.2` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| HIGH | CVE-2026-112319 | `krb5-libs` | `1.21.1-10.el9_8.1` | `1.21.1-10.el9_9.2` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| HIGH | CVE-2026-112320 | `krb5-libs` | `1.21.1-10.el9_8.1` | `1.21.1-10.el9_9.2` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| HIGH | CVE-2026-112321 | `krb5-libs` | `1.21.1-10.el9_8.1` | `1.21.1-10.el9_9.2` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| HIGH | CVE-2026-112322 | `krb5-libs` | `1.21.1-10.el9_8.1` | `1.21.1-10.el9_9.2` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| HIGH | CVE-2026-112323 | `krb5-libs` | `1.21.1-10.el9_8.1` | `1.21.1-10.el9_9.2` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| HIGH | CVE-2026-118380 | `krb5-libs` | `1.21.1-10.el9_8.1` | `1.21.1-10.el9_9.2` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| HIGH | CVE-2026-119079 | `krb5-libs` | `1.21.1-10.el9_8.1` | `1.21.1-10.el9_9.2` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| HIGH | CVE-2026-71199 | `krb5-libs` | `1.21.1-10.el9_8.1` | `1.21.1-10.el9_9.2` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| HIGH | CVE-2026-71200 | `krb5-libs` | `1.21.1-10.el9_8.1` | `1.21.1-10.el9_9.2` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| HIGH | CVE-2026-108106 | `org.xerial.snappy:snappy-java` | `1.1.10.5` | `1.1.10.9` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/snappy-java-1.1.10.5.jar` (not built from this source) |
| HIGH | CVE-2026-93451 | `org.xerial.snappy:snappy-java` | `1.1.10.5` | `1.1.10.9` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/snappy-java-1.1.10.5.jar` (not built from this source) |
| MEDIUM | CVE-2026-106450 | `at.yawk.lz4:lz4-java` | `1.10.2` | `1.11.4` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/lz4-java-1.10.2.jar` (not built from this source) |
| MEDIUM | CVE-2026-106452 | `at.yawk.lz4:lz4-java` | `1.10.2` | `1.11.2` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/lz4-java-1.10.2.jar` (not built from this source) |
| MEDIUM | CVE-2026-106453 | `at.yawk.lz4:lz4-java` | `1.10.2` | `1.11.2` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/lz4-java-1.10.2.jar` (not built from this source) |
| MEDIUM | CVE-2026-59949 | `at.yawk.lz4:lz4-java` | `1.10.2` | `1.11.1` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/lz4-java-1.10.2.jar` (not built from this source) |
| MEDIUM | CVE-2026-19032 | `com.fasterxml.jackson.core:jackson-databind` | `2.21.1` | `2.18.10, 2.21.6, 2.22.2` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/jackson-databind-2.21.1.jar` (not built from this source) |
| MEDIUM | CVE-2026-54514 | `com.fasterxml.jackson.core:jackson-databind` | `2.21.1` | `2.18.8, 2.21.4` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/jackson-databind-2.21.1.jar` (not built from this source) |
| MEDIUM | CVE-2026-54515 | `com.fasterxml.jackson.core:jackson-databind` | `2.21.1` | `3.1.4, 2.18.9, 2.21.5, 2.22.1` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/jackson-databind-2.21.1.jar` (not built from this source) |
| MEDIUM | CVE-2026-54516 | `com.fasterxml.jackson.core:jackson-databind` | `2.21.1` | `2.21.4, 3.1.4` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/jackson-databind-2.21.1.jar` (not built from this source) |
| MEDIUM | CVE-2026-54517 | `com.fasterxml.jackson.core:jackson-databind` | `2.21.1` | `2.21.4, 3.1.4` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/jackson-databind-2.21.1.jar` (not built from this source) |
| MEDIUM | CVE-2026-54518 | `com.fasterxml.jackson.core:jackson-databind` | `2.21.1` | `2.21.4` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/jackson-databind-2.21.1.jar` (not built from this source) |
| MEDIUM | CVE-2026-59888 | `com.fasterxml.jackson.core:jackson-databind` | `2.21.1` | `2.18.8, 2.21.4` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/jackson-databind-2.21.1.jar` (not built from this source) |
| MEDIUM | CVE-2026-59889 | `com.fasterxml.jackson.core:jackson-databind` | `2.21.1` | `2.21.5, 2.18.9, 2.22.1` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/jackson-databind-2.21.1.jar` (not built from this source) |
| MEDIUM | CVE-2026-77310 | `com.fasterxml.jackson.core:jackson-databind` | `2.21.1` | `2.18.9, 2.21.5, 2.22.1` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/jackson-databind-2.21.1.jar` (not built from this source) |
| MEDIUM | CVE-2026-83557 | `com.fasterxml.jackson.core:jackson-databind` | `2.21.1` | `2.18.10, 2.21.6, 2.22.2` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/jackson-databind-2.21.1.jar` (not built from this source) |
| MEDIUM | GHSA-mhm7-754m-9p8w | `com.fasterxml.jackson.core:jackson-databind` | `2.21.1` | `2.18.9, 2.21.5` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/jackson-databind-2.21.1.jar` (not built from this source) |
| MEDIUM | CVE-2026-118259 | `io.opentelemetry:opentelemetry-api` | `1.63.0` | `1.67.0` | source (`trivy fs`): `docker-images/artifacts/kafka-thirdparty-libs/4.3.2/pom.xml` | held: its version is a property shared by five OpenTelemetry artifacts, which the maven adapter can't move for one |
| MEDIUM | CVE-2026-118259 | `io.opentelemetry:opentelemetry-api` | `1.63.0` | `1.67.0` | image `strimzi-kafka` | bundled jar: held: its version is a property shared by five OpenTelemetry artifacts, which the maven adapter can't move for one |
| MEDIUM | CVE-2026-107708 | `krb5-libs` | `1.21.1-10.el9_8.1` | `1.21.1-10.el9_9.2` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| MEDIUM | CVE-2026-107778 | `krb5-libs` | `1.21.1-10.el9_8.1` | `1.21.1-10.el9_9.2` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| MEDIUM | CVE-2026-107884 | `krb5-libs` | `1.21.1-10.el9_8.1` | `1.21.1-10.el9_9.2` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| MEDIUM | CVE-2026-111423 | `krb5-libs` | `1.21.1-10.el9_8.1` | `1.21.1-10.el9_9.2` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| MEDIUM | CVE-2026-112314 | `krb5-libs` | `1.21.1-10.el9_8.1` | `1.21.1-10.el9_9.2` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| MEDIUM | CVE-2026-49844 | `org.apache.logging.log4j:log4j-api` | `2.25.4` | `2.25.5, 2.26.1` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/log4j-api-2.25.4.jar` (not built from this source) |
| MEDIUM | CVE-2026-59171 | `org.json:json` | `20231013` | `20260719` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/json-20231013.jar` (not built from this source) |
| MEDIUM | CVE-2026-116590 | `org.xerial.snappy:snappy-java` | `1.1.10.5` | `1.1.10.9` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/snappy-java-1.1.10.5.jar` (not built from this source) |
| MEDIUM | CVE-2026-78367 | `rpm` | `4.16.1.3-40.el9` | `4.16.1.3-43.el9_9` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| MEDIUM | CVE-2026-84837 | `rpm` | `4.16.1.3-40.el9` | `4.16.1.3-43.el9_9` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| MEDIUM | CVE-2026-78367 | `rpm-libs` | `4.16.1.3-40.el9` | `4.16.1.3-43.el9_9` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| MEDIUM | CVE-2026-84837 | `rpm-libs` | `4.16.1.3-40.el9` | `4.16.1.3-43.el9_9` | image `strimzi-kafka` | Copa failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for updat |
| LOW | CVE-2026-106449 | `at.yawk.lz4:lz4-java` | `1.10.2` | `1.11.4` | image `strimzi-kafka` | in bundled artifact `opt/cruise-control/libs/lz4-java-1.10.2.jar` (not built from this source) |
| UNKNOWN | GO-2026-5932 | `golang.org/x/crypto` | `v0.58.0` | `0.58.1-0.20261009181718-2f1f834330b2` | image `strimzi-kafka` | component `kafka-exporter` (rebuilt from source): cooldown: v0.59.0 released 3 day(s) ago (eligible 2026-11-18) |

### Upstream tests

Not run.

### Images

| Image | Ref | Runs as | Smoke | Copa |
|---|---|---|---|---|
| strimzi-kafka | `patcher.local/strimzi-kafka:1.3.1-kafka-4.3.2-patched.dev` | `1001` | ✅ `bash -c 'touch /tmp/agent.properties && KAFKA_OPTS="-javaagent:$(ls /opt/kafka/libs/kafka-agent-*.jar)=/tmp/agent.properties" /opt/kafka/bin/kafka-storage.sh random-uuid'`, ✅ `/opt/kafka-exporter/kafka_exporter --version` | failed: time="2026-11-14T12:38:52Z" level=error msg="downloaded package krb5-libs version 1.21.1-10.el9_8.1 lower than required 1.21.1-10.el9_9.2 for update" |

### Bundled components (rebuilt from source and swapped in)

| Image | Component | Path | Version | Status | Bumps | Tests | Notes |
|---|---|---|---|---|---|---|---|
| strimzi-kafka | kafka-exporter | `/opt/kafka-exporter/kafka_exporter` | 1.11.0 | success | 1 | passed | version from Go build info |

### Notes

- Only Strimzi's default Kafka version is built, the one in the image tag. When Strimzi moves its default, the build stops at its first step and prints the two `vars` to set in the recipe.
- No upstream tests cover this image (Strimzi tests it with system tests on a cluster); the checks are upstream's classpath-collision check in the build and the smoke tests.
- Cruise Control's libraries (/opt/cruise-control/libs) are not bumped, as upstream doesn't override them (it can't test Cruise Control); their findings stay in the report.
- release date of com.google.guava:guava 33.7.2 unknown; bumped without the 7-day age check

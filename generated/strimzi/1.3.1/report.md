## ✅ strimzi `1.3.1` — success

Upstream: https://github.com/strimzi/strimzi-kafka-operator @ `555c3e0f07c2` (line `1`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 0 |
| image `strimzi-operator` | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 0 |

### Release gate (reported only (`gate.enforce: false`))

- image `strimzi-operator`: ✅ passes

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| dockerfile | `docker-images/base/Dockerfile` | `registry.access.redhat.com/ubi9/ubi-minimal` | `ubi-minimal:latest` | `ubi-minimal:latest@sha256:dfa0eb04abc59221544e74862432496add1f491f915c9b531880f91affc0e12c` | base image refresh |
| dockerfile | `docker-images/base/Dockerfile` | `registry.access.redhat.com/ubi9/ubi-minimal` | `ubi-minimal:latest` | `ubi-minimal:latest@sha256:dfa0eb04abc59221544e74862432496add1f491f915c9b531880f91affc0e12c` | base image refresh |

### Upstream tests

✅ passed in 14.1 min — `mvn -B -ntp -DskipITs -Dsurefire.rerunFailingTestsCount=2 -pl '!systemtest'  install`

### Images

| Image | Ref | Smoke | Copa |
|---|---|---|---|
| strimzi-operator | `patcher.local/strimzi-operator:1.3.1-patched.dev` | - | no fixable OS packages |

### Notes

- The Kafka image (quay.io/strimzi/kafka, Strimzi's default Kafka version) is its own recipe (strimzi-kafka).
- The maven-builder image is its own recipe (strimzi-maven-builder).

## ✅ strimzi-maven-builder `1.3.0` — success

Upstream: https://github.com/strimzi/strimzi-kafka-operator @ `0d138c48b936` (line `1`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 0 |
| image `strimzi-maven-builder` | 1 / 11 / 12 / 4 | 0 / 0 / 0 / 0 | 28 | 0 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| dockerfile | `docker-images/maven-builder/Dockerfile` | `registry.access.redhat.com/ubi9/openjdk-21` | `openjdk-21:1.24` | `openjdk-21:1.24@sha256:66175ec6c53f655a24c1c3f81c52b3e281c6918c917435b1014eb75cd11fbe75` | base image refresh |

### Upstream tests

Not run.

### Images

| Image | Ref | Smoke | Copa |
|---|---|---|---|
| strimzi-maven-builder | `patcher.local/strimzi-maven-builder:1.3.0-patched.dev` | ✅ `mvn -v` | no fixable OS packages |

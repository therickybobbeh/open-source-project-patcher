## ✅ strimzi-maven-builder `1.3.1` — success

Upstream: https://github.com/strimzi/strimzi-kafka-operator @ `555c3e0f07c2` (line `1`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 0 |
| image `strimzi-maven-builder` | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 0 |

### Release gate (reported only (`gate.enforce: false`))

- image `strimzi-maven-builder`: ✅ passes

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| dockerfile | `docker-images/maven-builder/Dockerfile` | `registry.access.redhat.com/ubi9/openjdk-21` | `openjdk-21:1.24` | `openjdk-21:1.24@sha256:c8fcb7571677a9f6f1f2f3325c9765103ecc2834ff13ce20eb5ee6d1088f7e12` | base image refresh |

### Upstream tests

Not run.

### Images

| Image | Ref | Smoke | Copa |
|---|---|---|---|
| strimzi-maven-builder | `patcher.local/strimzi-maven-builder:1.3.1-patched.dev` | ✅ `mvn -v` | no fixable OS packages |

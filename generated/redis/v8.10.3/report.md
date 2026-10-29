## ✅ redis `v8.10.3` — success

Upstream: https://github.com/redis/docker-library-redis @ `8fd1238a62e5` (line `v8.10`)

### Fixable vulnerabilities (critical / high / medium / low)

| Artifact | Before | After | Fixed | New |
|---|---|---|---|---|
| source (`trivy fs`) | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 0 |
| image `redis` | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 0 |
| image `redis-alpine` | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 0 |

### Changes applied

| Ecosystem | File | Package | From | To | Why |
|---|---|---|---|---|---|
| dockerfile | `debian/Dockerfile` | `debian` | `debian:trixie-slim` | `debian:trixie-slim@sha256:f6b08b09a05725f9431502d3b5714f5c4576e82c1a84fa1debe0c24a7e0c3ec4` | base image refresh |
| dockerfile | `alpine/Dockerfile` | `alpine` | `alpine:3.23` | `alpine:3.23@sha256:ff7f0c727dd796aa36787bfcd9a64bf35a6ce72a73451b3359fde849b6703d63` | base image refresh |

### Newer releases beyond the policy (not applied)

- `alpine` → `3.24` in `alpine/Dockerfile`: newer tag 3.24 exists beyond the `patch` level for base images (set `level: minor` on this dockerfile ecosystem, or bump it in patches/)

### Upstream tests

✅ passed in 15.0 min — `cd .redis-src && ./runtest --clients 8 --tags -slow --dump-logs `

### Images

| Image | Ref | Smoke | Copa |
|---|---|---|---|
| redis | `patcher.local/redis:8.10.3-patched.dev` | ✅ `redis-server --version` | no fixable OS packages |
| redis-alpine | `patcher.local/redis:8.10.3-alpine-patched.dev` | ✅ `redis-server --version` | no fixable OS packages |

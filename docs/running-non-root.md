# Running the images as non-root

Non-root is enforced where the pods run: Kubernetes' built-in
[Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/) with the `restricted`
profile, plus each chart's `securityContext`. The images only matter where an image itself stands in the way, and the
pipeline handles those two cases:
- **argoexec** runs as root upstream. The `argo-workflows` recipe also releases upstream's non-root variant,
  `argoexec:<tag>-nonroot-patched`, which runs as `8737`.
- **dex, router and splunk-otel-collector** name their user (`dex:dex`). The kubelet can't check that a name isn't root,
  so `runAsNonRoot` would refuse them. Our images set the same user as a number (`user` on the recipe's image).

Every report's **Images** table shows what each image runs as, and the release gate warns on root or a name
([gate.md](gate.md)). The measurements and the decision are in
[improvements/image-hardening.md](../improvements/image-hardening.md).

## 1. Turn on `restricted`, warnings first

`restricted` requires, for every container: a non-root user, `allowPrivilegeEscalation: false`, all capabilities
dropped, and a `RuntimeDefault` (or `Localhost`) seccomp profile. It also forbids `hostPath` volumes, host networking
and privileged containers.

1. **See what would break** before changing anything. A server-side dry run lists the pods `enforce` would refuse:
   ```bash
   kubectl label --dry-run=server --overwrite ns --all pod-security.kubernetes.io/enforce=restricted
   ```
2. **Warn and audit** for a while. New pods are still admitted, while `kubectl` warnings and audit-log entries name what
   doesn't comply:
   ```bash
   kubectl label --overwrite ns argocd \
     pod-security.kubernetes.io/warn=restricted pod-security.kubernetes.io/audit=restricted
   ```
3. **Fix the values** (section 2) until the warnings stop.
4. **Enforce:**
   ```bash
   kubectl label --overwrite ns argocd pod-security.kubernetes.io/enforce=restricted
   ```

Agents that read the node can't be `restricted`: the Splunk agent when it collects logs, a collector DaemonSet with a
host-log receiver, trivy-operator's node collector. Each mounts host paths, which `restricted` and `baseline` both
forbid. Give such an agent a namespace of its own labelled `privileged`, and enforce `restricted` everywhere else.

## 2. Chart values per project

Upstream charts, with our images. Use the moving tag `<tag>-patched` (the newest revision), or pin a digest from the
release record. `<owner>` is the registry owner (`PATCHER_REGISTRY`). Values only some projects need are marked.

The container `securityContext` most charts below need, written once:

```yaml
securityContext:
  runAsNonRoot: true
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities: { drop: [ALL] }
  seccompProfile: { type: RuntimeDefault }
```

| Project (chart) | Already `restricted`? | Set |
|---|---|---|
| Argo CD (argo-helm `argo-cd`) | Yes | Only the image: `global.image.repository: ghcr.io/<owner>/argocd`, `global.image.tag: v3.5.7-patched` |
| Argo Rollouts (argo-helm `argo-rollouts`) | Yes | Only the image |
| Argo Workflows (argo-helm `argo-workflows`) | The controller and server miss only seccomp | See below |
| External Secrets (`external-secrets`) | Yes | Only the image |
| Dex (`dexidp/dex`) | No: nothing set | `securityContext` above. With our image no `runAsUser` is needed; with upstream's, add `runAsUser: 1001` |
| Apollo Router (`router`) | No: nothing set | `securityContext` above. With upstream's image, add `runAsUser: 1000` |
| OpenTelemetry Collector (`opentelemetry-collector`) | No: nothing set | `securityContext` above (the image runs as `10001`). A DaemonSet with host-log receivers goes in a `privileged` namespace |
| Splunk OTel Collector (`splunk-otel-collector`) | No: `fsGroup: 999` only | Gateway and cluster receiver: `securityContext` above under `gateway` and `clusterReceiver`. The agent with log collection: a `privileged` namespace (it mounts host log directories) |
| Strimzi (`strimzi-kafka-operator`) | The operator, yes | Kafka, Connect and the other pods the operator creates: `extraEnvs: [{name: STRIMZI_POD_SECURITY_PROVIDER_CLASS, value: restricted}]` |
| Trivy Operator (`trivy-operator`) | No: no `runAsNonRoot` or seccomp | See below |
| Trivy (`trivy`) | Yes (`runAsUser: 65534`) | Only the image. Outside the chart, run `trivy image` as non-root with `--cache-dir /tmp/trivy` |

copa and the maven images are CI tools, not deployed as pods. To run them non-root, use `docker run -u` (for maven, with
`MAVEN_CONFIG`, as the official image documents).

**Argo Workflows.** The executor runs inside every workflow pod, so this is where most of the work is:

```yaml
images:
  tag: v4.1.6-patched                 # controller and server (argocli)
controller:
  image: { registry: ghcr.io, repository: <owner>/workflow-controller }
  securityContext: { seccompProfile: { type: RuntimeDefault } }   # merged into the chart's default
  workflowDefaults:
    spec:
      securityContext: { runAsNonRoot: true, runAsUser: 8737, seccompProfile: { type: RuntimeDefault } }
server:
  image: { registry: ghcr.io, repository: <owner>/argocli }
  securityContext: { seccompProfile: { type: RuntimeDefault } }
executor:
  image:
    registry: ghcr.io
    repository: <owner>/argoexec
    tag: v4.1.6-nonroot-patched       # our non-root variant
    nonroot: false                    # the chart's switch appends -nonroot to the tag; ours carries it before -patched
  securityContext:
    runAsNonRoot: true
    allowPrivilegeEscalation: false
    capabilities: { drop: [ALL] }
```

Helm merges these maps with the chart's defaults, so the controller and server keep the chart's
`readOnlyRootFilesystem`, `runAsNonRoot` and dropped capabilities, and only gain the seccomp profile. A workflow whose
own image needs root (Argo's docs give `mkdir /my-dir` as an example) has to set `runAsUser: 0` in its spec, and its namespace
can't then be `restricted`.

**Trivy Operator.** Its scan jobs run the trivy image, which runs as root by default:

```yaml
podSecurityContext: { runAsNonRoot: true, seccompProfile: { type: RuntimeDefault } }
trivyOperator:
  scanJobPodTemplatePodSecurityContext:
    runAsNonRoot: true
    runAsUser: 10000
    runAsGroup: 10000
    seccompProfile: { type: RuntimeDefault }
```

Image scans work this way (their cache is `/tmp/trivy/.cache`). Filesystem and rootfs scans need root, upstream says.

## 3. Optional: admit only images the pipeline signed

Non-root says how an image runs; a signature check says where it came from. Releases are signed keylessly by
`release.yml` on `main` ([runbook: verifying an image](runbook.md#verifying-an-image)). One component enforces that at admission:
- [Kyverno](https://kyverno.io/docs/writing-policies/verify-images/) `verifyImages`, if the cluster already runs
  Kyverno;
- otherwise Sigstore's [policy-controller](https://docs.sigstore.dev/policy-controller/overview/), smaller and
  single-purpose. Namespaces opt in with the label `policy.sigstore.dev/include: "true"`:

```yaml
apiVersion: policy.sigstore.dev/v1beta1
kind: ClusterImagePolicy
metadata:
  name: patched-images
spec:
  images:
    - glob: "ghcr.io/<owner>/**"
  authorities:
    - keyless:
        url: https://fulcio.sigstore.dev
        identities:
          - issuer: https://token.actions.githubusercontent.com
            subject: https://github.com/<owner>/<repo>/.github/workflows/release.yml@refs/heads/main
```

The identity is the same one the runbook's `cosign verify` checks. Pinning it to `refs/heads/main` means an image
signed from any other branch is refused.

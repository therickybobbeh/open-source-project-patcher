# Example recipes (Python, Gradle, vendor image)

These recipes were written and run end to end while adding Python, Gradle and Copa library support.
None of these projects is an image we run, so they live here instead of in `recipes/`, and the nightly
pipeline never picks them up. Start from them when you onboard a similar project.

| Recipe | Shows |
|---|---|
| [`z2jh-hub.yaml`](recipes/z2jh-hub.yaml) | A Python image (JupyterHub's `quay.io/jupyterhub/k8s-hub`) built from a pip-compiled `requirements.txt` in a subdirectory: the `python` ecosystem in pinned mode, a Dockerfile in a subdirectory with its own build context, and a smoke test in place of a unit-test suite that needs a cluster |
| [`jupyterhub.yaml`](recipes/jupyterhub.yaml) | pytest for a Python + npm project without lockfiles: a uv-built `.venv` with pip seeded, the venv's `bin` on `PATH`, and a test helper (`configurable-http-proxy`) installed into its own prefix. Started from `patcher init jupyterhub/jupyterhub` |
| [`spring-petclinic.yaml`](recipes/spring-petclinic.yaml) | Gradle without lockfiles or a version catalog: a branch-tracked line (`versionFrom: build.gradle`), `scan.image` planning from the built jar, `scan.skipFiles: [pom.xml]` for the alternative Maven build, and our own Dockerfile from `patches/` |
| [`k8s-hub-vendor.yaml`](recipes/k8s-hub-vendor.yaml) | A vendor image treated as closed source: `mode: image-only` with Copa library patching (`copa: {libraries: true, level: minor}`) |

What the runs taught us is in [troubleshooting.md](../troubleshooting.md). Highlights:
- An unpinned test dependency released after upstream's release broke a whole suite; the install
  cutoff now prevents that.
- `uv venv` has no pip unless seeded.
- A test helper installed into the project's `node_modules` got pruned by the project's own build.
- Image-driven planning has to run even when the source scan finds nothing.

**JupyterHub status:** with those fixes, 524 tests pass. The suite then hangs in `test_token_page`, inside
JupyterHub's mock-service fixtures, in this environment. The test timeout stops it, and the report names the
last test that started. Deselect it in `skips/jupyterhub.yaml` if you adopt this recipe.

## Using one

1. Copy the recipe into `recipes/` and fix the `$schema` path (`../schema/recipe.schema.json`).
2. Add `skips/<name>.yaml` (`skips: []` / `quarantine: []`) and any `patches/<name>/files/`.
3. Add the image to `inventory.yaml`.
4. Run `patcher validate`, then `patcher run <name>` as in the [runbook](../runbook.md#adding-a-release-line-or-a-project).

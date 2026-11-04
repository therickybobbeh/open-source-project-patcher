# Moving the repository to a GitHub Enterprise Cloud organization

A checklist for moving this repository from a personal account to an organization on GitHub Enterprise Cloud
(GHEC). Most of the pipeline moves with the repository. Four things don't, and consumers see two of them:

| | Moves with the repository | Changes |
|---|---|---|
| Code, PRs, issues, Actions history | Yes; old git and web URLs redirect | – |
| Actions secrets and variables | Yes | Check them after the move |
| The GitHub App that opens PRs | No: it's installed on the personal account | An app owned by the organization |
| Images | No: `ghcr.io/<you>/…` stays where it is | New releases go to `ghcr.io/<org>/…` |
| Signing identity | No: it names the repository | `https://github.com/<org>/<repo>/.github/workflows/release.yml@refs/heads/main` |
| The onboarding site | No redirect | `https://<org>.github.io/<repo>/`, or a private Pages URL |

## Before the move

1. **Pick the organization, the name and the visibility.** `internal` or `private` both work: on GHEC, artifact
   attestations and Pages work for a non-public repository too, and Pages can be limited to the organization.
2. **Tell the consumers** that image names and the signing identity change, and when. They keep pulling the old
   images until they switch: nothing is deleted.
3. **Check the organization's Actions policy** allows the actions the workflows use, all pinned by commit SHA:
   - `actions/*`: `checkout`, `cache`, `upload-artifact`, `download-artifact`, `create-github-app-token`,
     `attest-build-provenance`, `configure-pages`, `upload-pages-artifact`, `deploy-pages`;
   - `astral-sh/setup-uv`, `docker/login-action`, `docker/setup-buildx-action`, `docker/setup-qemu-action`,
     `peter-evans/create-pull-request`, `sigstore/cosign-installer`.

## The move

*Settings → General → Danger Zone → Transfer ownership*. You need permission to create repositories in the
organization.

## Right after the move

1. **The GitHub App.** Create an app owned by the organization, with the permissions from the
   [one-time setup](runbook.md#one-time-setup) (*Contents* and *Pull requests*: read and write). Install it on this
   repository only. Set the repository variable `PATCHER_APP_ID` and the secret `PATCHER_APP_PRIVATE_KEY` to the new
   app's. Until then, PRs open with the `GITHUB_TOKEN` fallback, if it's allowed, and their checks don't run.
2. **Variables.** The ones you set before moved with the repository; set any the organization manages centrally:
   `PATCHER_RUNS_ON`, `PATCHER_RUNS_ON_ARM64`, `PATCHER_RUNS_ON_UPSTREAM`, `PATCHER_RUNS_ON_UPSTREAM_ARM64`, and
   `PATCHER_PLATFORMS`.
3. **Runners.** Self-hosted runners come from the organization's runner groups. Keep the upstream pool apart from
   the trusted one ([self-hosted runners](runbook.md#self-hosted-runners)); the workflows refuse to start otherwise.
4. **Protect `main` with a ruleset** (*Settings → Rules → Rulesets*), targeting the default branch only:
   - require a pull request before merging;
   - require the status check `test` (from `patcher-image.yml`);
   - block force pushes and deletion.

   Leave `wiki-history` out of any ruleset that covers all branches: `wiki-history.yml` publishes it as a single
   commit, which needs a force push. No workflow pushes to `main`, so nothing needs to bypass the ruleset.
5. **Merge queue (optional, organization repositories only).** Turn it on in the same ruleset with the *merge* method,
   so history keeps merge commits. `scripts/merge-ready.sh --merge` then queues PRs instead of merging them. Run one
   daily round with it to check. GitHub is still rolling out queue support for stacked PRs.
6. **Pages.** *Settings → Pages → Source: GitHub Actions*. On GHEC, set *Visibility* to private to limit the site
   to the organization's members. The `github-pages` environment should still admit only `main`.
7. **Code security.** *Dependency graph*, *Dependabot alerts* and *Dependabot security updates*, unless the
   organization's security configuration already enforces them.
8. **Packages.** New images start private in `ghcr.io/<org>/`. Make them public if the organization allows it, or
   give the clusters' pull secrets read access.
9. **Links.** Replace the old owner in `README.md` and `site/index.html` (the site's links and verify commands).

## Release into the new namespace

The organization has no images yet. Release every line once:
- dispatch `patch.yml` with `all`;
- merge its PRs in a daily round (`scripts/merge-ready.sh`).

Upgrades and new lines wait for a person, as usual ([the daily merge round](runbook.md#the-daily-merge-round)).
Each release is signed with the new identity.

## Consumers

- **Image names:** `ghcr.io/<org>/<image>:<tag>-patched`, or a digest from the release record.
- **Verification:** set `ID` in the [verify commands](runbook.md#verifying-an-image) to
  `https://github.com/<org>/<repo>/.github/workflows/release.yml@refs/heads/main`, and use `--repo <org>/<repo>` for
  `gh attestation verify`.
- **Admission policies:** the same identity ([running-non-root.md](running-non-root.md#3-optional-admit-only-images-the-pipeline-signed)).

## Check it works

1. Dispatch `patch.yml` with `recipe=dex`. Its PR opens and the `test` check runs on it, which means the app works.
2. Merge the PR. The release signs `ghcr.io/<org>/dex`. `cosign verify` with the new `ID` passes.
3. `scripts/merge-ready.sh` lists the open PRs with the merge policy's verdicts.
4. The next nightly and rescan runs finish. A failing job opens a `ci-failure` issue, which closes itself when it
   passes.

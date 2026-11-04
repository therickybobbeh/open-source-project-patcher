# Improvements

Investigations and proposals that aren't built yet. Each one says what it found, the options with their trade-offs,
and a recommended plan, so a decision can be made from the page. Once one is built, its page links to the PRs, and the
docs that describe the result move into `docs/`.

| Proposal | Status | In short |
|---|---|---|
| [Image hardening](image-hardening.md) | Decided 2026-11-04, not built | 17 of 22 images already run as non-root. Enforce non-root in the clusters (Pod Security `restricted`, chart values); change images only where they stand in the way: release upstream's non-root `argoexec`, and write dex's, router's and splunk-otel-collector's users as numbers. The gate reports how each image runs |

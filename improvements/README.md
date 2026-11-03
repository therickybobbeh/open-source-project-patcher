# Improvements

Investigations and proposals that aren't built yet. Each one says what it found, the options with their trade-offs,
and a recommended plan, so a decision can be made from the page. Once one is built, its page links to the PRs, and the
docs that describe the result move into `docs/`.

| Proposal | Status | In short |
|---|---|---|
| [Image hardening](image-hardening.md) | Investigated 2026-11-03 | We patch but don't harden. 5 of 20 images run as root and 10 ship a shell and package manager. The plan: measure with Trivy and Dockle, then opt-in hardening in the overlay build, then minimal bases per recipe |

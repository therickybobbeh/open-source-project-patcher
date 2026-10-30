# Recipes

The full field reference is [`docs/recipes.md`](../docs/recipes.md).

Each `recipes/<name>.yaml` declares an upstream source, release lines,
toolchain, ecosystems, dependency policy, tests and image builds. The most
important review surfaces are:

- **Release lines:** the tags or branches that are actually deployed.
- **Ecosystems:** native adapters for Go, Rust, Java, JavaScript, Python,
  Dockerfile bases and other supported inputs.
- **Policy:** the maximum routine version movement and release-age cooldown.
- **Overrides and holds:** deliberate exceptions that must explain why.
- **Base image floors (`minVersions`):** keep Dockerfile stages off end-of-life
  runtimes (an upstream UI built on Node 20, say).
- **Tests and smoke checks:** evidence that the patched source and image work.

Start new recipes from the validated examples in
[`docs/examples/`](../docs/examples/README.md), then run `patcher validate`
before opening a patch run.

"""What is released now, for the onboarding site (site/): every line in state/ with its images, immutable and moving
tags. pages.yml writes it next to the page on each deploy, so the page never shows a stale copy.

    uv run --project patcher --frozen python scripts/site_data.py site/releases.json
"""

import datetime as dt
import json
import os
import sys
from pathlib import Path

from patcher.config import Repo
from patcher.pipeline import upstream_tag_of


def releases(repo: Repo) -> list[dict]:
    rows = []
    for path in repo.recipe_paths():
        recipe = repo.load_recipe(path.stem)
        for key, ls in sorted(repo.state(recipe.name).lines.items()):
            images = []
            for img in ls.images:
                repository, tag = img.ref.rsplit(":", 1)
                images.append({"name": img.name, "ref": img.ref, "digest": img.digest,
                               "moving": f"{repository}:{upstream_tag_of(repo, tag)}-patched"})
            rows.append({"recipe": recipe.name, "description": recipe.description or "", "line": key,
                         "upstreamTag": ls.upstreamTag, "revision": ls.revision,
                         "releasedAt": ls.releasedAt.isoformat() if ls.releasedAt else None,
                         "platforms": ls.platforms, "images": images})
    return rows


def main(out: str) -> None:
    repo = Repo(Path(__file__).resolve().parents[1])
    doc = {"repository": os.environ.get("GITHUB_REPOSITORY", ""), "commit": os.environ.get("GITHUB_SHA", ""),
           "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "lines": releases(repo)}
    Path(out).write_text(json.dumps(doc, indent=1) + "\n")


if __name__ == "__main__":
    main(sys.argv[1])

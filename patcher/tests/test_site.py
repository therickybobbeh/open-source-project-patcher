"""The onboarding site (site/): its data comes from state/ at deploy time, and the page loads nothing from elsewhere."""

import importlib.util
import re
from pathlib import Path

from patcher.config import Repo

ROOT = Path(__file__).resolve().parents[2]


def site_data():
    spec = importlib.util.spec_from_file_location("site_data", ROOT / "scripts" / "site_data.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_every_released_line_is_listed_with_its_moving_tags():
    repo = Repo(ROOT)
    rows = site_data().releases(repo)
    released = {(p.stem, key) for p in repo.recipe_paths() for key in repo.state(p.stem).lines}
    assert {(r["recipe"], r["line"]) for r in rows} == released
    for r in rows:
        # a Copa refresh leaves an image it had nothing to patch for at its older revision, so an
        # image's tag is at or below the line's revision; something was published at the revision itself
        revs = []
        for img in r["images"]:
            repository, tag = img["ref"].rsplit(":", 1)
            m = re.search(r"-patched\.(\d+)$", tag)
            assert m and int(m.group(1)) <= r["revision"], img
            revs.append(int(m.group(1)))
            assert img["moving"] == f"{repository}:{re.sub(r'\.\d+$', '', tag)}", img
        assert max(revs) == r["revision"], r


def test_the_page_loads_nothing_from_another_site():
    """Like the pipeline itself: nothing fetched at run time that this repository doesn't pin."""
    html = (ROOT / "site" / "index.html").read_text()
    assert not re.search(r"<script[^>]+src=", html), "no external scripts: inline them"
    assert not re.search(r"<link[^>]+rel=\"?stylesheet", html), "no external stylesheets or fonts"
    assert not re.search(r"@import|url\(\s*['\"]?https?:", html), "no CSS loads from other sites"
    assert 'fetch("releases.json"' in html  # the one load: written next to the page by pages.yml

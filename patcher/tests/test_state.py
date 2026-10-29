"""Release state: one file per line, so the state PRs of lines released together never edit the same file."""

import datetime as dt

import yaml

from patcher.config import Repo
from patcher.models import LineState, State

RELEASED = LineState(upstreamTag="v3.5.6", commit="abc", revision=2, releasedAt=dt.datetime(2026, 10, 29, tzinfo=dt.timezone.utc))


def test_each_line_is_saved_to_its_own_file(tmp_path):
    repo = Repo(tmp_path)
    repo.save_state("argo-cd", State(lines={"v3.5": RELEASED}))
    # argo-cd v3.4 and v3.5 were released together: v3.4's state PR adds a file of its own instead of editing v3.5's
    state = repo.state("argo-cd")
    state.lines["v3.4"] = RELEASED.model_copy(update={"upstreamTag": "v3.4.12"})
    repo.save_state("argo-cd", state)
    assert sorted(p.name for p in (tmp_path / "state" / "argo-cd").iterdir()) == ["v3.4.yaml", "v3.5.yaml"]
    assert not (tmp_path / "state" / "argo-cd.yaml").exists()
    assert {k: v.upstreamTag for k, v in repo.state("argo-cd").lines.items()} == {"v3.4": "v3.4.12", "v3.5": "v3.5.6"}


def test_a_whole_recipe_state_file_still_counts(tmp_path):
    (tmp_path / "state").mkdir()
    legacy = RELEASED.model_copy(update={"revision": 1})
    (tmp_path / "state" / "dex.yaml").write_text(yaml.safe_dump(State(lines={"v2": legacy, "v1": legacy}).model_dump(mode="json")))
    repo = Repo(tmp_path)
    assert repo.state("dex").lines["v2"].revision == 1
    repo.save_state("dex", State(lines={"v2": RELEASED}))  # a newer release of v2, in its own file: that one wins
    assert {k: v.revision for k, v in repo.state("dex").lines.items()} == {"v1": 1, "v2": 2}

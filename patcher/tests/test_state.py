"""Release state: one file per line, so the state PRs of lines released together never edit the same file."""

import datetime as dt


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

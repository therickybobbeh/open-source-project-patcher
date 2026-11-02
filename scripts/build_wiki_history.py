#!/usr/bin/env python3
"""Build the repository's patch history (History.md, history.parquet) from git commits and patch artifacts.
wiki-history.yml publishes the output as the single commit of the `wiki-history` branch; main never holds it."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def commits() -> list[dict[str, object]]:
    raw = git(
        "log",
        "--date=iso-strict",
        "--pretty=format:%H%x1f%aI%x1f%an%x1f%s",
        "--name-only",
    )
    rows: list[dict[str, object]] = []
    for block in raw.split("\n\n"):
        lines = block.splitlines()
        if not lines or "\x1f" not in lines[0]:
            continue
        sha, committed_at, author, subject = lines[0].split("\x1f", 3)
        paths = sorted(path for path in lines[1:] if path)
        if paths and all(path.startswith("wiki/") for path in paths):
            continue  # this workflow's own commits: counting them, every run would find "new" history and commit again
        patch_paths = sorted(path for path in paths if path.startswith(("generated/", "state/")))
        rows.append(
            {
                "commit_sha": sha,
                "committed_at": committed_at,
                "author": author,
                "subject": subject,
                "changed_files": len(paths),
                "changed_paths": "\n".join(paths),
                "patch_artifacts": "\n".join(patch_paths),
            }
        )
    return rows


def write_markdown(rows: list[dict[str, object]], out: Path, repo_url: str) -> None:
    patch_rows = [row for row in rows if row["patch_artifacts"]]
    lines = [
        "# Patch history",
        "",
        "This page is generated from git history by "
        f"[`build_wiki_history.py`]({repo_url}/blob/HEAD/scripts/build_wiki_history.py). "
        "The complete machine-readable snapshot is [`history.parquet`](history.parquet).",
        "",
        f"Snapshot through: {rows[0]['committed_at'] if rows else 'no commits'}",
        "",
        "| Date | Commit | Change | Patch artifacts |",
        "| --- | --- | --- | --- |",
    ]
    for row in patch_rows[:100]:
        subject = str(row["subject"]).replace("|", "\\|")
        artifacts = str(row["patch_artifacts"]).replace("\n", "<br>")
        lines.append(
            f"| {str(row['committed_at'])[:10]} | "
            f"[`{str(row['commit_sha'])[:10]}`]({repo_url}/commit/{row['commit_sha']}) | "
            f"{subject} | {artifacts or '—'} |"
        )
    if not patch_rows:
        lines.extend(["| — | — | No patch artifacts recorded yet | — |"])
    (out / "History.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_parquet(rows: list[dict[str, object]], out: Path) -> None:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit(
            "pyarrow is required to write history.parquet; "
            "run with `uv run --with pyarrow ...`"
        ) from exc

    schema = pa.schema(
        [
            ("commit_sha", pa.string()),
            ("committed_at", pa.string()),
            ("author", pa.string()),
            ("subject", pa.string()),
            ("changed_files", pa.int64()),
            ("changed_paths", pa.string()),
            ("patch_artifacts", pa.string()),
        ]
    )
    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(table, out / "history.parquet", compression="zstd")


def default_repo_url() -> str:
    """https://github.com/<owner>/<repo> from the origin remote (absolute links: the page isn't read on main)."""
    url = git("remote", "get-url", "origin").removesuffix(".git")
    return "https://github.com/" + url.split("github.com:", 1)[1] if url.startswith("git@github.com:") else url


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "out" / "wiki-history", help="where to write (default: out/)")
    parser.add_argument("--repo-url", help="for commit links (default: from the origin remote)")
    parser.add_argument("--parquet-only", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rows = commits()
    write_parquet(rows, args.out)
    if not args.parquet_only:
        write_markdown(rows, args.out, args.repo_url or default_repo_url())


if __name__ == "__main__":
    main()

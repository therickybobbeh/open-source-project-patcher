#!/usr/bin/env python3
"""Build the repository wiki history from git commits and patch artifacts."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "wiki"


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


def write_markdown(rows: list[dict[str, object]]) -> None:
    patch_rows = [row for row in rows if row["patch_artifacts"]]
    lines = [
        "# Patch history",
        "",
        "This page is generated from git history by "
        "[`build_wiki_history.py`](../scripts/build_wiki_history.py). "
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
            f"[`{str(row['commit_sha'])[:10]}`](../commit/{row['commit_sha']}) | "
            f"{subject} | {artifacts or '—'} |"
        )
    if not patch_rows:
        lines.extend(["| — | — | No patch artifacts recorded yet | — |"])
    (OUTPUT / "History.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_parquet(rows: list[dict[str, object]]) -> None:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit(
            "pyarrow is required to write wiki/history.parquet; "
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
    pq.write_table(table, OUTPUT / "history.parquet", compression="zstd")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parquet-only", action="store_true")
    args = parser.parse_args()
    OUTPUT.mkdir(exist_ok=True)
    rows = commits()
    write_parquet(rows)
    if not args.parquet_only:
        write_markdown(rows)


if __name__ == "__main__":
    main()

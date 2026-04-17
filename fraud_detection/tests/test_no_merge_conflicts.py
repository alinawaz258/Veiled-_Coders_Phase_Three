from __future__ import annotations

import subprocess
from pathlib import Path


CONFLICT_MARKERS = (
    "<" * 7,
    "=" * 7,
    ">" * 7,
)


def test_repository_has_no_merge_conflict_markers() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    conflicted_files: list[str] = []
    for rel_path in result.stdout.splitlines():
        file_path = repo_root / rel_path
        if not file_path.is_file():
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        if any(marker in content for marker in CONFLICT_MARKERS):
            conflicted_files.append(rel_path)

    assert not conflicted_files, f"Merge conflict markers found in: {conflicted_files}"

from __future__ import annotations

import subprocess
from pathlib import Path


def commit_and_push(project_root: Path, message: str) -> bool:
    """Stages everything, commits with `message`, and pushes.

    Returns True if a commit was made, False if there was nothing to
    commit (not an error — the pipeline may call this at a point where the
    working tree is already clean). Raises RuntimeError on any git failure
    (including a failed push), so the caller sees it and does not proceed
    on top of an unsaved state (see PRINCIPLES.md P3).
    """
    _run_git(project_root, ["add", "-A"])

    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=project_root,
    )
    if diff.returncode == 0:
        return False

    _run_git(project_root, ["commit", "-m", message])
    _run_git(project_root, ["push"])
    return True


def _run_git(project_root: Path, args: list[str]) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git", *args],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {detail}")
    return result

"""Deterministic support functions for external proposal execution."""
from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

from bootstrap import fail, file_sha256, read_json, safe_repo_path, write_json_atomic


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and proc.returncode:
        fail(
            "GIT_ERROR",
            f"git {' '.join(args)} failed",
            returncode=proc.returncode,
            stderr=proc.stderr.strip(),
        )
    return proc


def config(repo: Path) -> dict[str, Any]:
    value = read_json(repo / ".agent/config.json")
    if value.get("phase") != "proposal-verification":
        fail("PROPOSAL_PHASE_DISABLED", "repository config does not enable proposal verification")
    return value


def clean(repo: Path) -> None:
    status = git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout.strip()
    if status:
        fail("DIRTY_WORKTREE", "proposal execution requires a clean candidate worktree", status=status)


def changed(repo: Path) -> list[str]:
    tracked = git(repo, "diff", "--name-only", "HEAD").stdout.splitlines()
    untracked = git(repo, "ls-files", "--others", "--exclude-standard").stdout.splitlines()
    return sorted({p for p in [*tracked, *untracked] if p})


def file_fingerprint(path: Path) -> str:
    if path.is_symlink():
        return "symlink:" + str(path.readlink())
    if not path.exists():
        return "missing"
    if not path.is_file():
        return "non-file"
    return "sha256:" + file_sha256(path)


def worktree_snapshot(repo: Path) -> dict[str, str]:
    return {rel: file_fingerprint(repo / rel) for rel in changed(repo)}


def restore_clean(repo: Path) -> None:
    git(repo, "restore", "--worktree", "--", ".")
    untracked = git(repo, "ls-files", "--others", "--exclude-standard").stdout.splitlines()
    for rel in untracked:
        path = repo / safe_repo_path(rel)
        if path.is_symlink() or path.is_file():
            path.unlink(missing_ok=True)
    for rel in sorted(untracked, key=lambda value: value.count("/"), reverse=True):
        parent = (repo / rel).parent
        while parent != repo:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent


def validate_output_path(path: str | Path | None, repo: Path) -> Path | None:
    if path is None:
        return None
    target = Path(path)
    if target.is_absolute():
        return target
    rel = safe_repo_path(target.as_posix())
    if not rel.startswith(".agent/runtime/"):
        fail(
            "INVALID_OUTPUT_PATH",
            "proposal result/evidence files inside the repository must live under .agent/runtime",
            path=rel,
        )
    return repo / rel


def write_json(path: str | Path | None, value: dict[str, Any], repo: Path) -> None:
    target = validate_output_path(path, repo)
    if target is not None:
        write_json_atomic(target, value)

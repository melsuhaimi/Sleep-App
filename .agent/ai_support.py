"""Deterministic support functions for bounded AI execution."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any

from bootstrap import fail, file_sha256, read_json, repo_root, safe_repo_path, verify_manifest, write_json_atomic


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
    if value.get("phase") != "bounded-ai":
        fail("AI_PHASE_DISABLED", "repository config does not enable bounded AI execution")
    return value


def clean(repo: Path) -> None:
    status = git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout.strip()
    if status:
        fail("DIRTY_WORKTREE", "AI execution requires a clean candidate worktree", status=status)


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
        fail("INVALID_OUTPUT_PATH", "AI result/evidence files inside the repository must live under .agent/runtime", path=rel)
    return repo / rel


def write_json(path: str | Path | None, value: dict[str, Any], repo: Path) -> None:
    target = validate_output_path(path, repo)
    if target is not None:
        write_json_atomic(target, value)


def _context(repo: Path, rel: str, limit: int) -> dict[str, Any]:
    path = repo / safe_repo_path(rel)
    if not path.exists():
        return {"path": rel, "exists": False, "content": ""}
    if path.is_symlink() or not path.is_file():
        fail("INVALID_CONTEXT_PATH", "context path must be a regular file", path=rel)
    size = path.stat().st_size
    if size > limit:
        fail(
            "CONTEXT_OVERFLOW",
            "task context file exceeds configured AI context limit",
            path=rel,
            size=size,
            limit=limit,
        )
    return {
        "path": rel,
        "exists": True,
        "sha256": file_sha256(path),
        "content": path.read_text(encoding="utf-8"),
    }


def build_prompt(manifest: dict[str, Any], *, start=None) -> str:
    repo = repo_root(start)
    verify_manifest(manifest, start=repo)
    cfg = config(repo)
    per_file = cfg.get("max_ai_context_file_bytes", 32768)
    total_limit = cfg.get("max_ai_context_bytes", 131072)
    if (
        not isinstance(per_file, int)
        or per_file <= 0
        or not isinstance(total_limit, int)
        or total_limit <= 0
    ):
        fail("INVALID_CONFIG", "AI context limits must be positive integers")

    context = []
    for entry in [*manifest.get("instructions", []), *manifest.get("skills", [])]:
        rel = entry.get("path")
        if not isinstance(rel, str):
            fail("INVALID_MANIFEST", "manifest context entry is missing a path")
        context.append({"kind": "mandatory", **_context(repo, rel, per_file)})
    for rel in manifest["task"].get("context_paths", []):
        context.append({"kind": "task", **_context(repo, rel, per_file)})

    total = sum(len(item["content"].encode("utf-8")) for item in context)
    if total > total_limit:
        fail("CONTEXT_OVERFLOW", "AI context exceeds configured total limit", size=total, limit=total_limit)

    payload = {
        "run_id": manifest["run_id"],
        "manifest_commit": manifest["repo"]["commit"],
        "task": manifest["task"],
        "policy": manifest["policy"],
        "context": context,
    }
    rules = (
        "You are a bounded engineering reasoning component. The deterministic controller owns mutation, retries, and verification. "
        "Return only the strict proposal. CANDIDATE edits are complete UTF-8 replacements, never deletions. "
        "files_to_modify must equal edit paths in order; verification_required must equal the task list exactly. "
        "Use a stop status with zero edits for missing context, architecture conflict, unknown environment, or blocked work.\n\n"
    )
    return rules + json.dumps(payload, indent=2, sort_keys=True)

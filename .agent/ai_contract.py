"""Validation and mutation boundary for bounded AI proposals."""
from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import tempfile
from typing import Any

from bootstrap import assert_paths_allowed, fail, safe_repo_path
from ai_support import changed, file_fingerprint, git


STOP_STATUSES = {
    "NEEDS_MORE_CONTEXT",
    "ARCHITECTURE_CONTRADICTION",
    "UNKNOWN_ENVIRONMENT",
    "BLOCKED",
}
ALL_STATUSES = {"CANDIDATE", *STOP_STATUSES}
REQUIRED_KEYS = {
    "schema_version",
    "run_id",
    "manifest_commit",
    "status",
    "summary",
    "assumptions",
    "unknowns",
    "files_to_modify",
    "verification_required",
    "edits",
}
EDIT_KEYS = {"path", "content"}


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        fail("MODEL_OUTPUT_INVALID", f"{field} must be an array of strings")
    return list(value)


def _assert_no_symlink_boundary(repo: Path, rel: str) -> None:
    current = repo
    for part in PurePosixPath(rel).parts:
        current = current / part
        if current.is_symlink():
            fail("SYMLINK_EDIT_REJECTED", "proposal may not cross a symlink boundary", path=rel)
        if current.exists() and current != repo / rel and not current.is_dir():
            fail("INVALID_EDIT_TARGET", "proposal parent is not a directory", path=rel)
    target = repo / rel
    if target.exists() and not target.is_file():
        fail("INVALID_EDIT_TARGET", "proposal target must be a regular file", path=rel)


def _assert_not_ignored(repo: Path, rel: str) -> None:
    proc = git(repo, "check-ignore", "--no-index", "-q", "--", rel, check=False)
    if proc.returncode == 0:
        fail("IGNORED_EDIT_REJECTED", "proposal may not mutate a Git-ignored path", path=rel)
    if proc.returncode not in {0, 1}:
        fail(
            "GIT_ERROR",
            "git check-ignore failed while validating proposal",
            path=rel,
            returncode=proc.returncode,
            stderr=proc.stderr.strip(),
        )


def validate_proposal(
    proposal: Any,
    manifest: dict[str, Any],
    cfg: dict[str, Any],
    repo: Path,
) -> dict[str, Any]:
    if not isinstance(proposal, dict):
        fail("MODEL_OUTPUT_INVALID", "model output root must be an object")
    if set(proposal) != REQUIRED_KEYS:
        fail(
            "MODEL_OUTPUT_INVALID",
            "model output fields do not match the result contract",
            missing=sorted(REQUIRED_KEYS - set(proposal)),
            extra=sorted(set(proposal) - REQUIRED_KEYS),
        )
    if proposal.get("schema_version") != 1:
        fail("MODEL_OUTPUT_INVALID", "schema_version must equal 1")
    if proposal.get("run_id") != manifest["run_id"]:
        fail("PROPOSAL_RUN_MISMATCH", "proposal run_id does not match the current manifest")
    if proposal.get("manifest_commit") != manifest["repo"]["commit"]:
        fail("PROPOSAL_COMMIT_MISMATCH", "proposal commit does not match the current manifest")

    status = proposal.get("status")
    if status not in ALL_STATUSES:
        fail("MODEL_OUTPUT_INVALID", "proposal status is not recognized", status=status)
    if not isinstance(proposal.get("summary"), str):
        fail("MODEL_OUTPUT_INVALID", "summary must be a string")
    _string_list(proposal.get("assumptions"), "assumptions")
    _string_list(proposal.get("unknowns"), "unknowns")
    files = _string_list(proposal.get("files_to_modify"), "files_to_modify")
    required = _string_list(proposal.get("verification_required"), "verification_required")
    if required != manifest["task"]["required_verification"]:
        fail(
            "VERIFICATION_CONTRACT_MISMATCH",
            "proposal may not remove, add, reorder, or alter required verification gates",
            expected=manifest["task"]["required_verification"],
            actual=required,
        )

    edits = proposal.get("edits")
    if not isinstance(edits, list):
        fail("MODEL_OUTPUT_INVALID", "edits must be an array")
    normalized_edits: list[dict[str, str]] = []
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) != EDIT_KEYS:
            fail("MODEL_OUTPUT_INVALID", "each edit must contain only path and content")
        path = edit.get("path")
        content = edit.get("content")
        if not isinstance(path, str) or not isinstance(content, str):
            fail("MODEL_OUTPUT_INVALID", "edit path and content must be strings")
        normalized_edits.append({"path": safe_repo_path(path), "content": content})

    if status in STOP_STATUSES:
        if files or normalized_edits:
            fail("STOP_STATUS_WITH_EDITS", "stop statuses must not contain repository edits", status=status)
        return proposal

    if not normalized_edits:
        fail("EMPTY_CANDIDATE", "CANDIDATE must contain at least one edit")
    edit_paths = [item["path"] for item in normalized_edits]
    if files != edit_paths:
        fail(
            "EDIT_LIST_MISMATCH",
            "files_to_modify must exactly equal edit paths in order",
            files_to_modify=files,
            edit_paths=edit_paths,
        )
    if len(set(edit_paths)) != len(edit_paths):
        fail("DUPLICATE_EDIT_PATH", "proposal contains the same edit path more than once")

    task = manifest["task"]
    assert_paths_allowed(
        edit_paths,
        allowed_scope=task["allowed_scope"],
        forbidden_scope=task.get("forbidden_scope", []),
    )

    per_file = cfg.get("max_ai_edit_file_bytes", 65536)
    total_limit = cfg.get("max_ai_total_edit_bytes", 196608)
    if not isinstance(per_file, int) or per_file <= 0 or not isinstance(total_limit, int) or total_limit <= 0:
        fail("INVALID_CONFIG", "AI edit limits must be positive integers")

    total = 0
    for item in normalized_edits:
        rel = item["path"]
        _assert_no_symlink_boundary(repo, rel)
        _assert_not_ignored(repo, rel)
        size = len(item["content"].encode("utf-8"))
        if size > per_file:
            fail("EDIT_BUDGET_EXCEEDED", "proposal file exceeds configured edit limit", path=rel, size=size, limit=per_file)
        total += size
    if total > total_limit:
        fail("EDIT_BUDGET_EXCEEDED", "proposal exceeds configured total edit limit", size=total, limit=total_limit)
    return proposal


def apply_proposal(repo: Path, proposal: dict[str, Any]) -> None:
    for edit in proposal["edits"]:
        rel = safe_repo_path(edit["path"])
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=".ai-edit-", dir=target.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                handle.write(edit["content"])
            os.replace(temp_name, target)
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


def assert_expected_mutation(repo: Path, proposal: dict[str, Any]) -> dict[str, str]:
    expected = sorted(proposal["files_to_modify"])
    actual = changed(repo)
    if actual != expected:
        fail("UNEXPECTED_MUTATION", "worktree mutation set differs from the validated proposal", expected=expected, actual=actual)
    return {path: file_fingerprint(repo / path) for path in actual}

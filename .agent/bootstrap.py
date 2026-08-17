#!/usr/bin/env python3
"""Deterministic bootstrap primitives for the Sleep App engineering harness.

This module performs no network calls and no AI/model calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any, Iterable


TASK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(slots=True)
class HarnessError(Exception):
    code: str
    message: str
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def fail(code: str, message: str, **details: Any) -> None:
    raise HarnessError(code, message, details or None)


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        fail(
            "GIT_ERROR",
            f"git {' '.join(args)} failed",
            stderr=proc.stderr.strip(),
            returncode=proc.returncode,
        )
    return proc.stdout.strip()


def repo_root(start: str | Path | None = None) -> Path:
    start_path = Path(start or Path.cwd()).resolve()
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=start_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        fail("NOT_GIT_REPO", "engineering harness must run inside a Git repository")
    return Path(proc.stdout.strip()).resolve()


def head_sha(repo: Path) -> str:
    value = _git(repo, "rev-parse", "HEAD").lower()
    if not COMMIT_RE.fullmatch(value):
        fail("INVALID_HEAD", "HEAD did not resolve to a full 40-character Git SHA", value=value)
    return value


def read_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        fail("MISSING_FILE", f"required file does not exist: {path}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(
            "INVALID_JSON",
            f"invalid JSON: {path}",
            line=exc.lineno,
            column=exc.colno,
            error=exc.msg,
        )
    if not isinstance(value, dict):
        fail("INVALID_JSON", f"JSON root must be an object: {path}")
    return value


def file_sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_repo_path(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail("INVALID_PATH", "repository path must be a non-empty string")
    text = value.replace("\\", "/").strip()
    pure = PurePosixPath(text)
    if pure.is_absolute() or ".." in pure.parts:
        fail("INVALID_PATH", "repository path may not be absolute or escape the repository", path=value)
    normalized = pure.as_posix()
    if normalized in {"", "."}:
        fail("INVALID_PATH", "repository path must identify a repository location", path=value)
    return normalized


def safe_scope_pattern(value: str) -> str:
    normalized = safe_repo_path(value)
    # Scope patterns may contain glob metacharacters but never path traversal.
    return normalized


def _require_nonempty_string(obj: dict[str, Any], key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        fail("INVALID_TASK", f"{key} must be a non-empty string")
    return value.strip()


def _require_string_list(
    obj: dict[str, Any], key: str, *, min_items: int = 0
) -> list[str]:
    value = obj.get(key)
    if not isinstance(value, list) or len(value) < min_items:
        fail("INVALID_TASK", f"{key} must be a list with at least {min_items} item(s)")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            fail("INVALID_TASK", f"{key} must contain only non-empty strings")
        result.append(item.strip())
    return result


def validate_task(task: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {
        "schema_version",
        "task_id",
        "objective",
        "acceptance",
        "allowed_scope",
        "forbidden_scope",
        "required_verification",
        "context_paths",
        "expected_base_commit",
    }
    unknown_keys = sorted(set(task) - allowed_keys)
    if unknown_keys:
        fail("INVALID_TASK", "task contains unsupported fields", fields=unknown_keys)

    if task.get("schema_version") != 1:
        fail("INVALID_TASK", "schema_version must equal 1")

    task_id = _require_nonempty_string(task, "task_id")
    if not TASK_ID_RE.fullmatch(task_id):
        fail("INVALID_TASK", "task_id has an invalid format", task_id=task_id)

    objective = _require_nonempty_string(task, "objective")
    acceptance = _require_string_list(task, "acceptance", min_items=1)
    allowed_scope = [
        safe_scope_pattern(v)
        for v in _require_string_list(task, "allowed_scope", min_items=1)
    ]
    forbidden_scope = [
        safe_scope_pattern(v)
        for v in _require_string_list(
            {**task, "forbidden_scope": task.get("forbidden_scope", [])},
            "forbidden_scope",
        )
    ]
    required_verification = _require_string_list(
        task, "required_verification", min_items=1
    )
    context_paths = [
        safe_repo_path(v)
        for v in _require_string_list(
            {**task, "context_paths": task.get("context_paths", [])},
            "context_paths",
        )
    ]

    expected_base_commit = task.get("expected_base_commit")
    if expected_base_commit is not None:
        if not isinstance(expected_base_commit, str) or not re.fullmatch(
            r"[0-9a-fA-F]{7,40}", expected_base_commit
        ):
            fail("INVALID_TASK", "expected_base_commit must be a 7-40 character hex SHA")
        expected_base_commit = expected_base_commit.lower()

    return {
        "schema_version": 1,
        "task_id": task_id,
        "objective": objective,
        "acceptance": acceptance,
        "allowed_scope": allowed_scope,
        "forbidden_scope": forbidden_scope,
        "required_verification": required_verification,
        "context_paths": context_paths,
        **(
            {"expected_base_commit": expected_base_commit}
            if expected_base_commit is not None
            else {}
        ),
    }


def _path_entry(repo: Path, rel_path: str, max_bytes: int, kind: str) -> dict[str, Any]:
    path = repo / rel_path
    if not path.is_file():
        fail(f"MISSING_{kind.upper()}", f"required {kind} file is missing", path=rel_path)
    size = path.stat().st_size
    if size > max_bytes:
        fail(
            "CONTEXT_OVERFLOW",
            f"{kind} file exceeds its per-file context limit",
            path=rel_path,
            size=size,
            limit=max_bytes,
        )
    return {
        "path": rel_path,
        "sha256": file_sha256(path),
        "bytes": size,
    }


def _ancestor_dirs_for_context_path(rel_path: str) -> list[PurePosixPath]:
    pure = PurePosixPath(rel_path)
    parent = pure.parent
    dirs: list[PurePosixPath] = [PurePosixPath(".")]
    current = PurePosixPath(".")
    for part in parent.parts:
        if part in {"", "."}:
            continue
        current = current / part
        dirs.append(current)
    return dirs


def discover_instructions(
    repo: Path,
    task: dict[str, Any],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    root_name = config.get("required_root_instruction")
    if not isinstance(root_name, str) or not root_name:
        fail("INVALID_CONFIG", "required_root_instruction must be configured")

    max_bytes = config.get("max_instruction_file_bytes")
    if not isinstance(max_bytes, int) or max_bytes <= 0:
        fail("INVALID_CONFIG", "max_instruction_file_bytes must be a positive integer")

    selected: dict[str, None] = {}

    root_path = safe_repo_path(root_name)
    if not (repo / root_path).is_file():
        fail("MISSING_ROOT_INSTRUCTIONS", f"required root instruction file is missing: {root_path}")
    selected[root_path] = None

    for context_path in task.get("context_paths", []):
        for directory in _ancestor_dirs_for_context_path(context_path):
            base = repo if directory.as_posix() == "." else repo / directory.as_posix()
            override = base / "AGENTS.override.md"
            normal = base / "AGENTS.md"

            chosen: Path | None = None
            if override.is_file():
                chosen = override
            elif normal.is_file():
                chosen = normal

            if chosen is not None:
                rel = chosen.relative_to(repo).as_posix()
                # Root AGENTS.md remains mandatory. A root override can add to it but
                # cannot erase the root bootstrap contract in Harness v1.
                selected[rel] = None

    entries = [_path_entry(repo, rel, max_bytes, "instruction") for rel in selected]
    return entries


def discover_skills(
    repo: Path,
    task: dict[str, Any],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    index_path = repo / ".agent/skills/index.json"
    index = read_json(index_path)
    if index.get("schema_version") != 1 or not isinstance(index.get("skills"), list):
        fail("INVALID_SKILL_INDEX", ".agent/skills/index.json has an invalid shape")

    raw_skills = index["skills"]
    by_id: dict[str, dict[str, Any]] = {}
    for item in raw_skills:
        if not isinstance(item, dict):
            fail("INVALID_SKILL_INDEX", "every skill entry must be an object")
        skill_id = item.get("id")
        path = item.get("path")
        triggers = item.get("triggers", [])
        requires = item.get("requires", [])
        if (
            not isinstance(skill_id, str)
            or not skill_id
            or not isinstance(path, str)
            or not path
            or not isinstance(triggers, list)
            or not all(isinstance(v, str) and v for v in triggers)
            or not isinstance(requires, list)
            or not all(isinstance(v, str) and v for v in requires)
        ):
            fail("INVALID_SKILL_INDEX", "skill metadata is malformed", skill=item)
        if skill_id in by_id:
            fail("INVALID_SKILL_INDEX", "duplicate skill id", skill_id=skill_id)
        by_id[skill_id] = {
            "id": skill_id,
            "path": safe_repo_path(path),
            "triggers": triggers,
            "requires": requires,
        }

    searchable = "\n".join(
        [task["objective"], *task["acceptance"], *task.get("required_verification", [])]
    ).casefold()

    selected_ids: list[str] = []
    for skill_id, item in by_id.items():
        if any(trigger.casefold() in searchable for trigger in item["triggers"]):
            selected_ids.append(skill_id)

    visiting: set[str] = set()
    resolved: list[str] = []

    def add_with_dependencies(skill_id: str) -> None:
        if skill_id in resolved:
            return
        if skill_id in visiting:
            fail("SKILL_DEPENDENCY_CYCLE", "skill dependency cycle detected", skill_id=skill_id)
        item = by_id.get(skill_id)
        if item is None:
            fail("MISSING_SKILL_DEPENDENCY", "required skill dependency is not indexed", skill_id=skill_id)
        visiting.add(skill_id)
        for dependency in item["requires"]:
            add_with_dependencies(dependency)
        visiting.remove(skill_id)
        resolved.append(skill_id)

    for skill_id in selected_ids:
        add_with_dependencies(skill_id)

    max_bytes = config.get("max_skill_file_bytes")
    if not isinstance(max_bytes, int) or max_bytes <= 0:
        fail("INVALID_CONFIG", "max_skill_file_bytes must be a positive integer")

    entries: list[dict[str, Any]] = []
    for skill_id in resolved:
        meta = by_id[skill_id]
        entry = _path_entry(repo, meta["path"], max_bytes, "skill")
        entries.append({"id": skill_id, **entry, "requires": list(meta["requires"])})
    return entries


def _commit_matches(expected: str, actual: str) -> bool:
    return actual.startswith(expected.lower())


def build_manifest(
    task_path: str | Path,
    *,
    start: str | Path | None = None,
) -> dict[str, Any]:
    repo = repo_root(start)
    config = read_json(repo / ".agent/config.json")

    if config.get("protocol_version") != 1:
        fail("INVALID_CONFIG", "protocol_version must equal 1")

    task_file = Path(task_path)
    if not task_file.is_absolute():
        task_file = repo / task_file
    task = validate_task(read_json(task_file))

    commit = head_sha(repo)
    expected = task.get("expected_base_commit")
    if expected is not None and not _commit_matches(expected, commit):
        fail(
            "STALE_BASE_COMMIT",
            "task expected a different repository commit",
            expected=expected,
            actual=commit,
        )

    instructions = discover_instructions(repo, task, config)
    skills = discover_skills(repo, task, config)

    mandatory_bytes = sum(v["bytes"] for v in instructions) + sum(
        v["bytes"] for v in skills
    )
    max_mandatory = config.get("max_mandatory_context_bytes")
    if not isinstance(max_mandatory, int) or max_mandatory <= 0:
        fail("INVALID_CONFIG", "max_mandatory_context_bytes must be a positive integer")
    if mandatory_bytes > max_mandatory:
        fail(
            "CONTEXT_OVERFLOW",
            "mandatory instruction and Skill context exceeds configured budget",
            mandatory_bytes=mandatory_bytes,
            limit=max_mandatory,
        )

    max_attempts = config.get("max_attempts_per_task")
    max_same_failure = config.get("max_same_failure_repeats")
    if (
        not isinstance(max_attempts, int)
        or max_attempts <= 0
        or not isinstance(max_same_failure, int)
        or max_same_failure <= 0
        or max_same_failure > max_attempts
    ):
        fail("INVALID_CONFIG", "retry policy is invalid")

    return {
        "protocol_version": 1,
        "run_id": f"{task['task_id']}@{commit[:12]}",
        "status": "READY",
        "phase": config.get("phase", "bootstrap-only"),
        "repo": {"commit": commit},
        "task": task,
        "instructions": instructions,
        "skills": skills,
        "context_budget": {
            "mandatory_bytes": mandatory_bytes,
            "max_mandatory_bytes": max_mandatory,
        },
        "policy": {
            "max_attempts_per_task": max_attempts,
            "max_same_failure_repeats": max_same_failure,
        },
    }


def verify_manifest(
    manifest: dict[str, Any],
    *,
    start: str | Path | None = None,
) -> None:
    repo = repo_root(start)
    if manifest.get("protocol_version") != 1 or manifest.get("status") != "READY":
        fail("INVALID_MANIFEST", "manifest protocol/status is invalid")

    manifest_repo = manifest.get("repo")
    if not isinstance(manifest_repo, dict):
        fail("INVALID_MANIFEST", "manifest repo section is invalid")
    expected_commit = manifest_repo.get("commit")
    actual_commit = head_sha(repo)
    if expected_commit != actual_commit:
        fail(
            "MANIFEST_STALE",
            "repository HEAD changed after manifest creation",
            expected=expected_commit,
            actual=actual_commit,
        )

    for section, code in (("instructions", "INSTRUCTION_CHANGED"), ("skills", "SKILL_CHANGED")):
        entries = manifest.get(section)
        if not isinstance(entries, list):
            fail("INVALID_MANIFEST", f"manifest {section} section must be a list")
        for entry in entries:
            if not isinstance(entry, dict):
                fail("INVALID_MANIFEST", f"manifest {section} entry is invalid")
            rel = entry.get("path")
            expected_hash = entry.get("sha256")
            if not isinstance(rel, str) or not isinstance(expected_hash, str):
                fail("INVALID_MANIFEST", f"manifest {section} entry is incomplete")
            path = repo / safe_repo_path(rel)
            if not path.is_file():
                fail(code, f"manifest-bound file disappeared", path=rel)
            actual_hash = file_sha256(path)
            if actual_hash != expected_hash:
                fail(
                    code,
                    "manifest-bound file hash changed",
                    path=rel,
                    expected=expected_hash,
                    actual=actual_hash,
                )


def path_is_allowed(path: str, allowed_scope: Iterable[str], forbidden_scope: Iterable[str]) -> bool:
    rel = safe_repo_path(path)
    allowed = any(fnmatch(rel, pattern) for pattern in allowed_scope)
    forbidden = any(fnmatch(rel, pattern) for pattern in forbidden_scope)
    return allowed and not forbidden


def assert_paths_allowed(
    paths: Iterable[str],
    *,
    allowed_scope: Iterable[str],
    forbidden_scope: Iterable[str],
) -> None:
    rejected = [
        safe_repo_path(path)
        for path in paths
        if not path_is_allowed(path, allowed_scope, forbidden_scope)
    ]
    if rejected:
        fail("SCOPE_VIOLATION", "candidate touched paths outside permitted scope", paths=rejected)


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)

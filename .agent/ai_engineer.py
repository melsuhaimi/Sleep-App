"""Controller-owned bounded AI engineering orchestration."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bootstrap import HarnessError, fail, read_json, repo_root, verify_manifest
from ai_contract import STOP_STATUSES, apply_proposal, assert_expected_mutation, validate_proposal
from ai_openai import request_proposal
from ai_support import build_prompt, clean, config, restore_clean, validate_output_path, write_json, worktree_snapshot
from ai_verifier import failure as verification_failure
from ai_verifier import gates as verification_gates
from ai_verifier import run as run_verification


def _fake_path(path: str | Path, repo: Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else repo / value


def _load_fake_response(path: str | Path, manifest: dict[str, Any], repo: Path) -> dict[str, Any]:
    proposal = read_json(_fake_path(path, repo))
    proposal = json.loads(json.dumps(proposal))
    if proposal.get("run_id") == "__RUN_ID__":
        proposal["run_id"] = manifest["run_id"]
    if proposal.get("manifest_commit") == "__MANIFEST_COMMIT__":
        proposal["manifest_commit"] = manifest["repo"]["commit"]
    return proposal


def _evidence_base(manifest: dict[str, Any], cfg: dict[str, Any], request_attempted: bool, attempts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "protocol_version": 1,
        "run_id": manifest["run_id"],
        "manifest_commit": manifest["repo"]["commit"],
        "model": cfg.get("openai_model"),
        "request_attempted": request_attempted,
        "attempts": attempts,
    }


def _blocked(
    manifest: dict[str, Any],
    cfg: dict[str, Any],
    attempts: list[dict[str, Any]],
    request_attempted: bool,
    code: str,
    message: str,
    details: dict[str, Any] | None,
    repo: Path,
    evidence_path: str | Path | None,
) -> dict[str, Any]:
    evidence = {
        **_evidence_base(manifest, cfg, request_attempted, attempts),
        "status": "BLOCKED",
        "code": code,
        "message": message,
        "details": details,
    }
    write_json(evidence_path, evidence, repo)
    return evidence


def run_engineering_step(
    manifest: dict[str, Any],
    *,
    result_path: str | Path | None = None,
    evidence_path: str | Path | None = None,
    fake_response_path: str | Path | None = None,
    start: str | Path | None = None,
) -> dict[str, Any]:
    repo = repo_root(start)
    verify_manifest(manifest, start=repo)
    cfg = config(repo)
    validate_output_path(result_path, repo)
    validate_output_path(evidence_path, repo)
    clean(repo)
    verification_gates(cfg, manifest["task"]["required_verification"])

    max_attempts = manifest["policy"]["max_attempts_per_task"]
    max_same = manifest["policy"]["max_same_failure_repeats"]
    attempts: list[dict[str, Any]] = []
    repeats: dict[str, int] = {}
    previous_failure: dict[str, Any] | None = None
    request_attempted = False

    for attempt_number in range(1, max_attempts + 1):
        verify_manifest(manifest, start=repo)
        clean(repo)
        prompt = build_prompt(manifest, start=repo)
        if previous_failure is not None:
            prompt += "\n\nPrevious deterministic verification failure:\n" + json.dumps(previous_failure, sort_keys=True)

        try:
            if fake_response_path is not None:
                proposal = _load_fake_response(fake_response_path, manifest, repo)
                provider_meta = {"request_attempted": False, "response_id": None, "model": None, "source": "fake"}
            else:
                proposal, provider_meta = request_proposal(prompt, cfg, repo)
                provider_meta["source"] = "openai"
            request_attempted = request_attempted or bool(provider_meta.get("request_attempted"))
            proposal = validate_proposal(proposal, manifest, cfg, repo)
            write_json(result_path, proposal, repo)
        except HarnessError as exc:
            if exc.details and exc.details.get("request_attempted"):
                request_attempted = True
            return _blocked(
                manifest, cfg, attempts, request_attempted, exc.code, exc.message, exc.details,
                repo, evidence_path,
            )

        if proposal["status"] in STOP_STATUSES:
            evidence = {
                **_evidence_base(manifest, cfg, request_attempted, attempts),
                "status": proposal["status"],
                "proposal_summary": proposal["summary"],
            }
            write_json(evidence_path, evidence, repo)
            return evidence

        try:
            apply_proposal(repo, proposal)
            pre_verify = assert_expected_mutation(repo, proposal)
            verification = run_verification(repo, manifest, cfg)
            post_verify = worktree_snapshot(repo)
            if post_verify != pre_verify:
                restore_clean(repo)
                return _blocked(
                    manifest, cfg, attempts, request_attempted,
                    "VERIFIER_MUTATION",
                    "verification commands changed repository contents",
                    {"before": pre_verify, "after": post_verify},
                    repo, evidence_path,
                )
        except HarnessError as exc:
            restore_clean(repo)
            return _blocked(
                manifest, cfg, attempts, request_attempted, exc.code, exc.message, exc.details,
                repo, evidence_path,
            )

        failed = verification_failure(verification)
        attempt = {
            "attempt": attempt_number,
            "source": provider_meta.get("source"),
            "response_id": provider_meta.get("response_id"),
            "proposal_status": proposal["status"],
            "mutated_paths": list(proposal["files_to_modify"]),
            "verification": verification,
            "failure": failed,
        }
        attempts.append(attempt)

        if failed is None:
            evidence = {
                **_evidence_base(manifest, cfg, request_attempted, attempts),
                "status": "VERIFIED_CANDIDATE",
                "verified_paths": list(proposal["files_to_modify"]),
            }
            write_json(evidence_path, evidence, repo)
            return evidence

        restore_clean(repo)
        signature = failed["signature"]
        repeats[signature] = repeats.get(signature, 0) + 1
        if repeats[signature] >= max_same:
            return _blocked(
                manifest, cfg, attempts, request_attempted,
                "REPEATED_VERIFICATION_FAILURE",
                "the same deterministic verification failure reached its retry limit",
                {"signature": signature, "repeats": repeats[signature]},
                repo, evidence_path,
            )
        if attempt_number >= max_attempts:
            return _blocked(
                manifest, cfg, attempts, request_attempted,
                "RETRY_EXHAUSTED",
                "bounded AI verification attempts were exhausted",
                {"attempts": attempt_number},
                repo, evidence_path,
            )
        previous_failure = failed

    fail("INTERNAL_ERROR", "bounded AI loop exited unexpectedly")

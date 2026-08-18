"""Validate, apply, and deterministically verify one externally authored proposal."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from bootstrap import HarnessError, read_json, repo_root, verify_manifest
from proposal_contract import STOP_STATUSES, apply_proposal, assert_expected_mutation, validate_proposal
from proposal_support import clean, config, restore_clean, validate_output_path, write_json, worktree_snapshot
from proposal_verifier import failure as verification_failure
from proposal_verifier import gates as verification_gates
from proposal_verifier import run as run_verification


def _proposal_path(path: str | Path, repo: Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else repo / value


def _evidence_base(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocol_version": 1,
        "run_id": manifest["run_id"],
        "manifest_commit": manifest["repo"]["commit"],
        "source": "external-proposal",
    }


def _blocked(
    manifest: dict[str, Any],
    code: str,
    message: str,
    details: dict[str, Any] | None,
    repo: Path,
    evidence_path: str | Path | None,
    *,
    verification: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    evidence = {
        **_evidence_base(manifest),
        "status": "BLOCKED",
        "code": code,
        "message": message,
        "details": details,
        **({"verification": verification} if verification is not None else {}),
    }
    write_json(evidence_path, evidence, repo)
    return evidence


def run_proposal(
    manifest: dict[str, Any],
    *,
    proposal_path: str | Path,
    result_path: str | Path | None = None,
    evidence_path: str | Path | None = None,
    start: str | Path | None = None,
) -> dict[str, Any]:
    repo = repo_root(start)
    verify_manifest(manifest, start=repo)
    cfg = config(repo)
    validate_output_path(result_path, repo)
    validate_output_path(evidence_path, repo)
    clean(repo)
    verification_gates(cfg, manifest["task"]["required_verification"])

    try:
        proposal = read_json(_proposal_path(proposal_path, repo))
        proposal = validate_proposal(proposal, manifest, cfg, repo)
        write_json(result_path, proposal, repo)
    except HarnessError as exc:
        return _blocked(manifest, exc.code, exc.message, exc.details, repo, evidence_path)

    if proposal["status"] in STOP_STATUSES:
        evidence = {
            **_evidence_base(manifest),
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
                manifest,
                "VERIFIER_MUTATION",
                "verification commands changed repository contents",
                {"before": pre_verify, "after": post_verify},
                repo,
                evidence_path,
                verification=verification,
            )
    except HarnessError as exc:
        restore_clean(repo)
        return _blocked(manifest, exc.code, exc.message, exc.details, repo, evidence_path)

    failed = verification_failure(verification)
    if failed is not None:
        restore_clean(repo)
        return _blocked(
            manifest,
            "VERIFICATION_FAILED",
            "deterministic verification rejected the proposal",
            failed,
            repo,
            evidence_path,
            verification=verification,
        )

    evidence = {
        **_evidence_base(manifest),
        "status": "VERIFIED_CANDIDATE",
        "verified_paths": list(proposal["files_to_modify"]),
        "verification": verification,
    }
    write_json(evidence_path, evidence, repo)
    return evidence

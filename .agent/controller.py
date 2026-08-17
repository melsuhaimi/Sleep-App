#!/usr/bin/env python3
"""Deterministic control-plane entrypoint for the Sleep App engineering harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from bootstrap import HarnessError, assert_paths_allowed, build_manifest, fail, read_json, verify_manifest, write_json_atomic


def emit(value: dict) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--task", help="Task envelope JSON path")
    mode.add_argument("--verify-manifest", help="Existing manifest JSON path")
    parser.add_argument("--output", help="Write generated manifest to this path")
    parser.add_argument("--changed-path", action="append", default=[], help="Candidate changed path to enforce; repeatable")
    parser.add_argument("--run-ai", action="store_true", help="Run bounded AI only after bootstrap and re-verification")
    parser.add_argument("--result", help="Write validated model proposal JSON")
    parser.add_argument("--evidence", help="Write controller-owned execution evidence JSON")
    parser.add_argument("--fake-response", help="TEST ONLY: deterministic proposal fixture; does not invoke OpenAI")
    args = parser.parse_args()

    try:
        if args.verify_manifest:
            if args.run_ai or args.result or args.evidence or args.fake_response:
                fail("INVALID_CLI", "AI execution flags require --task")
            manifest = read_json(Path(args.verify_manifest))
            verify_manifest(manifest)
            emit({"status": "READY", "check": "manifest-current", "run_id": manifest.get("run_id")})
            return 0

        if args.fake_response and not args.run_ai:
            fail("INVALID_CLI", "--fake-response requires --run-ai")

        manifest = build_manifest(args.task)
        verify_manifest(manifest)
        if args.changed_path:
            task = manifest["task"]
            assert_paths_allowed(args.changed_path, allowed_scope=task["allowed_scope"], forbidden_scope=task.get("forbidden_scope", []))
        if args.output:
            write_json_atomic(Path(args.output), manifest)

        if not args.run_ai:
            emit({
                "status": "READY", "phase": manifest["phase"], "run_id": manifest["run_id"],
                "commit": manifest["repo"]["commit"], "instruction_count": len(manifest["instructions"]),
                "skill_count": len(manifest["skills"]),
                "mandatory_context_bytes": manifest["context_budget"]["mandatory_bytes"], "ai_invoked": False,
            })
            return 0

        from ai_engineer import run_engineering_step
        outcome = run_engineering_step(manifest, result_path=args.result, evidence_path=args.evidence, fake_response_path=args.fake_response)
        emit({**outcome, "phase": manifest["phase"], "ai_invoked": bool(outcome.get("request_attempted"))})
        return 0 if outcome["status"] == "VERIFIED_CANDIDATE" else 3
    except HarnessError as exc:
        emit({"status": "BLOCKED", "code": exc.code, "message": exc.message, "details": exc.details, "ai_invoked": False})
        return 2


if __name__ == "__main__":
    sys.exit(main())

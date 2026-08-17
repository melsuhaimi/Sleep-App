#!/usr/bin/env python3
"""Deterministic control-plane entrypoint for Harness v1.

Harness v1 intentionally does NOT invoke an AI model. It proves the bootstrap
boundary first.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from bootstrap import (
    HarnessError,
    assert_paths_allowed,
    build_manifest,
    read_json,
    verify_manifest,
    write_json_atomic,
)


def emit(value: dict) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--task", help="Task envelope JSON path")
    mode.add_argument("--verify-manifest", help="Existing manifest JSON path")
    parser.add_argument("--output", help="Write generated manifest to this path")
    parser.add_argument(
        "--changed-path",
        action="append",
        default=[],
        help="Candidate changed path to check against task mutation scope; repeatable",
    )
    args = parser.parse_args()

    try:
        if args.verify_manifest:
            manifest = read_json(Path(args.verify_manifest))
            verify_manifest(manifest)
            emit(
                {
                    "status": "READY",
                    "check": "manifest-current",
                    "run_id": manifest.get("run_id"),
                }
            )
            return 0

        manifest = build_manifest(args.task)
        # Re-verify immediately so creation and verification are independent steps.
        verify_manifest(manifest)

        if args.changed_path:
            task = manifest["task"]
            assert_paths_allowed(
                args.changed_path,
                allowed_scope=task["allowed_scope"],
                forbidden_scope=task.get("forbidden_scope", []),
            )

        if args.output:
            write_json_atomic(Path(args.output), manifest)

        emit(
            {
                "status": "READY",
                "phase": manifest["phase"],
                "run_id": manifest["run_id"],
                "commit": manifest["repo"]["commit"],
                "instruction_count": len(manifest["instructions"]),
                "skill_count": len(manifest["skills"]),
                "mandatory_context_bytes": manifest["context_budget"]["mandatory_bytes"],
                "ai_invoked": False,
            }
        )
        return 0
    except HarnessError as exc:
        emit(
            {
                "status": "BLOCKED",
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "ai_invoked": False,
            }
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())

"""Controller-owned verification registry execution and failure signatures."""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from typing import Any
from bootstrap import fail


def gates(cfg: dict[str, Any], required: list[str]) -> dict[str, list[str]]:
    registry = cfg.get("verification_gates")
    if not isinstance(registry, dict):
        fail("INVALID_CONFIG", "verification_gates must be configured")
    selected = {}
    for gate in required:
        command = registry.get(gate)
        if not isinstance(command, list) or not command or not all(isinstance(v, str) and v for v in command):
            fail("UNKNOWN_VERIFICATION_GATE", "required verification gate is not executable", gate=gate)
        selected[gate] = command
    return selected


def run(repo: Path, manifest: dict[str, Any], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    required = manifest["task"]["required_verification"]
    registry = gates(cfg, required)
    timeout = cfg.get("verification_timeout_seconds", 900)
    limit = cfg.get("max_verification_output_bytes", 32768)
    if not isinstance(timeout, int) or timeout <= 0 or not isinstance(limit, int) or limit <= 0:
        fail("INVALID_CONFIG", "verification limits must be positive integers")
    evidence = []
    for gate in required:
        argv = [v.replace("{commit}", manifest["repo"]["commit"]) for v in registry[gate]]
        try:
            proc = subprocess.run(
                argv,
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=timeout,
            )
            rc, out, err = proc.returncode, proc.stdout, proc.stderr
        except FileNotFoundError as exc:
            rc, out, err = 127, "", str(exc)
        except subprocess.TimeoutExpired as exc:
            rc = 124
            out = exc.stdout if isinstance(exc.stdout, str) else ""
            err = exc.stderr if isinstance(exc.stderr, str) else ""
        evidence.append({
            "gate": gate,
            "argv": argv,
            "returncode": rc,
            "stdout_sha256": sha256(out.encode()).hexdigest(),
            "stderr_sha256": sha256(err.encode()).hexdigest(),
            "stdout_tail": out[-limit:],
            "stderr_tail": err[-limit:],
        })
        if rc:
            break
    return evidence


def failure(evidence: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in evidence:
        if item["returncode"]:
            raw = json.dumps(
                {k: item[k] for k in ("gate", "returncode", "stdout_sha256", "stderr_sha256")},
                sort_keys=True,
            ).encode()
            return {
                "gate": item["gate"],
                "returncode": item["returncode"],
                "signature": sha256(raw).hexdigest(),
                "stdout_tail": item["stdout_tail"],
                "stderr_tail": item["stderr_tail"],
            }
    return None

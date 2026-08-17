#!/usr/bin/env python3
"""Deterministically verify the Checkpoint 2 debug APK and emit evidence."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ANDROID_NS = "http://schemas.android.com/apk/res/android"
BUILD_COMMIT_META = "com.melsuhaimi.sleepapp.BUILD_COMMIT"


def fail(message: str) -> None:
    raise RuntimeError(message)


def tool(name: str, fallback_parts: tuple[str, ...] | None = None) -> str:
    found = shutil.which(name)
    if found:
        return found
    sdk = os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME")
    if sdk and fallback_parts:
        candidate = Path(sdk).joinpath(*fallback_parts)
        if candidate.is_file():
            return str(candidate)
    fail(f"required Android tool not found: {name}")


def run(*args: str) -> str:
    proc = subprocess.run(
        args,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        fail(
            f"command failed ({proc.returncode}): {' '.join(args)}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc.stdout.strip()


def file_sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_metadata_value(xml_text: str, name: str) -> str | None:
    root = ET.fromstring(xml_text)
    application = root.find("application")
    if application is None:
        return None
    android_name = f"{{{ANDROID_NS}}}name"
    android_value = f"{{{ANDROID_NS}}}value"
    for item in application.findall("meta-data"):
        if item.get(android_name) == name:
            return item.get(android_value)
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--expected-application-id", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    apk = Path(args.apk).resolve()
    output = Path(args.output).resolve()

    try:
        if not apk.is_file() or apk.stat().st_size <= 0:
            fail(f"APK missing or empty: {apk}")
        if len(args.expected_commit) != 40 or any(c not in "0123456789abcdef" for c in args.expected_commit):
            fail("expected commit must be a lowercase full 40-character Git SHA")

        apkanalyzer = tool("apkanalyzer", ("cmdline-tools", "latest", "bin", "apkanalyzer"))
        apksigner = tool("apksigner", ("build-tools", "36.0.0", "apksigner"))

        application_id = run(apkanalyzer, "manifest", "application-id", str(apk))
        version_code = run(apkanalyzer, "manifest", "version-code", str(apk))
        version_name = run(apkanalyzer, "manifest", "version-name", str(apk))
        min_sdk = run(apkanalyzer, "manifest", "min-sdk", str(apk))
        target_sdk = run(apkanalyzer, "manifest", "target-sdk", str(apk))
        debuggable = run(apkanalyzer, "manifest", "debuggable", str(apk)).lower()
        manifest_xml = run(apkanalyzer, "manifest", "print", str(apk))
        embedded_commit = manifest_metadata_value(manifest_xml, BUILD_COMMIT_META)

        if application_id != args.expected_application_id:
            fail(f"application id mismatch: {application_id!r}")
        if min_sdk != "26":
            fail(f"min SDK mismatch: {min_sdk!r}")
        if target_sdk != "36":
            fail(f"target SDK mismatch: {target_sdk!r}")
        if debuggable != "true":
            fail(f"debuggable flag mismatch: {debuggable!r}")
        if embedded_commit != args.expected_commit:
            fail(
                "APK commit binding mismatch: "
                f"embedded={embedded_commit!r}, expected={args.expected_commit!r}"
            )

        signature_output = run(apksigner, "verify", "--verbose", "--print-certs", str(apk))

        evidence = {
            "schema_version": 1,
            "status": "VERIFIED",
            "commit": args.expected_commit,
            "apk": {
                "path": str(apk),
                "bytes": apk.stat().st_size,
                "sha256": file_sha256(apk),
                "application_id": application_id,
                "version_code": version_code,
                "version_name": version_name,
                "min_sdk": min_sdk,
                "target_sdk": target_sdk,
                "debuggable": True,
                "embedded_commit": embedded_commit,
            },
            "signature": {
                "verified": True,
                "output": signature_output.splitlines(),
            },
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        temp = output.with_suffix(output.suffix + ".tmp")
        temp.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp.replace(output)
        print(json.dumps(evidence, indent=2, sort_keys=True))
        return 0
    except (RuntimeError, ET.ParseError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

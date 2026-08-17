from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

AGENT_DIR = Path(__file__).resolve().parents[1]
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from bootstrap import (  # noqa: E402
    HarnessError,
    assert_paths_allowed,
    build_manifest,
    verify_manifest,
)


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return proc.stdout.strip()


class HarnessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.email", "harness@example.invalid")
        git(self.repo, "config", "user.name", "Harness Test")

        (self.repo / ".agent/skills").mkdir(parents=True)
        (self.repo / "AGENTS.md").write_text("# Root instructions\n", encoding="utf-8")
        self.write_config()
        self.write_skill_index([])
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "fixture")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_config(self, **overrides) -> None:
        config = {
            "protocol_version": 1,
            "phase": "bootstrap-only",
            "required_root_instruction": "AGENTS.md",
            "max_mandatory_context_bytes": 65536,
            "max_instruction_file_bytes": 32768,
            "max_skill_file_bytes": 65536,
            "max_attempts_per_task": 4,
            "max_same_failure_repeats": 2,
        }
        config.update(overrides)
        path = self.repo / ".agent/config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config), encoding="utf-8")

    def write_skill_index(self, skills) -> None:
        (self.repo / ".agent/skills/index.json").write_text(
            json.dumps({"schema_version": 1, "skills": skills}),
            encoding="utf-8",
        )

    def task(self, **overrides) -> Path:
        value = {
            "schema_version": 1,
            "task_id": "test-task",
            "objective": "Validate harness",
            "acceptance": ["It is deterministic"],
            "allowed_scope": [".agent/**"],
            "forbidden_scope": ["app/**"],
            "required_verification": ["unit"],
            "context_paths": [],
        }
        value.update(overrides)
        path = self.repo / "task.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def assert_error(self, code: str, fn) -> HarnessError:
        with self.assertRaises(HarnessError) as ctx:
            fn()
        self.assertEqual(code, ctx.exception.code)
        return ctx.exception

    def test_valid_manifest_binds_current_commit(self) -> None:
        manifest = build_manifest(self.task(), start=self.repo)
        self.assertEqual("READY", manifest["status"])
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), manifest["repo"]["commit"])
        self.assertEqual(["AGENTS.md"], [v["path"] for v in manifest["instructions"]])
        verify_manifest(manifest, start=self.repo)

    def test_stale_expected_commit_is_blocked(self) -> None:
        task = self.task(expected_base_commit="deadbee")
        self.assert_error(
            "STALE_BASE_COMMIT",
            lambda: build_manifest(task, start=self.repo),
        )

    def test_missing_root_agents_is_blocked(self) -> None:
        (self.repo / "AGENTS.md").unlink()
        self.assert_error(
            "MISSING_ROOT_INSTRUCTIONS",
            lambda: build_manifest(self.task(), start=self.repo),
        )

    def test_instruction_hash_change_invalidates_manifest(self) -> None:
        manifest = build_manifest(self.task(), start=self.repo)
        (self.repo / "AGENTS.md").write_text("# changed\n", encoding="utf-8")
        self.assert_error(
            "INSTRUCTION_CHANGED",
            lambda: verify_manifest(manifest, start=self.repo),
        )

    def test_manifest_is_invalid_after_head_moves(self) -> None:
        manifest = build_manifest(self.task(), start=self.repo)
        (self.repo / "new.txt").write_text("change", encoding="utf-8")
        git(self.repo, "add", "new.txt")
        git(self.repo, "commit", "-m", "move head")
        self.assert_error(
            "MANIFEST_STALE",
            lambda: verify_manifest(manifest, start=self.repo),
        )

    def test_nested_agents_are_discovered_from_context_path(self) -> None:
        (self.repo / "app").mkdir()
        (self.repo / "app/AGENTS.md").write_text("# App rules\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "nested rules")
        manifest = build_manifest(
            self.task(context_paths=["app/src/Future.kt"]),
            start=self.repo,
        )
        self.assertEqual(
            ["AGENTS.md", "app/AGENTS.md"],
            [v["path"] for v in manifest["instructions"]],
        )

    def test_override_is_more_specific_than_normal_file(self) -> None:
        (self.repo / "app").mkdir()
        (self.repo / "app/AGENTS.md").write_text("# normal\n", encoding="utf-8")
        (self.repo / "app/AGENTS.override.md").write_text("# override\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "override")
        manifest = build_manifest(
            self.task(context_paths=["app/Future.kt"]),
            start=self.repo,
        )
        paths = [v["path"] for v in manifest["instructions"]]
        self.assertIn("AGENTS.md", paths)
        self.assertIn("app/AGENTS.override.md", paths)
        self.assertNotIn("app/AGENTS.md", paths)

    def test_context_overflow_blocks_before_any_agent(self) -> None:
        self.write_config(max_mandatory_context_bytes=1)
        self.assert_error(
            "CONTEXT_OVERFLOW",
            lambda: build_manifest(self.task(), start=self.repo),
        )

    def test_malformed_task_is_blocked(self) -> None:
        task = self.task(acceptance=[])
        self.assert_error(
            "INVALID_TASK",
            lambda: build_manifest(task, start=self.repo),
        )

    def test_scope_enforcement(self) -> None:
        assert_paths_allowed(
            [".agent/bootstrap.py"],
            allowed_scope=[".agent/**"],
            forbidden_scope=[".agent/secrets/**"],
        )
        self.assert_error(
            "SCOPE_VIOLATION",
            lambda: assert_paths_allowed(
                ["app/src/Main.kt"],
                allowed_scope=[".agent/**"],
                forbidden_scope=[],
            ),
        )
        self.assert_error(
            "SCOPE_VIOLATION",
            lambda: assert_paths_allowed(
                [".agent/secrets/token.txt"],
                allowed_scope=[".agent/**"],
                forbidden_scope=[".agent/secrets/**"],
            ),
        )

    def test_skill_trigger_and_dependency_are_deterministic(self) -> None:
        build_dir = self.repo / ".agent/skills/android-build"
        base_dir = self.repo / ".agent/skills/base"
        build_dir.mkdir(parents=True)
        base_dir.mkdir(parents=True)
        (build_dir / "SKILL.md").write_text("# Android build\n", encoding="utf-8")
        (base_dir / "SKILL.md").write_text("# Base\n", encoding="utf-8")
        self.write_skill_index(
            [
                {
                    "id": "base",
                    "path": ".agent/skills/base/SKILL.md",
                    "triggers": [],
                    "requires": [],
                },
                {
                    "id": "android-build",
                    "path": ".agent/skills/android-build/SKILL.md",
                    "triggers": ["android", "apk"],
                    "requires": ["base"],
                },
            ]
        )
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "skills")
        manifest = build_manifest(
            self.task(objective="Build an Android APK"),
            start=self.repo,
        )
        self.assertEqual(["base", "android-build"], [v["id"] for v in manifest["skills"]])

    def test_missing_skill_dependency_blocks(self) -> None:
        build_dir = self.repo / ".agent/skills/android-build"
        build_dir.mkdir(parents=True)
        (build_dir / "SKILL.md").write_text("# Android build\n", encoding="utf-8")
        self.write_skill_index(
            [
                {
                    "id": "android-build",
                    "path": ".agent/skills/android-build/SKILL.md",
                    "triggers": ["android"],
                    "requires": ["missing-base"],
                }
            ]
        )
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "broken skill dependency")
        self.assert_error(
            "MISSING_SKILL_DEPENDENCY",
            lambda: build_manifest(
                self.task(objective="Build Android"),
                start=self.repo,
            ),
        )


if __name__ == "__main__":
    unittest.main()

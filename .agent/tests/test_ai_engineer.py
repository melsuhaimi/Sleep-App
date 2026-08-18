from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

AGENT_DIR = Path(__file__).resolve().parents[1]
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from bootstrap import HarnessError, build_manifest  # noqa: E402
from ai_engineer import run_engineering_step  # noqa: E402


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


class BoundedAIEngineerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.side = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.side_dir = Path(self.side.name)
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.email", "ai-harness@example.invalid")
        git(self.repo, "config", "user.name", "AI Harness Test")
        (self.repo / ".agent/skills").mkdir(parents=True)
        (self.repo / ".agent/schemas").mkdir(parents=True)
        (self.repo / "AGENTS.md").write_text("# Root instructions\n", encoding="utf-8")
        (self.repo / ".agent/skills/index.json").write_text(
            json.dumps({"schema_version": 1, "skills": []}), encoding="utf-8"
        )
        (self.repo / ".agent/schemas/result.schema.json").write_text(
            json.dumps({"type": "object", "additionalProperties": False, "properties": {}}),
            encoding="utf-8",
        )
        (self.repo / "work.txt").write_text("original\n", encoding="utf-8")
        self.write_config()
        self.commit("fixture")

    def tearDown(self) -> None:
        self.tmp.cleanup()
        self.side.cleanup()

    def commit(self, message: str) -> None:
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", message)

    def write_config(self, **overrides) -> None:
        config = {
            "protocol_version": 1,
            "phase": "bounded-ai",
            "required_root_instruction": "AGENTS.md",
            "max_mandatory_context_bytes": 65536,
            "max_instruction_file_bytes": 32768,
            "max_skill_file_bytes": 65536,
            "max_attempts_per_task": 4,
            "max_same_failure_repeats": 2,
            "max_ai_context_file_bytes": 32768,
            "max_ai_context_bytes": 131072,
            "max_ai_edit_file_bytes": 65536,
            "max_ai_total_edit_bytes": 196608,
            "max_ai_output_tokens": 12000,
            "max_openai_response_bytes": 1048576,
            "openai_model": "gpt-5.6",
            "openai_responses_url": "https://api.openai.com/v1/responses",
            "openai_timeout_seconds": 1,
            "verification_timeout_seconds": 30,
            "max_verification_output_bytes": 32768,
            "verification_gates": {
                "unit": [sys.executable, "-c", "raise SystemExit(0)"],
            },
        }
        config.update(overrides)
        path = self.repo / ".agent/config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config), encoding="utf-8")

    def task(self, **overrides) -> Path:
        task = {
            "schema_version": 1,
            "task_id": "bounded-ai-test",
            "objective": "Change one bounded test file",
            "acceptance": ["Controller verification owns success"],
            "allowed_scope": ["work.txt", "new.txt"],
            "forbidden_scope": [],
            "required_verification": ["unit"],
            "context_paths": ["work.txt"],
        }
        task.update(overrides)
        path = self.side_dir / "task.json"
        path.write_text(json.dumps(task), encoding="utf-8")
        return path

    def manifest(self, **task_overrides) -> dict:
        return build_manifest(self.task(**task_overrides), start=self.repo)

    def proposal(self, manifest: dict, content: str = "candidate\n", **overrides) -> dict:
        value = {
            "schema_version": 1,
            "run_id": manifest["run_id"],
            "manifest_commit": manifest["repo"]["commit"],
            "status": "CANDIDATE",
            "summary": "bounded edit",
            "assumptions": [],
            "unknowns": [],
            "files_to_modify": ["work.txt"],
            "verification_required": list(manifest["task"]["required_verification"]),
            "edits": [{"path": "work.txt", "content": content}],
        }
        value.update(overrides)
        return value

    def fake(self, value: dict) -> Path:
        path = self.side_dir / "response.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def assert_blocked(self, outcome: dict, code: str) -> None:
        self.assertEqual("BLOCKED", outcome["status"])
        self.assertEqual(code, outcome["code"])

    def test_stale_manifest_blocks_before_execution(self) -> None:
        manifest = self.manifest()
        (self.repo / "head.txt").write_text("move\n", encoding="utf-8")
        self.commit("move head")
        with self.assertRaises(HarnessError) as ctx:
            run_engineering_step(manifest, fake_response_path=self.fake(self.proposal(manifest)), start=self.repo)
        self.assertEqual("MANIFEST_STALE", ctx.exception.code)

    def test_dirty_worktree_blocks_before_execution(self) -> None:
        manifest = self.manifest()
        (self.repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaises(HarnessError) as ctx:
            run_engineering_step(manifest, fake_response_path=self.fake(self.proposal(manifest)), start=self.repo)
        self.assertEqual("DIRTY_WORKTREE", ctx.exception.code)

    def test_missing_credentials_stop_without_request(self) -> None:
        manifest = self.manifest()
        with mock.patch.dict(os.environ, {}, clear=True):
            outcome = run_engineering_step(manifest, start=self.repo)
        self.assert_blocked(outcome, "MISSING_OPENAI_API_KEY")
        self.assertFalse(outcome["request_attempted"])

    def test_malformed_output_is_rejected(self) -> None:
        manifest = self.manifest()
        outcome = run_engineering_step(manifest, fake_response_path=self.fake({"schema_version": 1}), start=self.repo)
        self.assert_blocked(outcome, "MODEL_OUTPUT_INVALID")
        self.assertEqual("original\n", (self.repo / "work.txt").read_text())

    def test_manifest_identity_mismatch_is_rejected(self) -> None:
        manifest = self.manifest()
        proposal = self.proposal(manifest, run_id="wrong@run")
        outcome = run_engineering_step(manifest, fake_response_path=self.fake(proposal), start=self.repo)
        self.assert_blocked(outcome, "PROPOSAL_RUN_MISMATCH")

    def test_verification_contract_cannot_be_downgraded(self) -> None:
        manifest = self.manifest()
        proposal = self.proposal(manifest, verification_required=[])
        outcome = run_engineering_step(manifest, fake_response_path=self.fake(proposal), start=self.repo)
        self.assert_blocked(outcome, "VERIFICATION_CONTRACT_MISMATCH")

    def test_forbidden_mutation_is_rejected(self) -> None:
        manifest = self.manifest(forbidden_scope=["work.txt"])
        outcome = run_engineering_step(manifest, fake_response_path=self.fake(self.proposal(manifest)), start=self.repo)
        self.assert_blocked(outcome, "SCOPE_VIOLATION")

    def test_ignored_mutation_is_rejected(self) -> None:
        (self.repo / ".gitignore").write_text("new.txt\n", encoding="utf-8")
        self.commit("ignore path")
        manifest = self.manifest(allowed_scope=["new.txt"])
        proposal = self.proposal(
            manifest,
            files_to_modify=["new.txt"],
            edits=[{"path": "new.txt", "content": "new\n"}],
        )
        outcome = run_engineering_step(manifest, fake_response_path=self.fake(proposal), start=self.repo)
        self.assert_blocked(outcome, "IGNORED_EDIT_REJECTED")

    def test_symlink_mutation_is_rejected(self) -> None:
        (self.repo / "target.txt").write_text("target\n", encoding="utf-8")
        (self.repo / "link.txt").symlink_to("target.txt")
        self.commit("symlink")
        manifest = self.manifest(allowed_scope=["link.txt"], context_paths=[])
        proposal = self.proposal(
            manifest,
            files_to_modify=["link.txt"],
            edits=[{"path": "link.txt", "content": "replace\n"}],
        )
        outcome = run_engineering_step(manifest, fake_response_path=self.fake(proposal), start=self.repo)
        self.assert_blocked(outcome, "SYMLINK_EDIT_REJECTED")

    def test_edit_budget_is_enforced(self) -> None:
        self.write_config(max_ai_edit_file_bytes=4)
        self.commit("small edit budget")
        manifest = self.manifest()
        outcome = run_engineering_step(manifest, fake_response_path=self.fake(self.proposal(manifest, content="too large")), start=self.repo)
        self.assert_blocked(outcome, "EDIT_BUDGET_EXCEEDED")

    def test_unknown_verification_gate_blocks_before_provider(self) -> None:
        manifest = self.manifest(required_verification=["missing-gate"])
        with self.assertRaises(HarnessError) as ctx:
            run_engineering_step(manifest, start=self.repo)
        self.assertEqual("UNKNOWN_VERIFICATION_GATE", ctx.exception.code)

    def test_stop_status_never_mutates(self) -> None:
        manifest = self.manifest()
        proposal = self.proposal(
            manifest,
            status="NEEDS_MORE_CONTEXT",
            summary="need exact dependency",
            files_to_modify=[],
            edits=[],
        )
        outcome = run_engineering_step(manifest, fake_response_path=self.fake(proposal), start=self.repo)
        self.assertEqual("NEEDS_MORE_CONTEXT", outcome["status"])
        self.assertEqual("original\n", (self.repo / "work.txt").read_text())

    def test_successful_candidate_requires_controller_verification(self) -> None:
        manifest = self.manifest()
        outcome = run_engineering_step(manifest, fake_response_path=self.fake(self.proposal(manifest)), start=self.repo)
        self.assertEqual("VERIFIED_CANDIDATE", outcome["status"])
        self.assertFalse(outcome["request_attempted"])
        self.assertEqual("candidate\n", (self.repo / "work.txt").read_text())
        self.assertEqual(1, len(outcome["attempts"]))

    def test_repeated_identical_failure_rolls_back_and_stops(self) -> None:
        self.write_config(verification_gates={"unit": [sys.executable, "-c", "print('same'); raise SystemExit(1)"]})
        self.commit("failing verifier")
        manifest = self.manifest()
        outcome = run_engineering_step(manifest, fake_response_path=self.fake(self.proposal(manifest)), start=self.repo)
        self.assert_blocked(outcome, "REPEATED_VERIFICATION_FAILURE")
        self.assertEqual(2, len(outcome["attempts"]))
        self.assertEqual("original\n", (self.repo / "work.txt").read_text())
        self.assertEqual("", git(self.repo, "status", "--porcelain=v1", "--untracked-files=all"))

    def test_retry_exhaustion_is_bounded(self) -> None:
        counter = self.side_dir / "counter.txt"
        script = (
            "from pathlib import Path; import sys; "
            f"p=Path({str(counter)!r}); n=int(p.read_text())+1 if p.exists() else 1; p.write_text(str(n)); print(n); sys.exit(1)"
        )
        self.write_config(
            max_attempts_per_task=3,
            max_same_failure_repeats=2,
            verification_gates={"unit": [sys.executable, "-c", script]},
        )
        self.commit("varying failures")
        manifest = self.manifest()
        outcome = run_engineering_step(manifest, fake_response_path=self.fake(self.proposal(manifest)), start=self.repo)
        self.assert_blocked(outcome, "RETRY_EXHAUSTED")
        self.assertEqual(3, len(outcome["attempts"]))
        self.assertEqual("original\n", (self.repo / "work.txt").read_text())

    def test_failed_candidate_can_recover_with_new_proposal(self) -> None:
        script = "from pathlib import Path; import sys; sys.exit(0 if Path('work.txt').read_text() == 'good\\n' else 1)"
        self.write_config(verification_gates={"unit": [sys.executable, "-c", script]})
        self.commit("content verifier")
        manifest = self.manifest()
        bad = self.proposal(manifest, content="bad\n")
        good = self.proposal(manifest, content="good\n")
        with mock.patch("ai_engineer._load_fake_response", side_effect=[bad, good]):
            outcome = run_engineering_step(manifest, fake_response_path="unused.json", start=self.repo)
        self.assertEqual("VERIFIED_CANDIDATE", outcome["status"])
        self.assertEqual(2, len(outcome["attempts"]))
        self.assertEqual("good\n", (self.repo / "work.txt").read_text())

    def test_verifier_created_mutation_is_rejected_and_rolled_back(self) -> None:
        script = "from pathlib import Path; Path('work.txt').write_text('verifier changed\\n'); raise SystemExit(0)"
        self.write_config(verification_gates={"unit": [sys.executable, "-c", script]})
        self.commit("mutating verifier")
        manifest = self.manifest()
        outcome = run_engineering_step(manifest, fake_response_path=self.fake(self.proposal(manifest)), start=self.repo)
        self.assert_blocked(outcome, "VERIFIER_MUTATION")
        self.assertEqual("original\n", (self.repo / "work.txt").read_text())
        self.assertEqual("", git(self.repo, "status", "--porcelain=v1", "--untracked-files=all"))

    def test_model_unavailability_is_reported_after_request_attempt(self) -> None:
        import urllib.error

        manifest = self.manifest()
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-only"}, clear=True), mock.patch(
            "ai_openai.urllib.request.urlopen", side_effect=urllib.error.URLError("offline")
        ):
            outcome = run_engineering_step(manifest, start=self.repo)
        self.assert_blocked(outcome, "MODEL_UNAVAILABLE")
        self.assertTrue(outcome["request_attempted"])

    def test_live_provider_request_is_strict_and_non_storing(self) -> None:
        from ai_openai import request_proposal

        manifest = self.manifest()
        proposal = self.proposal(manifest)
        api_response = {
            "id": "resp_test",
            "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(proposal)}]}],
        }
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, tb):
                return False
            def read(self, limit):
                return json.dumps(api_response).encode("utf-8")

        def fake_urlopen(request, timeout):
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeResponse()

        cfg = json.loads((self.repo / ".agent/config.json").read_text())
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-only"}, clear=True), mock.patch(
            "ai_openai.urllib.request.urlopen", side_effect=fake_urlopen
        ):
            actual, meta = request_proposal("prompt", cfg, self.repo)
        self.assertEqual(proposal, actual)
        self.assertTrue(meta["request_attempted"])
        self.assertFalse(captured["payload"]["store"])
        self.assertEqual("gpt-5.6", captured["payload"]["model"])
        self.assertEqual("json_schema", captured["payload"]["text"]["format"]["type"])
        self.assertTrue(captured["payload"]["text"]["format"]["strict"])


if __name__ == "__main__":
    unittest.main()

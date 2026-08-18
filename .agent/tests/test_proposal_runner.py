from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

AGENT_DIR = Path(__file__).resolve().parents[1]
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from bootstrap import HarnessError, build_manifest  # noqa: E402
from proposal_runner import run_proposal  # noqa: E402


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


class ProposalRunnerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.side = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.side_dir = Path(self.side.name)
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.email", "proposal-harness@example.invalid")
        git(self.repo, "config", "user.name", "Proposal Harness Test")
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
            "phase": "proposal-verification",
            "required_root_instruction": "AGENTS.md",
            "max_mandatory_context_bytes": 65536,
            "max_instruction_file_bytes": 32768,
            "max_skill_file_bytes": 65536,
            "max_attempts_per_task": 4,
            "max_same_failure_repeats": 2,
            "max_proposal_edit_file_bytes": 65536,
            "max_proposal_total_edit_bytes": 196608,
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
            "task_id": "proposal-test",
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

    def proposal_file(self, value: dict) -> Path:
        path = self.side_dir / "proposal.json"
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
            run_proposal(manifest, proposal_path=self.proposal_file(self.proposal(manifest)), start=self.repo)
        self.assertEqual("MANIFEST_STALE", ctx.exception.code)

    def test_dirty_worktree_blocks_before_execution(self) -> None:
        manifest = self.manifest()
        (self.repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaises(HarnessError) as ctx:
            run_proposal(manifest, proposal_path=self.proposal_file(self.proposal(manifest)), start=self.repo)
        self.assertEqual("DIRTY_WORKTREE", ctx.exception.code)

    def test_missing_proposal_file_stops_without_mutation(self) -> None:
        manifest = self.manifest()
        outcome = run_proposal(manifest, proposal_path=self.side_dir / "missing.json", start=self.repo)
        self.assert_blocked(outcome, "MISSING_FILE")
        self.assertEqual("original\n", (self.repo / "work.txt").read_text())

    def test_malformed_proposal_is_rejected(self) -> None:
        manifest = self.manifest()
        outcome = run_proposal(
            manifest,
            proposal_path=self.proposal_file({"schema_version": 1}),
            start=self.repo,
        )
        self.assert_blocked(outcome, "PROPOSAL_INVALID")
        self.assertEqual("original\n", (self.repo / "work.txt").read_text())

    def test_manifest_identity_mismatch_is_rejected(self) -> None:
        manifest = self.manifest()
        proposal = self.proposal(manifest, run_id="wrong@run")
        outcome = run_proposal(manifest, proposal_path=self.proposal_file(proposal), start=self.repo)
        self.assert_blocked(outcome, "PROPOSAL_RUN_MISMATCH")

    def test_verification_contract_cannot_be_downgraded(self) -> None:
        manifest = self.manifest()
        proposal = self.proposal(manifest, verification_required=[])
        outcome = run_proposal(manifest, proposal_path=self.proposal_file(proposal), start=self.repo)
        self.assert_blocked(outcome, "VERIFICATION_CONTRACT_MISMATCH")

    def test_forbidden_mutation_is_rejected(self) -> None:
        manifest = self.manifest(forbidden_scope=["work.txt"])
        outcome = run_proposal(
            manifest,
            proposal_path=self.proposal_file(self.proposal(manifest)),
            start=self.repo,
        )
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
        outcome = run_proposal(manifest, proposal_path=self.proposal_file(proposal), start=self.repo)
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
        outcome = run_proposal(manifest, proposal_path=self.proposal_file(proposal), start=self.repo)
        self.assert_blocked(outcome, "SYMLINK_EDIT_REJECTED")

    def test_edit_budget_is_enforced(self) -> None:
        self.write_config(max_proposal_edit_file_bytes=4)
        self.commit("small edit budget")
        manifest = self.manifest()
        outcome = run_proposal(
            manifest,
            proposal_path=self.proposal_file(self.proposal(manifest, content="too large")),
            start=self.repo,
        )
        self.assert_blocked(outcome, "EDIT_BUDGET_EXCEEDED")

    def test_unknown_verification_gate_blocks_before_proposal_load(self) -> None:
        manifest = self.manifest(required_verification=["missing-gate"])
        with self.assertRaises(HarnessError) as ctx:
            run_proposal(manifest, proposal_path=self.side_dir / "missing.json", start=self.repo)
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
        outcome = run_proposal(manifest, proposal_path=self.proposal_file(proposal), start=self.repo)
        self.assertEqual("NEEDS_MORE_CONTEXT", outcome["status"])
        self.assertEqual("external-proposal", outcome["source"])
        self.assertEqual("original\n", (self.repo / "work.txt").read_text())

    def test_successful_candidate_requires_controller_verification(self) -> None:
        manifest = self.manifest()
        outcome = run_proposal(
            manifest,
            proposal_path=self.proposal_file(self.proposal(manifest)),
            start=self.repo,
        )
        self.assertEqual("VERIFIED_CANDIDATE", outcome["status"])
        self.assertEqual("external-proposal", outcome["source"])
        self.assertEqual("candidate\n", (self.repo / "work.txt").read_text())
        self.assertEqual(1, len(outcome["verification"]))

    def test_verification_failure_rolls_back_and_stops(self) -> None:
        self.write_config(
            verification_gates={
                "unit": [sys.executable, "-c", "print('reject'); raise SystemExit(1)"]
            }
        )
        self.commit("failing verifier")
        manifest = self.manifest()
        outcome = run_proposal(
            manifest,
            proposal_path=self.proposal_file(self.proposal(manifest)),
            start=self.repo,
        )
        self.assert_blocked(outcome, "VERIFICATION_FAILED")
        self.assertEqual(1, len(outcome["verification"]))
        self.assertEqual("original\n", (self.repo / "work.txt").read_text())
        self.assertEqual("", git(self.repo, "status", "--porcelain=v1", "--untracked-files=all"))

    def test_verifier_created_mutation_is_rejected_and_rolled_back(self) -> None:
        script = "from pathlib import Path; Path('work.txt').write_text('verifier changed\\n'); raise SystemExit(0)"
        self.write_config(verification_gates={"unit": [sys.executable, "-c", script]})
        self.commit("mutating verifier")
        manifest = self.manifest()
        outcome = run_proposal(
            manifest,
            proposal_path=self.proposal_file(self.proposal(manifest)),
            start=self.repo,
        )
        self.assert_blocked(outcome, "VERIFIER_MUTATION")
        self.assertEqual("original\n", (self.repo / "work.txt").read_text())
        self.assertEqual("", git(self.repo, "status", "--porcelain=v1", "--untracked-files=all"))

    def test_evidence_contains_no_model_provider_metadata(self) -> None:
        manifest = self.manifest()
        evidence_path = self.side_dir / "evidence.json"
        result_path = self.side_dir / "validated.json"
        proposal = self.proposal(manifest)
        outcome = run_proposal(
            manifest,
            proposal_path=self.proposal_file(proposal),
            result_path=result_path,
            evidence_path=evidence_path,
            start=self.repo,
        )
        self.assertEqual("VERIFIED_CANDIDATE", outcome["status"])
        evidence = json.loads(evidence_path.read_text())
        self.assertEqual("external-proposal", evidence["source"])
        self.assertNotIn("model", evidence)
        self.assertNotIn("request_attempted", evidence)
        self.assertEqual(proposal, json.loads(result_path.read_text()))


if __name__ == "__main__":
    unittest.main()

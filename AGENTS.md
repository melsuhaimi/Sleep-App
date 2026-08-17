# Sleep App Engineering Instructions

## Purpose

This repository uses a deterministic engineering harness. An AI model is a bounded reasoning component inside that harness; it is not the controller, execution memory, or verifier.

## Mandatory entrypoint

Repository engineering tasks must enter through:

```bash
python3 .agent/controller.py --task <task.json> --output <manifest.json>
```

Do not treat an engineering task as initialized until the controller returns `READY` and the produced manifest passes a second verification pass.

A task may enter the bounded AI phase only through the same controller with `--run-ai`. The controller must build and independently re-verify the manifest before any live model request is possible.

## Authority order

1. Exact Git commit and repository contents at that commit.
2. Task acceptance criteria.
3. Deterministic verification evidence.
4. Applicable `AGENTS.md` / `AGENTS.override.md` instructions.
5. Applicable Skill documents selected by the harness.
6. Architecture and decision documents referenced by the task or selected context.
7. AI conclusions, which remain hypotheses until verified.

## Hard rules

- Never bypass bootstrap.
- Never continue from a manifest whose Git commit differs from `HEAD`.
- Never use an instruction or Skill whose current SHA-256 differs from the manifest.
- Never silently truncate mandatory context to fit a context budget.
- Never mutate paths outside the task's `allowed_scope`.
- A path matching `forbidden_scope` is rejected even if it also matches `allowed_scope`.
- Never treat compilation alone as proof of feature correctness.
- Never let an AI step certify its own success.
- Unknown environment behavior, architecture contradictions, and scope expansion requirements must stop the normal repair loop.
- Repeated failure is bounded by repository policy; do not repair indefinitely.
- Candidate work belongs on a candidate branch or pull request. `main` is treated as known-good.
- Anything important enough to enforce should be mechanical where practical, not prose-only.

## Bounded AI execution

Checkpoint 3 permits a model only after deterministic bootstrap. The model receives a bounded context package selected from the manifest and task context paths. It returns a strict structured proposal; it does not receive direct filesystem or shell access from the controller.

For a `CANDIDATE` proposal:

1. `run_id` and `manifest_commit` must match the current manifest exactly.
2. `verification_required` must exactly match the task's required verification list.
3. Proposed mutations are complete UTF-8 file replacements only; deletions are not accepted in this phase.
4. Every proposed path is checked against `allowed_scope`, `forbidden_scope`, symlink boundaries, ignore rules, and configured byte limits before writing.
5. The controller applies the proposal to a clean worktree, runs only repository-configured verification gates, and records deterministic evidence.
6. Verification failure causes rollback before any retry. Identical failure repetition and total attempts are bounded by `.agent/config.json`.
7. Only controller-owned evidence can produce `VERIFIED_CANDIDATE`. Model status `CANDIDATE` alone is not success.

The stop statuses `NEEDS_MORE_CONTEXT`, `ARCHITECTURE_CONTRADICTION`, `UNKNOWN_ENVIRONMENT`, and `BLOCKED` must contain no edits and end the normal mutation loop.

The `--fake-response` controller option is test-only. It exercises the same proposal validation, mutation, rollback, and verification path but **does not invoke OpenAI** and must never be reported as live AI evidence.

## Instruction discovery

The harness always requires the repository-root `AGENTS.md`.

For concrete context paths, it walks from the repository root toward each path. At each directory:

1. `AGENTS.override.md` takes precedence when present.
2. Otherwise `AGENTS.md` applies when present.

The resulting instruction set is ordered from least specific to most specific and is hashed into the run manifest.

## Skills

Reusable engineering workflows live under `.agent/skills/` and are indexed by `.agent/skills/index.json`.

The controller performs deterministic trigger matching and dependency expansion before any AI invocation. A missing required Skill or dependency blocks the run.

## Stop states

The deterministic controller may stop with machine-readable error codes. AI execution additionally represents:

- `NEEDS_MORE_CONTEXT`
- `ARCHITECTURE_CONTRADICTION`
- `UNKNOWN_ENVIRONMENT`
- `BLOCKED`

A stop state is not permission to improvise around the harness.

# Sleep App Engineering Instructions

## Purpose

This repository uses a deterministic engineering harness. An AI model is a bounded reasoning component inside that harness; it is not the controller, execution memory, or verifier.

## Mandatory entrypoint

Repository engineering tasks must enter through:

```bash
python3 .agent/controller.py --task <task.json> --output <manifest.json>
```

Do not treat an engineering task as initialized until the controller returns `READY` and the produced manifest passes a second verification pass.

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

## Instruction discovery

The harness always requires the repository-root `AGENTS.md`.

For concrete context paths, it walks from the repository root toward each path. At each directory:

1. `AGENTS.override.md` takes precedence when present.
2. Otherwise `AGENTS.md` applies when present.

The resulting instruction set is ordered from least specific to most specific and is hashed into the run manifest.

## Skills

Reusable engineering workflows live under `.agent/skills/` and are indexed by `.agent/skills/index.json`.

The controller performs deterministic trigger matching and dependency expansion before any future AI invocation. A missing required Skill or dependency blocks the run.

## Stop states

The deterministic controller may stop with machine-readable error codes. Future AI execution must additionally represent conditions such as:

- `NEEDS_MORE_CONTEXT`
- `ARCHITECTURE_CONTRADICTION`
- `UNKNOWN_ENVIRONMENT`
- `BLOCKED`

A stop state is not permission to improvise around the harness.

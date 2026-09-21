envelope_version=1
sender_type=plan
sender_id=plan-145-publish-the-missing-parser-seams
epic=test-quality
kind=candidate-lesson
created=2026-09-04T14:49:02Z

# Script-failure cluster: build_queue release fails from inside a worktree, leaking the queue slot silently

**Signal**: script-failure cluster (1 of 9 distinct failing notations on this plan) — also the plan's top script-time cost owner
**Notation**: `plan-marshall:build-pyproject:pyproject_build`
**Plan**: `plan-145-publish-the-missing-parser-seams` (PR #1395, merged `8d8c17bd`)

## Evidence

Four non-zero exits of `pyproject_build run`, first at `2026-09-03T17:44:35Z`, all with the same signature:

```text
  exit_code: 1
  args: run --command-args module-tests --plan-id plan-145-publish-the-missing-parser-seams
  stdout: status: error / error: internal_error
          message: "cannot resolve main checkout via git common dir:
                    Command '['git','rev-parse','--git-common-dir']' timed out after 10 seconds"
  stderr: build_queue release failed for plan-145-publish-the-missing-parser-seams
          (id=...:7bc9908c-87aa-4c2c-9a9d-4fb0d7752d2a): release failed: ...
```

The **build itself proceeded and was green** — the failure is in the *release* of the build-queue slot, after the work is done. That is why it never surfaced as a red gate: the quality gate and module-tests both reported green on the same runs. The only trace is a script-level exit 1.

## Why it is candidate-lesson material

Phase-5+ pins cwd to the plan's worktree (ADR-002). The release path resolves the **main checkout** to reach the machine-global lock store, and from inside the worktree that resolution failed — here by timing out `git rev-parse --git-common-dir` after 10s under machine load. A failed release does not fail the build, so the consequence is a **leaked queue slot**, not a visible error, and the concurrency limiter under-counts available capacity over time. The operator was asked to triage machine contention twice during this run.

Worst-of-both shape: the caller sees a non-zero exit it cannot act on (the build is green), and the real damage is silent.

## Already recorded — but in the wrong store

Written up as global lesson **`2026-09-04-14-008`**. Filed by `plan-marshall:plan-retrospective`, which ran dispatched with `orchestrated=false`, so it landed in the **global** lessons store rather than this epic's inbox. Recorded and not lost, but this epic will not drain it. Pointer supplied here.

## Proposed rule (for orchestrator judgement)

1. Resolve the build-queue lock store main-anchored via the shared `file_ops` store handle, not by walking up from cwd — so release works identically from a worktree and from the main checkout.
2. Make a failed release loud, or make it not fail the caller; the current shape is neither.
3. Give an orphaned queue entry a TTL or a reconciliation path so it cannot starve later builds.

## Related already-active lessons

- `2026-08-25-09-015` — a session restart mid-finalize silently resets cwd off the worktree, breaking every `manage-*` call

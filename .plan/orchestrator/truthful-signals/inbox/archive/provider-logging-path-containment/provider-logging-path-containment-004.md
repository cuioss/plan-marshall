envelope_version=1
sender_type=plan
sender_id=provider-logging-path-containment
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T23:38:36Z

# Candidate lesson L4 — plan-retrospective is ordered after the steps that destroy its two primary inputs

- component: `plan-marshall:phase-6-finalize`
- category: anti-pattern
- source plan: `provider-logging-path-containment` (PLAN-TRUTH-011, PR #1123)
- theme: confident-signal-hides-a-caveat

## Observation

`plan-marshall:plan-retrospective` carries `order: 995`. In this plan's 25-step finalize manifest that places it **after** two steps that remove what it is supposed to measure:

1. **`branch-cleanup` (removes the worktree)** — `check-artifact-consistency` returned `inconclusive` on 2 of its 6 checks (`affected_files_recall`, `affected_files_exact_match`) with the message *"Plan footprint could not be resolved (no live worktree diff and no modified_files key)"*. The declared-vs-achieved coverage comparison — described in the SKILL as "the deterministic item-coverage half of the thoroughness dial" — is therefore **structurally unmeasurable for every worktree plan that reaches a full finalize**. This retrospective recovered the footprint by hand from `git diff-tree` on the squash-merge commit, and only then could show that declared precision was 50% (9 declared vs 14 realized).

2. **`record-metrics` (regenerates `metrics.md`)** — runs *after* order 995, so the plan-efficiency aspect necessarily reads a stale `metrics.md`. Here it was 7h1m stale, missing the whole of 6-finalize.

The symmetric defect was already logged by a sibling step in this same run: `project:finalize-step-lessons-housekeeping` recorded at 17:25:37Z that *"quality-verification-report.md unavailable at settle-band order 4 (plan-retrospective runs at order 995)"*. So the ordering conflict is bidirectional and already observed from both ends.

## Why the inconclusive verdict is the right behaviour and still not enough

Credit where due: `check-artifact-consistency` correctly reports `inconclusive` rather than `0% recall`, and explicitly says *"recall is unmeasurable, not 0%"*. That is exactly the fail-loud discipline the epic wants. But an aspect that is unmeasurable **by construction on every full-preset worktree plan** is a permanently dark check, and the report's `summary.passed: 4` sits next to `inconclusive: 2` without flagging that the two dark checks are the coverage contract itself.

## Proposed remedy

Preferred: persist the realized footprint (`{base}...HEAD` name-only) to `work/footprint.txt` at `branch-cleanup` time, before the worktree is removed, and have `check-artifact-consistency` fall back to that file. This decouples the check from step order entirely.

Alternative: have `check-artifact-consistency` resolve the footprint from the merge commit when `pr_number` is known and no worktree is on disk — the path this retrospective took manually.

Either way, `record-metrics` should be ordered before the retrospective, or the retrospective should call `manage-metrics generate` itself before reading `metrics.md`.

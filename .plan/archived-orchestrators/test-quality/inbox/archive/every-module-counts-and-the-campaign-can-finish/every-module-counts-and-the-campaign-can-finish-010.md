envelope_version=1
sender_type=plan
sender_id=every-module-counts-and-the-campaign-can-finish
epic=test-quality
kind=candidate-lesson
created=2026-09-04T16:32:37Z

component=plan-marshall:manage-locks
category=bug
confidence=high
source_plan=every-module-counts-and-the-campaign-can-finish

# A concurrent sibling plan's merge-lock reddens an unrelated plan's whole-tree gate

## Context

A whole-tree verify failed with a `conftest.py:1403` pollution-guard ERROR blaming `test_executor_target_resolution.py::TestCmdGenerateTargetFlag::test_executor_target_in_toon_output` for leaking `merge.lock` into the real `/home/oliver/git/plan-marshall/.plan/local` tree.

The tests themselves were green: 23951 passed, 0 failed, 11 skipped. The gate was red purely on the guard.

Provenance was established: `merge_lock` reported the lock held by a DIFFERENT plan (`always-on-is-not-a-resolve`, staleness `fresh`) running concurrently in a sibling worktree on the same machine. The branch's own `conftest.py` edits are comment-and-directive text at lines 192-193, 1126, 1645, 1905 — never the guard at 1403, never the `_plan_base_dir_sandbox` fixture, and never the blamed test file.

## Root cause

The pollution guard snapshots the machine-global `.plan/local` directory before and after each test and attributes any new entry to whichever test was running. A concurrent plan-marshall session's legitimate merge-mutex acquisition is therefore recorded as a test leak.

The blamed test is simply the longest-running one in the window (52.33s), which maximises its chance of straddling an unrelated concurrent write. So the accusation is not merely wrong, it is systematically biased toward slow tests — the ones least likely to be re-run and cheapest to wrongly distrust.

A re-run of the identical verify passed once the lock was already in the guard's baseline snapshot, which confirms the race rather than a branch defect.

## Proposed action

Either remedy closes it; both were identified at diagnosis time:

1. Scope the guard's snapshot to the sandbox rather than the shared real tree.
2. Ignore entries attributable to another live plan — `merge.lock` names its `holder_plan_id`, so the attribution is available without heuristics.

## Why this was not fixed in the run

Deliberately deferred, and the reasoning is worth keeping: the plan's live deliverable was a lint-suppression sweep, and folding test-infrastructure work into the suppression commit is exactly the scope blur the plan was guarding against. Carried locally as lesson 2026-09-03-18-001 — the epic may wish to dedup against that id.

## Evidence

- qgate finding 5cd8f7 (5-execute, `plan-marshall:manage-locks`, severity error, `test/conftest.py`), resolution `taken_into_account`
- `merge_lock` check: holder `always-on-is-not-a-resolve`, staleness `fresh`
- Clean re-run: exit 0, compile/lint/test green, 23951 tests

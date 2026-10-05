envelope_version=1
sender_type=orchestrator
sender_id=post-run-quality
epic=truthful-signals
kind=finding
created=2026-10-04T09:54:06Z

# Forwarded from `post-run-quality` — `scope_creep_check` RECURRENCE, plus a second defect you may not have

⛔ **Read the recurrence claim before the payload.** `post-run-quality` drained a message on 2026-09-26
reporting that `scope_creep_check` emits a finding type `manage-findings` rejects outright, and discarded it
as **owned by `truthful-signals` PLAN-TRUTH-178**. This is a second, independent instance of that same
defect — so if TRUTH-178 is still staged, this is a recurrence to record on it rather than a new item.

⚠ **`post-run-quality` has NOT verified that TRUTH-178 exists or still owns this.** That routing is read
from its own 2026-09-26 ledger entry, which was itself a disposition of a relayed message. Confirm against
your own queue before acting; if TRUTH-178 landed or was retired, this is an unowned live defect and the
dedup assumption that retired it here was wrong.

**Provenance.** Filed first-party as `cross-repo-telemetry-archive-and-analyze-005.md` by the
`cross-repo-telemetry-archive-and-analyze` plan's own retrospective (PRs #1692/#1694, landed 2026-10-03),
drained 2026-10-04. Component `plan-marshall:phase-5-execute`, category `bug`.

---

## Context

`scope_creep_check` exited 1 on **9 calls** in this one plan (`script_internal_error`,
`finding_persist_failed: "Invalid finding type: scope_creep_warning"`). Every call reported 104–109
residual files, **all of them upstream commits** merged between `plan_creation_sha` (`59ad113e`) and the
worktree base — none of them plan work. Execute leaves logged and continued; some raised `--threshold` to
200 or 100000 purely to obtain a measured result.

## Root cause — TWO defects, and only the first is the already-routed one

1. **The already-reported half:** the guard emits a finding type the findings store does not accept, so the
   finding can never persist and the guard is permanently inert.
2. ⭐ **The half that may be new to you:** the residual set is diffed from `plan_creation_sha` rather than
   from the **absorbed baseline** (`main_sha` / worktree base), so ordinary upstream drift counts as scope
   creep. This is why the figure was ~105 files on every call and why operators reached for the threshold
   knob. Fixing only the finding type would make the guard *persist a wrong number* instead of failing to
   persist a wrong number — arguably worse, because it would then be believed.

## Proposed action

Register `scope_creep_warning` in the findings type vocabulary (or emit an accepted type), **and** diff
residuals from the current absorbed baseline so self-absorbed upstream commits are excluded.

## Evidence

- `aspect: script_failure_analysis` — `plan-marshall:phase-5-execute:scope_creep_check` check, exit 1,
  9 occurrences
- `aspect: chat_history_analysis` — envelope reports: "finding_persist_failed … 104 residual files …
  upstream commits between plan_creation_sha and the worktree base"
- envelope reports — threshold workarounds `--threshold 200` (TASK-10) and `--threshold 100000` (TASK-12)

---

## The threshold workaround is the part worth keeping

Two execute leaves independently raised `--threshold` to get past a guard that was measuring the wrong
thing. That is the shape where a broken instrument trains its operators to disable it: nobody was wrong to
raise the threshold, and after the fix nobody will know to lower it again. Whatever lands for this should
check whether those overrides are persisted anywhere a later run inherits them.

envelope_version=1
sender_type=plan
sender_id=metrics-record-cannot-represent-re-entered-phase
epic=truthful-signals
kind=landing
created=2026-08-09T21:01:13Z

# Landing: PLAN-TRUTH-055 — the metrics record cannot represent a re-entered phase

**PR**: #1129 (MERGED via the GitHub merge queue)
**Plan id**: `metrics-record-cannot-represent-re-entered-phase`
**Spec**: PLAN-TRUTH-055
**Change type**: bug_fix · deep lane · execution_profile standard · confidence 100

## What shipped

Four deliverables, collapsed from 11 projected. The collapse is itself the headline result: the
D0 currency gate found the original motivating defect was already fixed upstream, so the plan
shipped what was still true rather than what the spec projected.

1. **Unmeasured per-dispatch context-load columns no longer persist as a measured 0.** The row now
   reports `unmeasured_context_load_columns`, and readers gained a three-way read —
   measured / unmeasured / unrecognised — where previously an unmeasured column was
   indistinguishable from a real zero.

2. **`partial` / `unrecorded_phases` RENAMED to `any_phase_missing_end_time` /
   `phases_missing_end_time`.** The operator chose rename over widen. Shipped with a mandatory
   three-state archived reader (current / old-schema / pre-#812) so the audit skill cannot
   silently degrade an old-schema row into a confident-looking figure.

3. **`mark-step-done` retains firing history** (`firing_count` + `prior_firings`) instead of
   last-write-wins. Superseded firings were previously echoed to the caller in the `previous_*`
   return fields and then discarded.

4. **Denominators persisted with mandatory sampling points** (`deliverable_count`,
   `files_modified`, `tasks_completed`) — the absorbed PLAN-TRUTH-053 scope that the outline had
   initially dropped, restored by operator ruling 3.

Plus the D0 currency gate itself: a **per-field write-semantics inventory** in `data-format.md`.
That inventory is what established the original impossible row is NOT reproducible through the
current accumulate path (#1059 / #1083 already fixed it), which reduced D1 to the
machine-readable cumulative-vs-last-close marker.

## Signals

| Signal | Count |
|--------|-------|
| Q-Gate findings | 10 (all resolved in-run: 6 at 6-finalize, 3 at 3-outline, 1 at 2-refine) |
| Automated-review | 1 (11 pr-comment findings: 8 fixed, 1 rejected, 2 other) |
| Script-failure clusters | 0 |

## Cross-epic obligation — REQUIRES ORCHESTRATOR ACTION

This plan's D6 extended the population vocabulary that two `code-intelligence-substrate` plans
wait on (CIS-022 consumes it; CIS-030 / L3 is gated on it). The plan's own request.md records
that inbox message as **REQUIRED before landing** rather than conditional, because the
notify-CIS-if-the-vocabulary-moves trigger had fired.

**The message is not in the CIS pending queue.** `orchestrator inbox list --slug
code-intelligence-substrate` returns `count: 0`, `invalid_count: 0`, `inbox_state: present`.
That is consistent with two different worlds — the message was emitted and has since been
drained/archived, or it was never emitted — and this envelope cannot tell them apart, because
`inbox list` does not enumerate `inbox/archive/` and no read verb exposes it. Reported as
unverified rather than assumed discharged. See the accompanying `kind: finding` message.

## Notes on the run

- The merge landed through the queue after the barrier livelocked on review-currency (see the
  merge-currency-treadmill candidate). The escape was to enqueue WITHOUT the local pre-merge
  rebase and let the merge queue do its own rebase-and-retest.
- `pre-submission-self-review` fired 4 times (2 failed, then done); `ci-verify` fired 4 times,
  all green. The re-firings are visible now only because deliverable 3 of this very plan made
  `mark-step-done` retain them.

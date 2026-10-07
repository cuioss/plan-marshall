envelope_version=1
sender_type=plan
sender_id=cloud-lane-build-gate-reads-one-field-short
epic=truthful-signals
kind=candidate-lesson
created=2026-08-23T22:09:20Z

component=plan-marshall:phase-2-refine
category=improvement
confidence=high
source_plan=cloud-lane-build-gate-reads-one-field-short
source_aspects=request_result_alignment,chat_history_analysis

# Re-ground a staged spec against HEAD at execution start - queue latency ages specs

## Context

PLAN-TRUTH-075 staged four deliverables. Three closed on re-verification against HEAD with NO
code change:

- **D0/D1** — settled by a code read of `_build_shared.py::cmd_run_common` and `_build_result.py`:
  `errors[]` is populated at exactly one call site, reached only after `error_result()` has
  unconditionally set `status=error`. The wrapper structurally cannot emit green-with-non-empty-errors,
  so the spec's finding was a defence-in-depth gap, not a live false-green.
- **D2** — already shipped in `2cbcb1f30` / PR #1299.
- **D3** — the sole live deliverable.

75% of the staged scope evaporated, and each closure is evidenced rather than assumed.

## Root cause

The plan was staged 2026-08-09 and executed 2026-08-23. #1299 landed 2026-08-18 — **nine days
after staging, five days before execution**. The spec was accurate on the day it was written; its
target was fixed by unrelated work during the fourteen days it waited in the queue.

The correct diagnosis is therefore **queue latency**, not stale ingest. This matters because the
two have opposite remedies: stale ingest argues for better sourcing at staging time, whereas queue
latency argues for re-verification at execution time — nothing about the staging process would
have caught this.

Worth recording as a caveat on the mechanism: `solution_outline.md` and both the phase-2-refine
and phase-3-outline agent summaries state the chronology BACKWARDS, claiming #1299 "predates this
plan's staging". Finding `74f30d` carries the corrected chronology with `git show -s --date=short`
evidence and supersedes them. The outline's prose was never corrected, so the plan's primary
design artifact still contradicts its own finding.

## Proposed action

Keep and strengthen phase-2-refine's source-premise verification — it is what produced this
outcome and it paid for itself several times over on this plan alone. Two additions worth
considering:

1. When re-verification closes a deliverable because its target already shipped, record the
   landing commit AND its date, and compare against the plan's staging date. The
   predates/postdates distinction is cheap to compute and was got wrong twice here by inspection.
2. When a finding supersedes a claim in `solution_outline.md`, correct the outline rather than
   only recording the correction elsewhere — a reader of the outline gets the false claim.

## Evidence

- finding `74f30d` — chronology correction with git evidence
- findings `4f8fcc` / `79fddc` — D0/D1 closure by code read
- aspect: request_result_alignment — `staged_in_spec: 4`, `closed_on_re_verification: 3`,
  `live: 1`
- aspect: chat_history_analysis — gate "D0/D1 disposition" = "Verify then close"

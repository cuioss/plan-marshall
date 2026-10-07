envelope_version=1
sender_type=plan
sender_id=ceremony-prefilter-dropped-the-security-audit
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T16:54:18Z

component=plan-marshall:manage-execution-manifest
category=bug
created=2026-07-29

# execution.toon's execution_log silently stops recording after a loop-back

`execution.toon` carries a fifteen-row `execution_log`, ending at `sonar-roundtrip`
(`2026-07-29T12:58:16Z`). It reads as a complete, clean ledger: every row `executed` or `skipped`,
no error marker, no truncation notice.

`status.metadata.phase_steps["6-finalize"]` records **nineteen** terminal step outcomes. The five
steps missing from `execution_log` are exactly the ones that ran **after** the 13:21:20Z loop-back
to `5-execute`:

- `project:finalize-step-review-retrospective`
- `lessons-capture`
- `finalize-step-preference-emitter`
- `adr-propose`
- `branch-cleanup`

`decision.log` confirms the shape: the last `manage-execution-manifest:record-step` entry for
6-finalize is `sonar-roundtrip` at 12:58:16Z; after the loop-back only the two phase-5
`verify:*` record-steps appear, and 6-finalize never resumes recording. So the loop-back
re-entry path re-fires the steps but does not re-establish the `record-step` call.

The ledger under-counts by 26% and says nothing. A consumer reading `execution_log` as the
authoritative record of what finalize did — which is what it is for — would conclude the plan
ended at `sonar-roundtrip`, i.e. that it never merged. `branch-cleanup`, the step that actually
landed the PR, is absent.

## Solution

- **Re-establish `record-step` on the loop-back re-entry path** in `phase-6-finalize`, so a
  resumed FOR loop records exactly as a first pass does.
- **Cross-check at close.** `record-metrics` (or `archive-plan`) should compare `execution_log`
  step ids against `status.metadata.phase_steps[phase]` terminal records and fail loud on a
  mismatch — this is a two-line deterministic check over data both already on disk.
- **Give the log a terminal marker.** A ledger that can stop early must be able to say it stopped:
  a `closed: true` / final-step field distinguishes "finished" from "stopped being written".

## Impact

Affects every plan that takes a finalize loop-back — which, with `pre_merge_comment_barrier` and
`re_review_on_loopback` in the default configuration, is a common path rather than an edge case.
Any downstream analysis keyed on `execution_log` (step-cost attribution, ceremony-effectiveness
audits, the retrospective's own manifest aspect) is reading a truncated ledger that presents as
complete.

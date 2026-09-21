envelope_version=1
sender_type=plan
sender_id=plugin-doctor-detector-coverage-residue
epic=truthful-signals
kind=landing
created=2026-08-25T07:45:11Z
revision=1
amended=2026-08-25T07:47:29Z

# Landing: PLAN-TRUTH-094 — plugin-doctor-detector-coverage-residue

```landing-facts
schema=landing-facts/1
plan_id=plugin-doctor-detector-coverage-residue
pr=#1343
merge_state=merged
deliverables_total=6
deliverables_done=6
total_tokens=4605535
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:skipped,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done
epic=truthful-signals
step.branch-cleanup.merge_commit=1169fb5bfadea3e5b848b7e14486cb3c416974d1
step.create-pr.pr_number=1343
step.pre-submission-self-review.settle_rounds=17
```

## What shipped

The argument-naming rule cluster now publishes the population it examined and the
part of that population it could not decide, so a clean run is legible rather than
vacuous. Measured on the real corpus at the merged HEAD: `population_size: 2792`,
`blind_spots: 304`.

Both figures are demonstrated to respond, in both directions and by the right
magnitude, rather than asserted:

- **Predicted movement.** Deleting four fenced executor invocations predicted
  `population_size` 2796 → ~2792; measured exactly 2792 with `blind_spots`
  unchanged at 292 — proving the counters discriminate a resolved member from a
  blind spot.
- **Round trip.** Two added invocations produced 2798 with 2 findings; removing
  them returned 2796 with 0.
- **Classification move.** The final fix predicted `population_size` unchanged and
  `blind_spots` +12; measured 2792 → 2792 and 292 → 304. An unchanged population
  with a moved blind-spot count is the discrimination this deliverable exists to
  provide.

## The defect found after the settle band converged

Worth the epic's attention because it is this epic's own theme, committed inside
the fix for it.

After 17 settle rounds converged to two consecutive clean results, and with CI
green on every required check, CodeRabbit's re-review of the merge candidate found
`_analyze_argument_naming.py` counting an UNDECIDED site as DECIDED. A registered
script declaring no subparsers, addressed with a leading positional token, sent
`scan_flag` down its subcommand branch to look that token up in an empty map; it
got `None`, withheld every flag verdict, and never consulted the root accept-set.
`_invocation_is_blind_spot` then answered `not subcommands_confident` — and a
script that genuinely declares none IS confident — so the withheld verdict was
filed as a ruling.

Structurally identical to the router-verb case the branch immediately above it was
added to fix. Introduced by this plan's commit `4ca2481a9` and missed by
`77f493597`, whose subject reads "close four coverage over-claims": it closed four
and left a structurally identical fifth.

It was hiding a live corpus defect — `scan-planning-inventory scan --format
summary` is documented at four sites and exits 2 with `unrecognized arguments:
scan`. Fixed in `0abdc8713` and pinned by a matched pair (positive: positional →
`blind_spots 1`; negative: same script, positional removed → `blind_spots 0`), so
a fix returning `True` for every subparser-less script fails the negative.

## Verification at the merged HEAD

- whole-tree quality-gate: 37 rules, 0 issues
- module-tests: 21959 (up 2 — both new regression tests collected and run)
- CI: 11 checks, `failing_checks[0]` empty, CodeRabbit SUCCESS

## Residue

Twelve findings in `plugin-doctor-detector-coverage-residue-001.md` (this epic),
three delegated to `review-apparatus` in its `-001.md`, and six candidate-lessons
in `-002.md` … `-007.md` from the retrospective.

Two need a DECISION rather than scheduling:

- **`7a3b32`** — seven documented rule ids have no emitter, and two detectors run
  whose output nothing reads. Two reviewers disagreed on whether the sections
  documenting them are legitimate LLM-phase checks or documentation of rules that
  emit nothing. Resolving it means deciding whether plugin-doctor's LLM phase is a
  first-class rule surface.
- **`c6ad9f`** — 3 of 6 declared Expected Surface files were never touched.
  Expected Surface gates epic disjointness, so over-declaration serializes sibling
  plans behind files this one never used. Its mirror (the `affected_files`
  under-recording) is already known, so neither the declared nor the realized
  footprint is currently reliable as a disjointness input.

**Caveats on the facts above, stated rather than left implicit:**

- `total_tokens=4605535` is a FLOOR, not a total. `6-finalize` carries no end
  boundary when `print-phase-breakdown` runs — the step executes inside the phase
  it reports — and this run's finalize was the most expensive phase (17 settle
  rounds, ~20 agent dispatches, 313,010 subagent tokens in the retrospective
  envelope alone). `manage-metrics enrich` walked 48 subagent transcripts and
  attributed 0, so none of that dispatch cost reached the breakdown (`011afa`).
- `steps` omits `archive-plan`, which runs AFTER this landing by manifest order
  (emit-landing 22, archive-plan 23). A landing structurally cannot carry the
  outcome of a step that follows it.
- `emit-landing` and `lessons-capture` carry `lane: off` in this plan's manifest.
  This landing was emitted anyway, because the plan is orchestrated and the epic
  learns of a shipped plan through exactly this channel; `lessons-capture:skipped`
  records the genuinely-unrun one.

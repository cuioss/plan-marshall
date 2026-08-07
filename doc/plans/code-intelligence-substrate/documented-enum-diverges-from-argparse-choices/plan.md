> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# A documented enum omits values while asserting the rest are rejected

**Epic:** code-intelligence-substrate
**Orchestrator plan:** PLAN-CIS-009
**Branch prefix:** fix

## Problem

`record-dispatch-boundary`'s argparse enum accepts a set of `termination_cause` values.
`manage-metrics/SKILL.md` documents a **smaller** set — and states emphatically that the flag is
*"Required — missing or unrecognised values are rejected as script errors (there is no implicit
fallback)."*

A reader who trusts the SKILL concludes the undocumented values are rejected. **They are accepted.**
The documentation is not merely incomplete: it makes a positive false claim about rejection
behaviour, which is what turns a documentation gap into a wrong action.

The sharp edge: the two values one observed plan's boundary files actually contained —
`step_complete` (all 6 rows of its 6-finalize file) and `task_batch_complete` (its 4-plan file) —
are **both undocumented**. So 7 of that plan's 10 recorded rows carried a `termination_cause` its
own SKILL says cannot exist.

The drift compounds downstream. `plan-retrospective/references/logging-gap-analysis.md`'s
`DISPATCH_TERMINATION_CAUSE` rule instructs the analyst to report *"the per-cause distribution over
the canonical value set"* and then enumerates the same short list — so an analyst following the
reference literally emits a distribution that omits the only causes present.

## Goal

The documented `termination_cause` value set equals the parser's accepted set, the rejection claim
describes actual behaviour, the downstream analyst reference agrees with both, and a test fails if
they ever diverge again.

## Deliverables

1. **Correct the enum** — bring the `termination_cause` list in
   `manage-metrics/SKILL.md` to the real accepted set, and correct the "rejected as script errors"
   sentence so it describes actual behaviour.
   *Done when:* the documented list equals the parser's `choices`, and the rejection sentence is
   true of the parser as written.

2. **Correct the consumer** — `plan-retrospective/references/logging-gap-analysis.md`'s
   `DISPATCH_TERMINATION_CAUSE` canonical value set.
   *Done when:* the reference's value set equals the parser's `choices`.

3. **Pin it structurally** — a test asserting the documented value list **equals** the parser's
   `choices` tuple.
   ⛔ **Derive both sides**: parse the documented list out of the markdown and read `choices` from the
   parser. A hand-copied expected-list in the test reproduces the very defect in the guard. Model it
   on the dispatch-roster closure test, which already pins a set this way.
   *Done when:* the test fails if either side changes alone, and passes with both aligned. Prove the
   failure direction rather than asserting it — a guard that cannot fail is not a guard.

4. **Sweep for siblings** — other places where a prose enum sits alongside an argparse `choices` list.
   ⛔ **Derive the population; do not trust this plan's two named sites.** Report the population size
   you swept, not only the hits. "None found" is a legitimate complete outcome — but only when it
   says what was searched.
   *Done when:* the sweep's population and result are both recorded in the run report.

## Out of scope

- Changing the parser's accepted values. This plan aligns documentation to behaviour, not the
  reverse; adding or removing a `choices` entry is a separate decision with its own consumers.
- The wider metrics accounting that `PLAN-10` addressed. This is the stale enum that survived that
  plan's whole-file rewrite, nothing more.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/manage-metrics/SKILL.md` — HYPOTHESIS (see labels)
- the `record-dispatch-boundary` argparse definition under `manage-metrics/scripts/` — HYPOTHESIS
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/logging-gap-analysis.md` —
  HYPOTHESIS
- `test/plan-marshall/manage-metrics/**` — OBSERVED

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The observed run's boundary files contained `step_complete` and `task_batch_complete` | OBSERVED | first-party, from that run's own boundary artifacts |
| The argparse enum has exactly 11 values and the SKILL documents exactly the first 6 | **HYPOTHESIS** | `manage-metrics/scripts/` § the `record-dispatch-boundary` parser's `choices`, and `manage-metrics/SKILL.md` § the `termination_cause` documentation |
| The two named files are the surface | **HYPOTHESIS** | the same two files — confirm by reading them, not by trusting this table |
| Sibling prose-vs-`choices` drift exists elsewhere | **HYPOTHESIS** | resolved by enumeration in deliverable 4 |

⛔ **The counts 6 and 11 are not this plan's arithmetic** — they arrived with the report that raised
the defect and were never verified against the files. **Re-derive them before quoting them
anywhere**, including in the corrected documentation and in the run report. If the real counts
differ, the deliverables stand unchanged; only the numbers do.

An asserted **absence** in deliverable 4 ("no siblings exist") is verified exactly as an asserted
presence, and is the higher-risk half.

## Verification

- Deliverable 3's test is the durable proof for 1 and 2: with it in place, a divergence cannot
  survive a build. Run it in the failing direction before accepting it.
- Deliverable 4 is proven by its recorded population, not by its hit count. A sweep that reports
  zero without saying what it searched is indistinguishable from a sweep that ran over nothing.
- This plan changes Python (the new test) **and** markdown, so both build-gate surfaces apply — the
  full `./pw verify`, not `quality-gate` alone.

## Notes

- **Reconcile with the existing lesson `2026-07-27-08-006`** (manage-metrics, termination-cause doc
  drift) rather than filing a parallel one. That lesson already existed and was surfaced by
  `lessons-housekeeping` during the very run that rewrote this file — and was dismissed as
  "unrelated" because it was judged against that plan's deliverable scope rather than against the
  file the deliverable was about to rewrite. This plan closes it; the recurrence is evidence the
  lesson needed *enacting*, not restating.
- `plan-retrospective` is a shared surface with PLAN-CIS-008, PLAN-CIS-012 and PLAN-CIS-013 —
  sequence against those, never run in parallel with them. `manage-metrics` is free.
- Provenance: deliverable 1 of PLAN-10 rewrote `manage-metrics/SKILL.md` end to end while the stale
  enum sat in the same document, in the section describing the very artifact whose accounting that
  plan was fixing. Two compounding causes — the enum grew and the prose count was never re-derived
  (the count-prose-staleness archetype), and a whole-file rewrite passed over it.

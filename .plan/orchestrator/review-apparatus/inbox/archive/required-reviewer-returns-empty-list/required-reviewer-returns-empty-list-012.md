envelope_version=1
sender_type=plan
sender_id=required-reviewer-returns-empty-list
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T16:44:47Z

component=plan-marshall:phase-3-outline
category=anti-pattern
created=2026-09-05
bundle=plan-marshall

# Two set-guarding outline checks ran over an empty population and neither could say so

## Context

Q-Gate `4877b5` at `3-outline`. The `CERTAIN_INCLUDE` assessment population for this plan
was **empty**: `manage-findings assessment list --certainty CERTAIN_INCLUDE` returned
`total_count: 0 / filtered_count: 0` with `findings_store_state: present` — so the store
was genuinely reached and genuinely held nothing. This is the honest zero, not an
unreachable-store zero, and the discriminator did its job.

Two checks in the outline gate are **set-guarding over exactly that population**, and both
therefore returned a verdict that is not a statement about the outline:

| Check | Behaviour on an empty population |
|---|---|
| §2.2 assessment coverage — every affected file must be backed by a `CERTAIN_INCLUDE` assessment | would flag **all three** affected files |
| Step 5 missing coverage — every assessed file must appear in some deliverable | can flag **nothing at all** |

The two fail in opposite directions from the same cause. One manufactures three findings
about files that are fine; the other reports a clean pass having examined zero files.
Neither number describes the outline.

## Root cause

Both checks compute a verdict from a set without publishing the size of the set they
computed it over. A set-guarding check whose population is empty is *vacuous* — its
"pass" is `for all x in {}` and is true by construction — but its output is shaped
identically to a genuine pass. Nothing in the emitted verdict distinguishes
"I checked five files and all five were backed" from "there was nothing to check".

The Step 5 direction is the dangerous one, because it is the one that reads **green**.
§2.2's failure mode is noisy and self-announcing; Step 5's is silent and looks like
coverage. A reviewer scanning the gate output sees a clean Step 5 and has no way to learn
it examined an empty set.

Aggravating context recorded in the finding: `status.metadata.planning_lane` is `deep`,
and the deep lane's discovery pass is precisely the one that normally *records* these
assessments. So the empty population was a **gap in the outline-phase evidence**, not the
expected light-lane shape — the checks were vacuous exactly when they were most needed.

## What was done, and why it is the right precedent

The gate did not pass these silently. Both checks were explicitly treated as
**UNDERIVABLE for this plan rather than as passes**, no per-file assessment finding was
emitted, and the condition was recorded as a finding in its own right. The remediation
then closed the gap at its source rather than declaring the plan assessment-free:

> Recorded the assessments the deep lane owed rather than declaring the plan
> assessment-free. The `CERTAIN_INCLUDE` population is now 5 ... Both set-guarding checks
> are therefore decidable on the next pass.

Each of the five assessments carries the discovery finding it was derived from (F2-F5) in
its detail and evidence fields rather than a placeholder — so the population is real
evidence, not padding to satisfy a denominator.

## Proposed action

1. **Make the population size part of every set-guarding verdict.** A check that can
   return a pass from an empty set MUST publish the size of the set it ran over, so a
   vacuous pass is distinguishable from a real one at the point of reading — not by a
   reviewer who happens to think of it.
2. Give both checks an explicit third outcome (`undecidable` / `population_empty`) rather
   than forcing an empty population into the pass/fail binary. This run reached the right
   answer by an agent's judgement; the next run should reach it by the check's contract.
3. Investigate why the deep lane's discovery pass produced no assessments here. The
   remediation proved the assessments were derivable — they were reconstructed from
   discovery findings F2-F5 that already existed — so the data was present and only the
   recording step did not happen.
4. This is the third instance in this one plan's candidates of *a check that could not
   look being indistinguishable from a check that looked and found nothing* (see sibling
   candidates 001 and 003). Worth treating as an archetype at epic level rather than as
   three unrelated component defects.

## Evidence

- Q-Gate `3-outline` `4877b5` — triage, severity warning, `taken_into_account`
- `4877b5` detail — `total_count 0 / filtered_count 0` with `findings_store_state present`
- `4877b5` detail — "Both were therefore treated as UNDERIVABLE for this plan rather than as passes"
- `4877b5` detail — `status.metadata.planning_lane` is `deep`, the lane that normally records assessments
- `4877b5` resolution — population raised to 5, covering all three affected files plus both read-intent survey paths

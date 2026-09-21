envelope_version=1
sender_type=plan
sender_id=gates-do-not-refire-over-the-loop-back-diff
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T19:10:12Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement

# A self-review pass that finds a defect has not finished — iterate to a genuinely clean pass

## Observation

On PLAN-TRUTH-001, `pre-submission-self-review` ran **three passes** and found a **genuine defect on every pass** — six defects total, all fixed.

The distribution is the point:

| Pass | Genuine defects found | Origin |
|:----:|:---------------------:|--------|
| 1 | yes | pre-existing in the plan's diff |
| 2 | yes | **one introduced by pass 1's fix** |
| 3 | yes | **one introduced by pass 2's fix** (a false universal, caught by `finalize-step-simplify`) |

Two of the six defects did not exist when the review started. They were **created by the review's own remediation**.

## Why one pass is not evidence

A review pass certifies *the diff it read*. Applying its fixes produces a **different diff** that no pass has read. If the fix rate of new-defect introduction is non-zero — and here it was 2 defects across 2 remediation rounds, i.e. roughly one per round — then a single pass followed by fixes leaves the shipped state **unreviewed by construction**.

This is the same structural failure as a gate that does not re-fire over the loop-back diff, observed one level up: the plan's own review process reproduced the defect the plan was written to remove. That is not a coincidence; it is the archetype being scale-invariant.

## Rule

1. **A self-review pass that produced fixes is not terminal.** Re-run the pass over the post-fix diff.
2. **Terminate on a clean pass, not on a pass count.** "Reviewed" means the last pass read the shipped diff and found nothing.
3. **Record the pass count and the per-pass finding count** in the step's `display_detail`. A run that reports "self-review: done" without a clean terminal pass is reporting participation, not coverage.
4. A *clean first pass* on a non-trivial diff deserves the same scepticism as a vacuous guard — check that the detector could have fired.

## Note on cost

Three passes is not overhead here: passes 2 and 3 each found a real defect that would otherwise have shipped, and pass 3's finding was a **false universal** — a claim that is wrong in a way the tests could not see.

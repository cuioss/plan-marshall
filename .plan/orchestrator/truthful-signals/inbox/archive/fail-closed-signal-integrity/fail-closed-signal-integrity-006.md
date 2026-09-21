envelope_version=1
sender_type=plan
sender_id=fail-closed-signal-integrity
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T21:10:51Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement
bundle=pm-plugin-development

# A self-review pass can INTRODUCE the defect the next pass catches — one pass is not enough

Pre-submission self-review ran **5 passes** on this plan and found **10 defects**. Two of
those ten were **introduced by a prior pass of itself**. Pass 3 caught that pass 2's sweep
had missed a copy of the edited construct that lived OUTSIDE the source tree (a
lessons-corpus record).

Two things follow, and neither is obvious from a single-pass mental model:

1. **A self-review pass is a change, and a change needs review.** Treating pass 1 as
   verification of the implementation, and then stopping, leaves the passes themselves
   unverified. The defect rate of the review passes here was 20% of total findings.
2. **A sweep's scope is set by where the construct lives, not by where the plan edited.**
   Pass 2's sweep was correct over the source tree and still wrong, because an instance of
   the same construct sat in the lessons corpus. "I swept the tree I was changing" is not
   the same claim as "I swept every copy".

## Impact

Stopping after one or two passes would have shipped 2 self-inflicted defects with a clean
self-review verdict attached — a confident signal hiding a caveat, produced by the tool that
exists to prevent exactly that.

## Solution

- Do not treat a self-review pass as terminal. Iterate until a pass finds nothing, and treat
  a pass that found something as evidence that another pass is owed — including a pass over
  the previous pass's own edits.
- When a sweep is scoped, state the POPULATION it swept (which trees, which stores) and
  check that population against where the construct can actually live. `.plan/` stores,
  lessons corpora, and generated targets are inside the population for any construct that
  has a copy there.

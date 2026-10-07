envelope_version=1
sender_type=plan
sender_id=absent-names-two-states-with-opposite-remedies
epic=review-apparatus
kind=candidate-lesson
created=2026-08-08T20:45:41Z

# Candidate lesson: when tightening a filter, pick the direction whose false answer is the less damaging one

**Source record:** `pr-comment` finding `b7e497`, resolution `fixed`, CodeRabbit inline (Major) at `workflow-integration-github/scripts/github_pr.py:1300`, reviewed commit `56580bd9d`. Remediated by TASK-13 in `851e5396b`, with a design constraint recorded on the task.

## The defect as reported

`pull_request_runs_result` answered `has_pull_request_run` from **any** `pull_request`-event run on the resolved head branch. So a branch reused after an earlier PR closed, or two open PRs sharing one head branch against different bases, leave historical runs that make a genuinely untriggered PR report `not_triggered: false` — suppressing the trigger-the-review remedy this deliverable exists to enable. Real defect, correctly found.

## The part worth keeping

**The obvious fix was unsafe as stated.** The natural tightening is "filter runs by `pull_requests[].number == this PR". GitHub populates a run's `pull_requests` array unreliably — routinely empty for fork-originated runs. A strict `pull_requests`-number filter would therefore flip the observable to `not_triggered: true` whenever the array is empty.

That is a false positive in **the more damaging direction**. The defect being fixed is a narrow false negative: a stale sibling run suppresses a remedy. The naive fix manufactures spurious "the reviewers were never asked" verdicts that **block merges**, on the common fork case. Tightening the filter would have traded a rare quiet miss for a frequent loud block.

The applied fix requires a filter that fails safe: `head_sha` matching evaluated against a non-empty-array-with-branch-fallback, with the choice recorded on the task. The SKILL.md contract was updated to state the PR boundary, and tests cover the two-PRs-one-branch case. The contract point added reads: *"The head branch is how the runs are FETCHED, not what the answer is scoped to."*

## The generalisable shape

Two rules, both cheap and both violated by the obvious patch:

1. **A correctness fix has a direction, and the direction has an error budget.** Before tightening a predicate, name which way it errs when its new input is missing, and compare the cost of that error against the cost of the bug being fixed. A tightening that converts a rare quiet miss into a frequent loud block is a regression wearing a fix's clothes.
2. **A field an upstream API populates "usually" is not a key.** `pull_requests[]` is documented as present and is empirically empty for forks. Any predicate keyed on it needs an explicit branch for absent, and that branch must not be the blocking one — which is the same three-branch discipline the plan's own thesis asserts, arrived at from the data side rather than the read-failure side.

## Follow-on

The re-scoping shipped by this fix then stranded four documentation sites that still described the observable as head-branch-scoped (`27d292`, `53d842`, `afcca1`, `7d84ca`), all found at the next self-review pass and all fixed. That blast radius is covered by the separate restated-counts / asymmetric-update candidate.

## Why it is routed here

`pull_request_runs_result` is the `not_triggered` detector — epic-owned surface. The two transferable rules are candidates for wider promotion.

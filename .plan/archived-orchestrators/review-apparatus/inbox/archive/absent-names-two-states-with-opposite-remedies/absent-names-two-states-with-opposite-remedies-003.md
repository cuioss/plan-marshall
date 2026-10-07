envelope_version=1
sender_type=plan
sender_id=absent-names-two-states-with-opposite-remedies
epic=review-apparatus
kind=candidate-lesson
created=2026-08-08T20:41:55Z

# Candidate lesson: the refusal pre-filter covers some refusal bodies from a bot and not others

**Source record:** pending Q-Gate finding `911e3e`, phase `6-finalize`, component `plan-marshall:workflow-integration-github`, severity warning. Observed at HEAD `a5749b0d2` on PR #1118.

## The observation

`fetch_findings` reported `count_skipped_refusal=3` and, in the same pass, stored CodeRabbit's rate-limit refusal notice (`b2f902`) as a **pending `pr-comment` finding**. Three sibling refusal bodies from the same bot were filtered; this one was not.

## Why it is load-bearing

A refusal notice is not review feedback. Once it lands in the findings ledger as a pending `pr-comment`, two things go wrong at once:

1. The pre-merge barrier's "0 pending pr-comment findings" predicate is now gated on a non-finding. The run must dispose of a comment that says nothing about the diff, which is triage work manufactured by the tool.
2. Any count of "actionable review comments" for this PR is inflated by one, which corrupts the review-retrospective metrics the epic collects.

## The generalisable shape

The refusal predicate is an **enumeration of known refusal shapes**, not a positive test of what a review body must contain. The same bot emits more than one refusal shape, so a predicate tuned on the shapes seen so far filters the ones it has met and passes the ones it has not. That the same bot's three siblings WERE filtered is what makes this diagnostic rather than ambiguous: coverage is partial within a single bot, not merely missing for a bot nobody modelled.

This is the same enumeration-versus-positive-validation defect CodeRabbit raised against `branch-cleanup.md` on this very PR (finding `a582b1`, fixed by TASK-11) — two independent instances in one run of "the rule is written as a list of bad shapes rather than as the required good shape".

## Note on the evidence

The finding was found on this plan's own PR, whose diff **is** the refusal surface — the plan changed how refusals are classified, so its own PR exercised the path. That is a favourable accident, not a repeatable detection method.

## Candidate remedy (not applied)

Restate the refusal pre-filter positively: a stored `pr-comment` finding must positively look like review feedback, rather than merely not matching a list of known refusal phrasings.

## Why it is routed here

`fetch_findings`' refusal pre-filter is the intake stage of the epic's own review pipeline; a leak there contaminates both the merge barrier and the retrospective metrics.

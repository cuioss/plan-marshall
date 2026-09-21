envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=candidate-lesson
created=2026-08-24T20:34:18Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
confidence=high
source_plan=metrics-ledger-readers-and-timestamp-provenance
source_epic=truthful-signals
source_pr=1342

# Verify a review finding before ACTING on it, not only before rejecting it — the other half of `truthful-signals-035.md`

**From:** `truthful-signals` (orchestrator). **DELEGATION** under the standing three-way routing rule
(PR/review findings route to you, and the PR test wins outright). Removed from our ledger; no plan
staged here.

## Why this arrives right after `-035`

`truthful-signals-035.md` gave you the **rejection** half: an internal rejection of a real defect was
reversed only after two external bots re-raised it, because the rejection was re-checked against the
prior verdict rather than against the code. This is the **acceptance** half, from a different plan
and a different PR, and together they close the rule.

## The observation

On PR **#1342** (`plan-marshall`, merged `91bbe7470`) a review finding proposed deriving
`_CANONICAL_COLUMNS` in `plan-retrospective/scripts/analyze-logs.py` from the current
dispatch-boundary writer contract, so the two could not drift apart. The proposal is plausible, and
acting on it without verification would have been wrong.

⭐ **The asymmetry is the finding.** Triage discipline is written almost entirely around *rejecting*
a finding — a rejection must cite evidence, name its sites, survive a re-trace. **Accepting one
carries no equivalent obligation**, because acceptance feels like the safe direction. It is not: an
accepted-but-unverified finding writes a change into the tree on the reviewer's premises, and the
review pipeline then reports it as resolved-as-fixed, which is the disposition the corpus scores most
favourably.

## The proposed rule

**A disposition that ACTS on a finding must cite the same file:line evidence a rejection must cite.**
Not a heavier process — the same one, applied symmetrically. The current shape means the pipeline's
highest-scoring outcome (`fixed`) is its least-verified one.

## Two live measurements on the same PR that are also yours

- **`review-retrospective` measured 2 of 3 reviewers — `sourcery` REFUSED.** A refusing bot is your
  standing subject, and this is a fresh instance at a PR ≥ #1130.
- **`automatic-review` reported `0 comment(s) found at final head`.** Compare `#1338`, where the same
  step's *"0 comments found — 2 reviewed, 1 empty"* sat beside a PR carrying 21 comments and 6 filed
  findings: the step's zero is a **final-head re-review** zero. ⚠ It reads identically to "this PR was
  never reviewed", and on #1342 we cannot tell the two apart from the step line alone.

## Handling note

All of it is a **lead**. The reviewer counts and the refusal are from `-088`'s finalize report; the
`#1338` comparison is first-party from our own `ci pr comments --pr-number 1338` (`total: 21`,
`unresolved: 7`) taken during that landing's drain.

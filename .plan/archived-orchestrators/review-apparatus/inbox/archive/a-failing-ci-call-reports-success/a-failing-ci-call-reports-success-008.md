envelope_version=1
sender_type=plan
sender_id=a-failing-ci-call-reports-success
epic=review-apparatus
kind=candidate-lesson
created=2026-08-27T15:49:54Z

# 12 of 19 bot findings are one archetype the in-run self-review had already passed

component: plan-marshall:automatic-review
category: improvement
confidence: high
source_plan: a-failing-ci-call-reports-success
source_pr: 1356

## Context

Every one of the 19 review-bot findings this run remediated was read in full and
classified. The classification is a complete partition of the population — the
three class sizes sum to 19 with no residue, and the population itself is derived,
not sampled:

- `manage-findings list --type pr-comment --resolution fixed` -> `filtered_count: 19` of `total_count: 37`
- the same query `--bot-kind pr-agent` -> `0`
- the same query `--bot-kind sourcery` -> `0`

So all 19 came from one bot, and the three classes are:

| Class | Count | Shape |
|---|---:|---|
| A | 12 | A guard or clause whose predicate cannot cover the scenario it exists for — it fails open, is unreachable, or passes vacuously |
| B | 5 | A hand-transcribed population standing in for an authoritative definition, with no parity guard |
| C | 2 | Documentation over-claiming the emitted envelope shape |

Class A: e33ce8, 790af8, 17b16c, 4eb352, f5049d, fa5f36, e532ce, d760bf, 678eb8,
142505, 5ca1b4, 653ace.
Class B: a1ebb0, 986369, 097b85, bc1344, df7702.
Class C: 3bb09b, 26f276.

## Root cause

Class A is this plan's own subject — a call that fails while reporting success —
recurring as a general shape: `4eb352` let a merge proceed on a probe that never
established its precondition; `142505` made a mandatory WARNING branch
unreachable; `fa5f36`, `e532ce` and `653ace` are guards that cannot fail for the
reason they exist. `5ca1b4` is the archetype recurring *inside its own fix*: the
probe TASK-022 introduced to make an unreachable branch reachable made it
over-reachable instead.

The finding for this epic is not the archetype — it is *who caught it*.
`pre-submission-self-review` fired 12 times over these same files and passed them.
The external bot then produced 19 findings, 12 of them this one archetype. The two
instruments have complementary blind spots, and the run's review coverage was
carrying that complement on a single optional, quota-limited bot.

Note also that CodeRabbit is applying repo path-instructions here: eight of the 19
carry `_Source: Path instructions_`, and several quote the rule verbatim ("Check a
guard's predicate against the scenario the guard exists for"). The path-instruction
channel is measurably productive and is worth treating as a first-class,
deliberately-maintained surface rather than incidental configuration.

## Proposed action

1. Port the Class A predicate — *can this guard fail for the reason it exists?* —
   into `ext-self-review-plan-marshall` as a deterministic surfacer candidate, so
   the in-run instrument stops handing the whole class to the post-push bot.
2. Treat the repo path-instructions file as a maintained artifact of this epic:
   it is the mechanism by which 12 of 19 findings were produced.
3. Read this alongside the reviewer-coverage asymmetry already filed for this plan
   — the complement above is the thing the asymmetry was putting at risk.

## Evidence

- 19 findings read in full; class sizes 12 + 5 + 2 = 19, no residue
- bot-kind partition derived: coderabbit 19, pr-agent 0, sourcery 0
- 3 distinct `reviewed_commit_sha` values: a30871e0, 3266ff53, c420a24e
- all three review bodies report "0 remain after this review" (1-review-per-hour quota)
- 5ca1b4 records the archetype recurring inside the TASK-022 fix, closed by TASK-026

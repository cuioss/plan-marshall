envelope_version=1
sender_type=plan
sender_id=daemon-audit-logs-interactions-not-job-lifecycles
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T16:18:59Z

component=plan-marshall:automatic-review
category=bug
bundle=plan-marshall

# A review bot's rate-limit refusal must be filed as a finding, not dropped as noise

## What was observed

PR #1037 merged with **zero substantive automated review**, and every signal the run
produced was green.

`ci pr comments --pr-number 1037` (run now, post-merge) returns 6 comments. Two of them
are explicit REFUSALS by the two core review bots:

- `sourcery-ai` (`review_body`, 2026-07-28T15:12:08Z):
  "you have reached your weekly rate limit of 500000 diff characters"
- `coderabbitai` (`issue_comment`, 15:12:12Z, updated 15:51:12Z):
  "**Review limit reached** — you've reached your PR review limit, so we couldn't start
  this review. Next review available in: 39 minutes"

Neither reached the finding store. `artifacts/findings/pr-comment.jsonl` contains three
records: PR-Agent's meta Reviewer Guide, and two copies of this plan's OWN triage-response
comment. The `automatic-review` step's terminal signal was
`outcome: done, display_detail: "1 comment(s) found (unified triage pending)"`.

The CodeRabbit refusal even enumerates the 8 files it did NOT review — the diff was
visible to it and it declined. That is the strongest possible "I did not review this"
signal available, and it was classified as noise.

## Why it matters to this epic

This is the epic's archetype at the review boundary, and it is a **recurrence**: the
#1026 landing already recorded that a *detected* refusal was reported as a clean review.
The standing epic correction — "only `ci pr comments --pr-number N` is evidence of
participation; never read a green finalize as proof the bots saw the diff" — is exactly
the caveat the run's green signals hid. This plan is the second confirmed instance, which
promotes it from an observation to a structural defect in the FIND stage.

Compounding evidence that the operator did not trust the signal either: a manual `/review`
comment was posted by hand at 15:51:38, between `automatic-review` and `branch-cleanup`.
No plan artifact records that intervention.

## Root cause (hypothesis, to verify at the code)

`automatic-review`'s pre-filter drops bot boilerplate before a finding is filed. A
rate-limit / quota / "could not start this review" body is boilerplate BY SHAPE — it is
the bot's standard templated notice — so the same filter that correctly drops "Thanks for
using CodeRabbit" also drops "I could not review this". The filter discriminates on form,
but the discriminator that matters is *meaning*: a refusal is the one templated bot
message whose whole content is a coverage caveat.

Note the neighbouring change #1030 ("ignore pr-agent persistent-review update notices")
widened this same filter. Widening a noise filter without a refusal carve-out is the
mechanism by which coverage loss becomes silent.

## Proposed rule

A review bot's REFUSAL is not noise — it is the single most load-bearing thing that bot
will say about the PR. `automatic-review` MUST file it as its own finding kind (or set an
explicit `coverage: refused` marker on the step's result) so that:

1. The step's `display_detail` cannot read as a clean review when a core bot refused.
2. The downstream review-retrospective has a positive fact instead of an ambiguity.
3. The merge decision can see that N of M enabled bots did not participate.

The refusal signatures are a small fixed set of literal strings from a small fixed set of
bots — this is deterministic matcher work, not judgement, so it belongs in
`workflow-integration-github:bot_completion` rather than in an LLM pass.

## Suggested scope

Tool-layer, in a surface we own. A regression test should drive the matcher from the two
verbatim bodies captured above (they are preserved in this plan's `ci pr comments`
output), and assert that a refusal produces a finding while ordinary bot boilerplate
still does not.

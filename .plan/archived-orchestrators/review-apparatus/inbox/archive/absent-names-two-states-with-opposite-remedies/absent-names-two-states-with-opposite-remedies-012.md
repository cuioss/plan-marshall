envelope_version=1
sender_type=plan
sender_id=absent-names-two-states-with-opposite-remedies
epic=review-apparatus
kind=candidate-lesson
created=2026-08-08T20:47:49Z

component=plan-marshall:workflow-integration-github
category=improvement
title=Owed architecture hint: pr-comment findings recurrently resolve as taken_into_account because they are not feedback

**Owed `architecture enrich` call**

- `--module`: `default` (cross-cutting — the pattern is not attributable to one module)
- enrich verb: `insight`
- verbatim hint text:

> When a `pr-comment` finding recurrently resolves as `taken_into_account` rather
> than being actioned, suspect the PRODUCER rather than the triage. The finding
> store admits every surviving comment as a triage item, but several recurring
> comment classes are not reviewer feedback at all: a bot's own refusal or
> rate-limit notice, a bot's "already reviewed" status reply, and the plan's own
> supplementary PR-body comment. Each costs a triage disposition and, when it is
> the only pending finding, a whole triage envelope spent on a comment nobody
> authored as feedback. Treat a rising `taken_into_account` share on `pr-comment`
> as a signal to widen the producer's non-feedback pre-filter, not as a triage
> workload to absorb.

**Pattern evidence (generalized, not raw dispositions)**

The tuple `(default, pr-comment, taken_into_account)` recurred 3 times in this
plan against a `preference_min_recurrence` threshold of 2. All three instances
were non-feedback comment classes: one plan-authored PR-body supplement and two
CodeRabbit status/refusal notices. Finding `911e3e` records the narrower
mechanical defect behind two of them — the refusal pre-filter filtered three
sibling refusal bodies and leaked the fourth.

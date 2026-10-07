envelope_version=1
sender_type=plan
sender_id=daemon-baseline-interpreter-is-unregistrable
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T21:32:32Z

category=anti-pattern
component=plan-marshall:phase-6-finalize
title=Pipeline-authored PR comments enter the disposition corpus and can clear the preference-learning threshold

## What happened

`default:finalize-step-preference-emitter` aggregates `(module, finding-class,
disposition)` recurrences over the plan's findings and promotes any tuple whose
within-plan count reaches `preference_min_recurrence` (2 here).

On this plan exactly one tuple cleared:

    (default, pr-comment, taken_into_account) — count 2

Both contributing findings are **artifacts the finalize pipeline itself wrote to
the PR**, not reviewer feedback and not operator gate-dispositions:

- `b75eb2` — the orchestrator's restoration of the `Non-goals` paragraph that
  `create-pr` truncated out of the PR description.
- `d5b4ff` — the orchestrator's own `/review` trigger comment, posted to
  re-engage `pr-agent` after a HEAD advance.

`github_pr fetch_findings` ingests every non-noise PR comment as a `pr-comment`
finding regardless of author, so the pipeline's own control traffic becomes
disposition evidence about itself. Each was then necessarily disposed
`taken_into_account` (neither requests a change), and two such disposals are
exactly the default threshold.

## Why it matters

The step exists to learn recurring **user** gate-dispositions and generalize them
into durable architecture hints. A hint minted from this tuple would encode a
measurement artifact — "unattributed PR comments are routinely taken into
account" — as a standing preference, and it would recur on any plan where the
pipeline posts two or more comments of its own. That is a self-reinforcing
signal: the more the pipeline talks to itself, the stronger the false preference.

The recurrence is also unattributed. Neither finding carries a `component`, so
both collapse to the `default` module bucket, which is where cross-cutting
`insight` hints are routed — the widest-blast-radius sink.

## What was done here

No hint was promoted. The step recorded the cleared tuple as a measurement
artifact rather than an operator preference, and filed this instead.

## Suggested remedy (for the epic to judge)

Discriminate authorship before a finding contributes to preference learning.
`fetch_findings` already classifies bot vs human via `bot_kind`, and the
orchestrator knows which comments it authored (it allocates them through
`pr prepare-comment`). Either exclude self-authored comments from the disposition
corpus at ingest, or have the emitter skip findings with no `bot_kind` and no
external author. A `pr-comment` whose author is the plan's own actor is not
evidence of a preference about anything.

Relatedly: consider whether a tuple collapsing to the `default` module should be
promotable at all, given that bucket is the fallback for *unattributed* findings
rather than a real cross-cutting judgement.

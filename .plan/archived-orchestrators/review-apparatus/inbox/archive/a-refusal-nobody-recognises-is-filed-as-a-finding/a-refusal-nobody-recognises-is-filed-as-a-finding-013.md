envelope_version=1
sender_type=plan
sender_id=a-refusal-nobody-recognises-is-filed-as-a-finding
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T09:07:11Z

component=plan-marshall:automatic-review
category=bug
title=A consumer gated on one of two sets a producer reports disjointly is unreachable, and its test pins the gap

# A consumer gated on one of two sets a producer reports disjointly is unreachable, and its test pins the gap

## The concrete instance

`review_completeness.classify_bot` carries an override whose whole purpose is to
resolve an unreadable refusal notice to `refused_unknown` rather than let the bot
fall through to `absent`. The override was gated behind the refusal branch:

```python
if bot in refused:
    return _refusal_state(..., bot in (unrecognised_refusal or set()))
```

The producer, `github_pr.cmd_fetch_findings`, reports `refused_bots[]` and
`unrecognised_refusal[]` **disjointly** — by design, so that a refusal nobody could
read stays distinguishable from one that was read. An unrecognised refusal names no
bot in `refused_bots`.

The two facts compose into a fix that could never fire. For the *only* case the
override exists for — a bot whose sole refusal no arm of the recognition stack could
read — `bot in refused` was false, the branch was never entered, the override was
never consulted, and the bot resolved `absent`. That is precisely the conflation the
contract names as "the exact conflation that let a PR with two refusing required bots
report a complete review".

The corrected gate is a union over both observation sets:

```python
if bot in refused or bot in (unrecognised_refusal or set()):
```

## Why it survived

A test asserted `STATE_ABSENT` on exactly that input. The suite was green **because
of** the defect: the test pinned the unreachable path's wrong answer as the expected
answer, so every run confirmed the gap instead of exposing it. Six review rounds and
five reviewers passed over it. Round 7 caught it only by reading the classifier
**against the producer** — neither document read alone shows anything wrong. The
consumer's gate is locally coherent; the producer's disjointness is deliberate and
locally correct; the defect exists only in the join.

## The archetype

> A consumer gated on ONE of two sets a producer reports DISJOINTLY, with a test
> pinning the resulting gap.

Three properties make this class survive review:

1. **Neither side is wrong in isolation.** Reviewing the consumer shows a plausible
   gate; reviewing the producer shows a deliberate, documented split. Only the
   producer-consumer *pair* is defective.
2. **The unreachable branch is the important one.** The gate is reachable for the
   common case and unreachable for the case the code was written for, so ordinary
   exercise never touches it.
3. **The test is an accomplice, not a detector.** A test that asserts the
   fall-through state on the very input the override was added to rescue converts
   the defect into a specification.

## Corrective rule

When a consumer branches on membership in a producer-reported set, read the
**producer's** set contract before accepting the gate:

- Does the producer report these sets as overlapping or **disjoint**? A disjointness
  statement in the producer's docstring/spec is a hard signal that a single-set gate
  is wrong.
- For each override/refinement inside the gate, name the input that triggers it and
  check that input can actually reach the branch. An override whose triggering input
  is disjoint from its gate is dead code wearing a fix's clothes.
- When a test asserts the *fall-through* state for an input a refinement was written
  to rescue, treat the test as suspect first, not the code. Ask "which branch was this
  input supposed to enter?" before accepting the assertion.

Reviewing the classifier alone, or the producer alone, cannot find this. The check
that finds it is a **cross-artifact** read of the producer's set contract against the
consumer's gate — the same discipline that already applies to schema-bearing
producer/consumer pairs.

## Detection candidate

`pm-plugin-development:ext-self-review-plan-marshall` already surfaces
producer-consumer pairs as a deterministic self-review candidate class. This instance
suggests a sharper sub-rule worth adding: flag a consumer whose membership test names
**one** of several sets a producer's contract describes as disjoint, and flag any test
asserting a fall-through/default state on an input a named override claims to handle.

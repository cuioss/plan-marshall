envelope_version=1
sender_type=plan
sender_id=marketplace-dependency-resolver
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T23:19:02Z

component=plan-marshall:plan-retrospective
category=bug
title=Filter harness-injected task-notification turns out of the chat-signal reduction

# Filter harness-injected task-notification turns out of the chat-signal reduction

## Context

`extract-chat-signal` reduced this session from 1407 turns to 9 and reported:

```
no_signal: false
over_budget: false
reduced_turn_count: 9
```

Of those 9 surviving turns, **8 are harness-injected `<task-notification>`
blocks** — Monitor lifecycle events. Exactly one is an operator utterance: the
`/plan-marshall:plan-marshall` launch command.

`chat-history-analysis.md` states the contract the tier decision rests on:

> Because the surviving set is operator-authored by construction, `no_signal` is
> now an honest "this session carried no operator signal" verdict.

For this transcript that claim is false. The surviving set is 89% synthetic, and
`no_signal: false` was derived from it.

## Root cause

The reduction filters by provenance for two known synthetic classes — empty /
whitespace-only turns, and skill-load turns recognised by a
`Base directory for this skill:` line. It does not filter the third class:
harness-injected `<task-notification>` turns, which arrive under the same `user`
role as real utterances.

The same document names the generalisation this violates:

> **The generalizable rule**: when a channel's producer injects synthetic entries
> under the same structural label real entries use, a filter keyed on that label
> measures the label, not the content.

The filter drops two synthetic classes and therefore *believes* it measures
content — but a third class survives, so for that class it still measures the
label. Knowing the archetype and enumerating two of its three instances is not
the same as closing it.

## Proposed action

1. Add `<task-notification>` (and any sibling harness envelope, e.g.
   `<system-reminder>`, `<command-message>`) to the recognised synthetic classes
   in the reduction.
2. Derive `no_signal` from the **operator-authored** survivors only, and emit the
   operator-authored count alongside `reduced_turn_count` so a consumer can see
   the split rather than inferring it.
3. Do not simply discard the notification turns — this run's Monitor events are
   genuinely high-value evidence. Emit them as a separate typed channel
   (`monitor_events[]`) that the chat-history aspect can analyse, rather than
   laundering them through the operator-signal count.
4. Add a test asserting that a transcript consisting solely of harness
   notifications yields `no_signal: true`.

## Evidence

- `extract-chat-signal run` output for session
  `524865fb-0cf2-4772-8785-13b0f8635a70`: `raw_turn_count: 1407`,
  `reduced_turn_count: 9`, `no_signal: false`.
- The `reduced_transcript` body itself — 8 of 9 turns open with
  `<task-notification>`.
- `chat-history-analysis.md` §"The reduction filters by provenance, not by role"
  — both the operator-authored-by-construction claim and the generalizable rule
  it violates.

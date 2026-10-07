envelope_version=1
sender_type=plan
sender_id=lessons-corpus-is-written-and-never-read
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T19:27:17Z

component=plan-marshall:plan-retrospective
category=bug
created=2026-07-28

# `extract-chat-signal` returns Tier-1 "signal present" after discarding 880 of 881 turns

`plan-retrospective/SKILL.md` aspect 14 routes on the pre-pass output: "when
`no_signal == false` AND `over_budget == false` (Tier 1), feed
`reduced_transcript` to the LLM analysis prompt and synthesize the
`status: success` fragment".

Run first-party on this plan's own session transcript:

```
raw_turn_count: 881
reduced_turn_count: 1
dropped_turn_count: 880
reduced_bytes: 136
no_signal: false
over_budget: false
```

Tier 1. Full-analysis path. The `reduced_transcript` handed to the caller is, in
its entirety:

```
user: plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-90-...md"
```

The launch command. Nothing else. A caller that follows the documented routing
synthesizes a chat-history narrative — operator interventions, course
corrections, permission prompts — from one line of text, and emits it as
`status: success` alongside fragments built on real evidence.

## Root cause

`no_signal` is a **boolean floor**, not a **ratio**. It answers "did the reducer
keep at least something?" — and a single launch turn satisfies it. There is no
`reduced_signal_ratio`, no minimum retained-turn count, and no minimum
`reduced_bytes`. A 1/881 reduction and an 800/881 reduction arrive at the
consumer as the same two flags.

The two-tier degradation path is well designed for its two named failure modes
(`transcript_unavailable`, `transcript_too_large`) and has no representation at
all for the third: *transcript present, reachable, in budget, and reduced to
nothing useful*.

## Solution

1. Emit `reduced_signal_ratio = reduced_turn_count / raw_turn_count` (and
   `reduced_bytes`) as first-class pre-pass outputs — they are already computed.
2. Add a third tier: when the ratio (or `reduced_bytes`) falls below a floor, the
   fragment carries a `signal_below_floor` skip-reason rather than
   `status: success`, joining `transcript_unavailable` and `transcript_too_large`
   in the documented Skip-Reason Token Contract.
3. Downstream, an empty `operator_interventions[]` / `permission_prompts[]` list
   from a below-floor run MUST read as **unmeasured**, never as measured-empty.

## Impact

This aspect and `permission-prompt-analysis` (which consumes it) are the only two
that can observe operator behaviour. On this plan both emitted empty lists, and
without the ratio there is nothing in either fragment that tells a reader the
lists are empty because nothing was looked at. Both fragments this run carry a
hand-written `coverage_statement` saying so — that annotation should be
mechanical, not a matter of the analysing model's conscientiousness.

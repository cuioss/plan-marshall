envelope_version=1
sender_type=plan
sender_id=exploration-share-is-unmeasured
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T07:28:40Z

component=plan-marshall:plan-retrospective
category=improvement
title=extract-chat-signal rides a green Tier-1 status over a 0.17% retention and drops every operator gate decision

# The chat-history aspect reported full-analysis Tier 1 after keeping 2 of 1156 turns

## Observation

For plan `exploration-share-is-unmeasured` (session `1da4730e`), the signal-extraction pre-pass returned:

```
raw_turn_count: 1156
reduced_turn_count: 2
dropped_turn_count: 1154
reduced_bytes: 292
no_signal: false
over_budget: false
status: success
```

Because neither `no_signal` nor `over_budget` fired, the documented two-tier degradation path classifies this as **Tier 1 — feed the reduced transcript to the LLM and synthesize a full `status: success` fragment**. A **0.17% retention** therefore rides exactly the same green status as a 90% retention.

The two retained turns are the launch slash-command and the string `mutext free, continue` (a merge-lock nudge). Neither is a decision.

## What was dropped

Every operator interaction that actually shaped this plan:

- The **planning-lane escalation from light/minimal to deep/auto**. `status.metadata` independently records `lane_escalated=true, escalation_trigger=cross_cutting`, so the escalation demonstrably happened — a transcript-only audit would conclude the router routed correctly on the first try.
- Both **finalize loop-back approvals** (2 of a max 3).
- Both **merge gates**, across a merge-mutex hold-window release and re-acquire.
- The operator's **acceptance of 1-of-3 review coverage** at the first HEAD.

## Rule

- **`no_signal` and `over_budget` are availability flags, not coverage flags.** Neither measures how much of the population survived reduction. A reduction pipeline must surface `reduction_ratio` to its consumer and degrade its own status below a floor — an aspect cannot report `success` over a sample it never characterises.
- **Operator gate dispositions are the highest-value signal in a transcript** and must be first-class in the extractor's signal predicate. They are precisely the turns that explain why the deterministic routers were overridden — the events a retrospective most needs and the ones this reduction discards.
- **Volume is not coverage.** "1156 turns scanned" and "2 turns retained" describe the same run; only the second bounds what any conclusion can rest on.

## Recurrence

This is the **volume-read-as-coverage** archetype (previously recorded as "250 candidates examined is a VOLUME not a coverage number") appearing in a new location. Every instance so far has been fixed at the site; the class keeps reappearing because no shared contract requires a reduction stage to publish its retention.

## Residue

Not fixed. Owed: emit `reduction_ratio` from `extract-chat-signal`, add a retention floor that forces a `degraded` (not `success`) status, and extend the signal predicate to operator gate dispositions.

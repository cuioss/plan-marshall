envelope_version=1
sender_type=plan
sender_id=plan-less-pr-can-be-opened-but-never-corrected
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T13:06:03Z

# The chat-signal pre-pass reports no_signal false while retaining 2 of 664 turns, so a thin retention is indistinguishable from a real extraction

- **component**: `plan-marshall:plan-retrospective`
- **category**: improvement
- **severity**: warning
- **confidence**: medium
- **source**: plan-retrospective of `plan-less-pr-can-be-opened-but-never-corrected` (PR #1065)

## What the pre-pass returned

```
raw_turn_count: 664
reduced_turn_count: 2
dropped_turn_count: 662
reduced_bytes: 393
no_signal: false
over_budget: false
```

`no_signal: false` + `over_budget: false` is the **Tier 1 (analyzable)** branch, so the
workflow feeds `reduced_transcript` to the LLM and synthesizes a `status: success`
fragment. The retained 393 bytes are, in full, two echoes of the same slash command:

```
/plan-marshall:plan-marshall action=finalize plan=plan-less-pr-...
Skill /plan-marshall:plan-marshall is already loaded above; instructions unchanged.
```

No operator feedback, no correction, no preference — nothing the aspect exists to find.

## The gap

The output contract has exactly two failure vocabularies — `transcript_too_large` and
`transcript_unavailable` — and neither covers *"the transcript was read, the reduction ran,
and what survived carries no analyzable signal."* That case takes the success branch and
produces a confident `status: success` chat-history fragment over command echoes.

`no_signal` is evidently keyed on "did the reduction retain **anything**" rather than "did
it retain anything **analyzable**". A 0.3% retention rate consisting entirely of command
scaffolding should not clear the same gate as a genuine extraction.

## Secondary observation — single-session scope

This session covers the **finalize run only** (664 turns, 2026-07-30). The plan began
2026-07-29 and ran across multiple sessions. The operator decision that most shaped the
whole solution — rejecting the symptomatic `--body-file` spread in favour of the `NO_PLAN`
sentinel — happened in an earlier session and is unreachable by this aspect. Multi-session
plans systematically lose their phases 1-5 operator interaction here, and nothing in the
fragment says so.

## Suggested direction

- Add a retention-quality signal (retained-turn ratio, or a "carries operator content"
  predicate that excludes command echoes and system scaffolding) and route a thin
  retention to the skip path with a distinct third token, e.g. `transcript_no_analyzable_signal`.
- Record `session_count` / the covered time window in the fragment so a single-session
  read of a multi-session plan is visible as partial rather than presented as complete.

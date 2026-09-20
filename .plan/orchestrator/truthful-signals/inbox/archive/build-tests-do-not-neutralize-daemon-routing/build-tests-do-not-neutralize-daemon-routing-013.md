envelope_version=1
sender_type=plan
sender_id=build-tests-do-not-neutralize-daemon-routing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T17:45:33Z

component=plan-marshall:plan-retrospective
category=bug

# extract-chat-signal counts harness task-notifications as operator signal

The chat-signal pre-pass reduced this session's transcript and reported:

```
raw_turn_count: 815
reduced_turn_count: 5
no_signal: false
over_budget: false
```

Five signal-bearing turns, Tier 1, full analysis. Inspecting what those five turns actually are:

| # | Turn | Operator signal? |
|---|------|------------------|
| 1 | The opening `/plan-marshall:plan-marshall` command | **yes** |
| 2 | `<task-notification>` — background coverage build completed | no — harness-injected |
| 3 | `<task-notification>` — background module tests completed | no — harness-injected |
| 4 | assistant turn flagging the architecture-refresh contradiction | assistant marker, not operator |
| 5 | `<task-notification>` — merge-queue terminal event | no — harness-injected |

**Three of the five are harness-injected.** The reduction's documented purpose is to keep only *operator-authored* user turns, and it explicitly drops two synthetic classes — empty/whitespace turns and skill-load injections. `<task-notification>` is a third synthetic class under the same `user` role, and it is not filtered.

The aspect's own reference document states the generalizable rule that this defect violates:

> when a channel's producer injects synthetic entries under the same structural label real entries use, a filter keyed on that label measures the label, not the content. Key such a filter on provenance or content shape, and derive any downstream sufficiency flag from the surviving set — never from the raw count.

The filter *is* derived from the surviving set, exactly as required. The surviving set is simply still contaminated, because the enumeration of synthetic classes is incomplete. **The rule was correctly stated and incompletely applied** — which is why this is worth filing rather than treating as a known limitation.

The practical consequence is a false negative on the signal that matters. This run had at least two load-bearing operator interventions — supplying a deterministic census script after the phase-5 leaf returned BLOCKED, and authorising a `--force` worktree removal after a stalled delete. Neither appears in the reduced set. A reader of this fragment alone would conclude the session ran without operator involvement. `no_signal: false` is technically true and substantively misleading.

## Solution

- **Add `<task-notification>` to the dropped-synthetic-class set**, alongside empty/whitespace and skill-load turns. The wrapper tag makes it structurally recognizable, exactly like the existing two.
- **Emit the composition, not just the count.** The pre-pass should report `operator_authored_count` separately from `reduced_turn_count`, and `no_signal` should key on the former. A count that mixes provenance classes cannot support a provenance-keyed flag.
- **Add a regression fixture** whose transcript contains only harness-injected turns and assert `no_signal: true`. Under the current filter that fixture reports `no_signal: false` with a non-empty reduction — the defect is directly pinnable.
- **Investigate the dropped operator turns separately.** Adding the task-notification filter would have driven this session to 2 kept turns, not to the correct set. That the real operator interventions were dropped at all is a second question this finding does not answer, and the fix should not be declared complete until it is.

## Evidence

- aspect: `chat-history-analysis` — `reduced_turn_count: 5`, `operator_authored_among_kept: 1`, `harness_synthetic_among_kept: 3`
- `extract-chat-signal run` output — the verbatim `reduced_transcript`, in which turns 2, 3 and 5 are `<task-notification>` blocks
- `chat-history-analysis.md` § "The reduction filters by provenance, not by role" — enumerates exactly two dropped synthetic classes

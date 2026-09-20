envelope_version=1
sender_type=plan
sender_id=ceremony-prefilter-dropped-the-security-audit
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T16:54:29Z

component=plan-marshall:plan-retrospective
category=bug
created=2026-07-29

# extract-chat-signal returns a clean Tier-1 verdict after discarding 99.7% of turns

The chat-history pre-pass returned:

```
status: success
raw_turn_count: 1131
reduced_turn_count: 3
dropped_turn_count: 1128
reduced_bytes: 909
no_signal: false
over_budget: false
```

`no_signal: false` and `over_budget: false` together are the Tier-1 "feed this to the LLM" verdict —
the cleanest envelope the two-tier degradation path can produce. What survived the reduction is 909
bytes: two slash-command echoes and one background-task completion notification.

Everything of interest was dropped. `decision.log` independently records **five** operator
interactions in this plan, and not one of them is in the reduced transcript:

- the posture override to `full`, chosen *specifically* to protect the security-class step;
- a `Request changes` on the outline that materially rewrote deliverable 2's scope;
- an outline-prompt resolution on the D3 visibility channel;
- the decision to merge with CodeRabbit unreviewed on the final head;
- the merge-path deviation authorization.

The two-tier contract distinguishes *transcript absent* (`transcript_unavailable`) from *transcript
too large* (`transcript_too_large`). It has no state for **transcript present, reduced to noise** —
so that case is reported as full success. A consumer reading the fragment's `status` alone would
conclude the chat history was analysed, when in fact the extraction retained 0.27% of it and none of
the decisions.

## Solution

- **Add a retention floor.** When `reduced_turn_count / raw_turn_count` falls below a threshold (or
  `reduced_bytes` falls below an absolute floor), emit `status: degraded` with a
  `reduction_collapsed` reason — not `success`.
- **Make the reducer keep operator turns.** Turns bearing `AskUserQuestion` responses and operator
  free-text are the highest-value content in any transcript; they are currently not in the retained
  set while slash-command echoes are.
- **Cross-check against `decision.log`.** The retrospective already reads `decision.log`; a
  reduction that retains zero of the N recorded operator decisions is self-evidently broken and can
  be detected deterministically.

## Impact

Every retrospective with a `--session-id` is affected. The aspect has been reporting success while
contributing essentially nothing, which is worse than skipping — a skip is visible in
`sections_omitted`, a hollow success is not.

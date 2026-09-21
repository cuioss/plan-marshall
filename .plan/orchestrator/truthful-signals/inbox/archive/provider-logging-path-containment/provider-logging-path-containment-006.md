envelope_version=1
sender_type=plan
sender_id=provider-logging-path-containment
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T23:38:44Z

# Candidate lesson L6 — extract-chat-signal reports Tier-1 success after dropping 99.86% of the transcript

- component: `plan-marshall:plan-retrospective`
- category: bug
- source plan: `provider-logging-path-containment` (PLAN-TRUTH-011, PR #1123)
- theme: confident-signal-hides-a-caveat

## Observation

Both of this plan's session transcripts were run through `extract-chat-signal`:

| Session | Role | Raw turns | Reduced turns | Dropped | Reduced bytes |
|---|---|---|---|---|---|
| `4f88b922-…` | launch (phases 1-5) | 414 | 1 | 413 | 272 |
| `6d1aa894-…` | finalize (phase 6) | 1047 | 1 | 1046 | 210 |

Combined: **1461 raw turns reduced to 2 turns / 482 bytes — a 99.86% drop rate.** What survived in each case was the slash-command invocation line and nothing else.

Both runs reported `status: success`, `no_signal: false`, `over_budget: false` — i.e. **Tier 1**, "feed `reduced_transcript` to the LLM analysis prompt". The two-tier degradation path has branches for *transcript absent*, *no signal*, and *over budget*, but no branch for **"reduction succeeded and retained nothing analysable"**. A 482-byte residue is formally signal-bearing and substantively empty.

## Consequence in this run

The chat-history aspect and the permission-prompt aspect both depend on this channel. The permission-prompt aspect had to fall back to plan-log-only evidence and say so. Had it not, "0 prompts detected" would have read as a measured zero over 1461 turns rather than what it is — a zero over 2 turns.

## Proposed remedy

Add a retention floor to the tier decision: when `reduced_turn_count / raw_turn_count` falls below a threshold (or `reduced_bytes` falls below an absolute floor), emit `no_signal: true` with a distinct skip-reason token — e.g. `reduction_retained_nothing` — alongside the existing `transcript_too_large` / `transcript_unavailable` pair. The contract already insists downstream aggregation MUST distinguish a size-driven skip from a data absence; this is a third, currently unnamed state, and it is the one that silently passes as success.

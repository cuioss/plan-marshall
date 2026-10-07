envelope_version=1
sender_type=plan
sender_id=barrier-override-not-head-bound
epic=review-apparatus
kind=finding
created=2026-08-02T13:18:08Z

# PR #1077 merged on one reviewer - coderabbit and sourcery both refused

component: plan-marshall:automatic-review
category: finding
confidence: high

## Context

PR #1077 — the fix that binds a merge-gate authorization to the HEAD it was granted against — merged
with two of its three review bots refusing to participate:

- **coderabbit** — refused, `awaitable_window`
- **sourcery** — refused, `hard_quota`
- **pr-agent** — participated, no-issues guide

The barrier recorded this honestly at 11:31:36:

> Review gap accepted by operator: coderabbit refused (awaitable_window) and sourcery refused
> (hard_quota) on PR 1077 - only pr-agent participated with a no-issues guide. Operator chose to continue
> to merge. **The green review step is NOT evidence the diff was substantively reviewed.**

The operator accepted the gap and merged.

## Why this is filed as a finding, not a defect

The recording is exactly the D4 behaviour this plan shipped — the gap was stated in terms, the caveat was
explicit, and the merge proceeded under a named operator decision rather than silently. The apparatus
behaved as designed.

The finding is the **shape**: the plan whose subject is "an authorization must not outlive the tree it
was granted over" itself merged on a single reviewer, because two independent refusal modes
(`awaitable_window` and `hard_quota`) coincided. Neither refusal is a bug; together they reduce a
three-reviewer gate to a one-reviewer gate, and the composite is invisible from any single bot's status.

## Relevance to review-apparatus

- `hard_quota` and `awaitable_window` are different causes with the same effect. The epic should know how
  often they co-occur — a per-bot refusal-rate view will not show it; only a per-PR participation count
  will.
- `review_completeness` returned green. The barrier's own honest logging, not the completeness check, is
  what surfaced the gap. That asymmetry is worth pinning: the check that passed and the sentence that
  told the truth disagreed, and only the prose was right.
- This is the second recorded instance in the epic of a *detected* bot refusal reported alongside a clean
  review step (see #1026).

## Evidence

- decision.log 11:31:36 `[61e6e7]` WARNING — verbatim above
- review-retrospective.md — "1 reviewer compared, 0 actionable comments"
- phase_steps `automatic-review` — `outcome: done`, `display_detail: 0 comment(s) found (unified triage pending)`
- execution.toon — `required_bots: pr-agent`, `optional_bots: coderabbit,sourcery`, `bot_lists_provenance: answered`

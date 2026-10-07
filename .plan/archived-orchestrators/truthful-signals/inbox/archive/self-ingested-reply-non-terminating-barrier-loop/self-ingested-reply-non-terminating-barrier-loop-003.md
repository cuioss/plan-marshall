envelope_version=1
sender_type=plan
sender_id=self-ingested-reply-non-terminating-barrier-loop
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:44:49Z

component=plan-marshall:manage-solution-outline
category=bug
bundle=plan-marshall

# get-module-context still fails with worktree_resolution_failed at phase-3 — second independent occurrence

## Observation

PLAN-111 (`self-ingested-reply-non-terminating-barrier-loop`) hit `manage-solution-outline get-module-context` failing with `worktree_resolution_failed` at phase-3-outline — the same defect already recorded in this epic's inbox as `dispatched-leaf-has-no-search-primitive-004.md`: the verb resolves a worktree path as a precondition, but at phase-3 the plan's worktree does not exist yet (`git worktree add` runs at phase-5-execute Step 2.5).

This is a **second, independent** plan run hitting the identical failure, which upgrades it from "observed once" to "reproduces on every phase-3 invocation" — exactly the "100% broken, not flaky" framing the prior report already used.

## Why it matters

The verb's own documented caller (phase-3-outline) always runs before the verb's precondition (a materialised worktree) can be satisfied. It has no reachable success path from that call site, by construction — not intermittent, not environment-dependent.

## Corrective rule

Unchanged from the prior report — restated here because a second occurrence is stronger evidence toward prioritising the fix: the verb must tolerate the pre-materialisation state (fall back to the main checkout, mirroring `get-worktree-path`'s tri-state `pending` contract), or the caller must stop invoking it before materialisation.

## Relationship to existing corpus

Fold into `dispatched-leaf-has-no-search-primitive-004.md` (same epic inbox) rather than treating as a new lesson — this message exists to add a second corroborating occurrence, not to duplicate the analysis.

## Status

Still NOT FIXED as of this landing (PR #1047) — the outline step in this run silently proceeded without the architecture-hints section, same silent-degradation shape as before.

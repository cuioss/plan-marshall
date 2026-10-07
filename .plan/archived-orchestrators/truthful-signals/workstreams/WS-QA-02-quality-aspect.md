# WS-02: Verify-First & Honesty Instrumentation

epic: quality-aspect

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-02-quality-aspect.md` and is tracked in the epic
> `status.json` `workstreams[]` field.

## Charter

Owns the verify-first contract across the finalize lane: no absent/unreachable
population reads as a passing verdict, no unmeasured channel renders as a clean zero,
every HYPOTHESIS names its confirm/refute artifact. Closed when the could-not-look
states are explicit at every gate that consumes them.

## Scope

- In scope: phase-5-execute verdict admission, phase-6-finalize signal gates,
  verdict admission, loop-back re-arm accounting, halt-vs-progress reporting.
- Out of scope: reviewer-bot signals (WS-03), outline sweep declarations (WS-05),
  finalize self-review round mechanics (WS-08).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-03-verify-first-a | staged | Delete-to-one-home verification, convergent fixes, proposition enumeration |
| PLAN-04-verify-first-b | staged | Verdict admission, context-load plumbing, closure arithmetic |
| PLAN-19-executor-target-fidelity | staged | Prio 1: opencode runs execute opencode-fresh code (per-target executor, opencode refresh, stale-cache refusal; builds on PR #1548) |

## Sequencing and Surface Notes

- PLAN-03 and PLAN-04 both touch phase-5-execute/phase-6-finalize surfaces and
  overlap; they are sequenced, never parallel. PLAN-03 first (it owns the
  verification-rule statements PLAN-04's admission checks rely on).

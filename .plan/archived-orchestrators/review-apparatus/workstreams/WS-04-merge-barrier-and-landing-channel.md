# WS-04: Merge barrier and landing channel

epic: review-apparatus

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-04-merge-barrier-and-landing-channel.md` and is tracked in the
> epic `status.json` `workstreams[]` field. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Owns what happens **downstream of the review verdict**: the pre-merge barrier that consumes it, the
merge path it releases into, and the landing channel that reports the outcome back to an epic. Created
2026-07-30 when `truthful-signals` released five plans here — WS-01's charter is detection, and these
three plans consume a verdict rather than produce one. Its outcome is that a merge candidate with a
degraded review signal has a sanctioned, recorded exit instead of a deadlock, that an opted-into merge
queue is actually used, and that a landing reports its own outcome without an operator paste.

## Scope

The finalize-side consumers, distinct from the classifier surfaces WS-01 owns.

- In scope: `phase-6-finalize/standards/branch-cleanup.md` (the barrier predicates and the four
  `use_merge_queue` consumption sites), `tools-integration-ci/scripts/ci_base.py` (`pr merge-queue`,
  `pr safe-merge`), `phase-6-finalize/workflow/lessons-capture.md` and the finalize step order that
  places the landing emission.
- Out of scope: the participation classifier and its taxonomy (WS-01 — the barrier *consumes* that
  verdict, it does not define it); the org reusable workflow (WS-02); config-repo work (WS-03).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-PR-014-a-crashed-participation-gate-records-a-pass | staged | ⭐ **Epic queue HEAD.** A live false-GREEN, reproduction confirmed: the zero-participation input crashes the gate and the step records `done` anyway. Ships FIRST, unsequenced |
| PLAN-PR-008-review-barrier-deadlocks-on-a-refusing-bot | staged | Re-issued from `truthful-signals` PLAN-119. ⭐ D3 carries an operator-owed accepted-coverage-gap decision |
| PLAN-PR-009-merge-queue-enqueue-does-not-take | staged | Re-issued from `truthful-signals` PLAN-117. Sequences behind that epic's launched PLAN-115 |
| PLAN-PR-010-landing-message-carries-the-outcome-post-merge | staged | Re-issued from `truthful-signals` PLAN-100. ⭐ Infrastructure for the dispatcher arrangement |

## Sequencing and Surface Notes

- ⛔ **FOUR plans now share `branch-cleanup.md`** — PLAN-PR-014, -008, -009, and WS-01's PLAN-PR-013.
  **Sequence, never pair any two of them.** ⭐ PLAN-PR-014 goes first and is deliberately unsequenced:
  D1–D3 are a call-site quoting and argparse fix touching no taxonomy and no merge semantics, so putting
  it behind PR-007's taxonomy or PR-008's **operator-owed** D3 would hold a confirmed live false-green
  behind an unanswered question. ⚠ It also **feeds PLAN-PR-008's D1**: "the checker crashed" is a barrier
  terminal state that D1's population must enumerate, and it is *not* a bot-refusal state.
- ⛔ **PLAN-PR-008 and PLAN-PR-009 both edit `branch-cleanup.md` and both reach the merge path.
  Sequence, never pair.**
- **PLAN-PR-008 sequences behind WS-01's PLAN-PR-007.** A false `absent` and a true `absent` are
  indistinguishable at the barrier, so the `stale` taxonomy member is an *input* to the deadlock work.
- **PLAN-PR-009 sequences behind `truthful-signals` PLAN-115** (launched, retained there) — same
  `tools-integration-ci` pr verb group. That epic reports its landing here; **name that PR when
  retiring the deferral**, per the epic's named-PR deferral convention.
- ⚠ **`truthful-signals` PLAN-113 and PLAN-52 remain on `phase-6-finalize` in that epic.** PLAN-113 is
  retained **deliberately** — `code-intelligence-substrate` already recorded the PLAN-113 → PLAN-121
  sequencing in its own ledger as a hard constraint, so this epic must not assume it can take it.
  Re-verify by SLUG at outline.
- PLAN-PR-010 is ranked early despite low bleed: until it lands, every forwarded PR-related landing
  needs its outcome attached by hand. Its previously-recorded PLAN-92 blocker is **discharged**
  (shipped `#1041`).

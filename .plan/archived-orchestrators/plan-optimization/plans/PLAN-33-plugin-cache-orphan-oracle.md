# PLAN-33: Session-Binding Store — Caller and Conflict Semantics

epic: plan-optimization
workstream: WS-10

> Staged plan spec. Surfaced 2026-07-21 by an orchestrator cleanup sweep.
> **Scope reduced the same day**: the plugin-cache half was absorbed into PLAN-34 once the
> operator directed that `marshall-steward upgrade` own the cache lifecycle. Keeping both here
> would have put two plans in `upgrade.py`/`upgrade-flow.md` simultaneously — adjacent, not
> disjoint. This plan now owns exactly one cache: the session-binding store.

## Objective

`~/.cache/plan-marshall/sessions/` accumulates one `active-plan` slot per Claude session and
nothing ever removes them. Measured 2026-07-21:

```
scanned:        571
stale_count:    566   (99% — plan no longer live)
conflict_count:  88   (one plan_id bound to several sessions)
gc_removed:       0   (the GC had never run)
```

A working GC already exists — `platform-runtime session doctor --fix`. It was run during the
cleanup and behaved correctly: **566 slots removed**, re-run reports `scanned: 5, stale: 0,
conflicts: 0`, and **all five live plan bindings survived** (verified individually, including
`68da809a-… → domain-conditional-loading-concept` read back after the sweep).

**So the logic is not the problem — the absence of a caller is.** A GC reachable only by a human
remembering to run a doctor verb is indistinguishable from no GC. That is the same shape as the
plugin cache's unrun sweep (now PLAN-34), which is what makes this a pattern rather than an
incident: **n=2 caches whose GC exists, is documented, works when invoked, and never runs.**

## ⚠ What is settled vs open

- **SETTLED, do not re-derive**: the counts above, that `session doctor --fix` works, and that
  it preserves live bindings. The sweep has already been performed; this plan does not need to
  re-run or re-validate it.
- **OPEN**: where the caller belongs, and what the conflict semantics should be (below).

## Deliverables

1. **Give the session-store GC an automatic caller.** The sweep must run without a human
   invoking a doctor verb. Decide the site — a finalize step, a steward stage, or a
   session-open hook — and wire it. **Reuse `session doctor --fix`; do NOT write a second GC.**
   The call must report what it removed so a silent no-op is distinguishable from a clean run;
   that indistinguishability is exactly how 566 stale slots accumulated unnoticed.
2. **Settle conflict semantics — the unresolved correctness question.** 88 slots had one
   `plan_id` bound to multiple sessions. This is not cosmetic: `close` and `archive` call
   `session resolve-plan` to choose which plan-scoped title to restore, so a multiply-bound plan
   makes that resolution ambiguous. The 07-21 sweep cleared the conflicts only *incidentally*
   (they were nearly all stale) — **nothing prevents recurrence among live sessions**, which is
   the case that actually matters. Decide whether `bind`'s documented last-driven-wins is
   correct, or whether `resolve-plan` must fail closed on ambiguity (ADR-009 precedent), and
   encode the choice with a regression covering two live sessions bound to one plan.
3. **Prune empty session directories.** 26 directories remained after the sweep while only 5
   carried an `active-plan` slot — the GC removes the slot file but leaves the parent directory.
   Minor, but it makes `scanned` counts misleading and the store's on-disk size unbounded in
   inodes.

Three deliverables, well under the split guard. D2 is the only one requiring design judgment.

## Expected Surface

- `platform-runtime/scripts/session_binding.py` (`_iter_slots`, `_plan_is_live`, `bind`,
  `resolve_plan`, the doctor/`--fix` path) — **read-mostly**: the logic works
- `platform-runtime/scripts/platform_runtime.py` (`session doctor` verb)
- wherever D1 wires the caller (finalize step / steward stage / session hook)
- tests: caller fires and reports; **two live sessions bound to one plan** (D2); empty-dir prune

## Dependencies and Sequencing

- Depends on: none.
- **Scope handed to PLAN-34**: the plugin-cache orphan oracle, retention policy, and cache
  fetch/prune. If D1 concludes the session-store caller belongs in `marshall-steward upgrade`,
  this plan becomes **ADJACENT to PLAN-34** on `upgrade.py`/`upgrade-flow.md` — check PLAN-34's
  state before emitting, and sequence behind it if it is live. Choosing a different call site
  (session hook, finalize step) keeps them disjoint.
- Overlaps with: none in flight (PLAN-25, PLAN-29, PLAN-31, PLAN-32 all elsewhere). ⚠ PLAN-29
  touches `platform-runtime` — confirm at outline that it is not editing `session_binding.py`;
  its declared surface is the Runtime ABC and `targets/`, but PLAN-26 (#964) did touch
  `session_binding.py`, so the region is not untouched historically.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-33-plugin-cache-orphan-oracle.md"

SETTLED CONTEXT — do NOT re-derive or re-run: on 2026-07-21 the session-binding store at ~/.cache/plan-marshall/sessions/ held 571 slots, of which 566 were stale and 88 were conflicts, with gc_removed 0 because the GC had never been invoked. It was swept via `platform-runtime session doctor --fix` (566 removed); a re-run now reports scanned:5 stale:0 conflicts:0, and all five live plan bindings survived and were verified individually. The GC logic is CORRECT and needs no rework. What is missing is an automatic CALLER — a GC reachable only by a human running a doctor verb is indistinguishable from no GC. Deliverable 1 wires that caller reusing `session doctor --fix`; do not write a second GC. Deliverable 2 is the real design question and is UNRESOLVED: 88 slots had one plan_id bound to several sessions, and close/archive use `session resolve-plan` to pick which plan-scoped title to restore, so a multiply-bound plan is ambiguous; the sweep cleared those only incidentally because they were nearly all stale, and nothing prevents recurrence among LIVE sessions, which is the case that matters — decide whether bind's documented last-driven-wins is correct or whether resolve-plan must fail closed on ambiguity, and pin it with a regression covering two live sessions bound to one plan. Deliverable 3 prunes empty session directories: 26 dirs remained after the sweep while only 5 carried an active-plan slot, because the GC removes the slot file but not the parent. SEQUENCING: the plugin-cache half of this work was moved to PLAN-34 (steward owns the cache lifecycle). If you conclude the caller belongs in marshall-steward upgrade, this plan becomes adjacent to PLAN-34 on upgrade.py/upgrade-flow.md — flag it rather than editing both concurrently.
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-33.md is recorded}

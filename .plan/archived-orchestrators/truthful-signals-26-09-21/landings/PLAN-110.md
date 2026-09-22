# Landing Analysis: PLAN-110 — Build tests do not neutralize daemon routing

epic: truthful-signals
workstream: WS-01
pr: [#1061](https://github.com/cuioss/plan-marshall/pull/1061) — merged (`c259f5c74`)

⚠ **This landing was NOT reported by the operator.** It was found by the orchestrator's
landed-but-unreconciled scan against `origin/main`. Recorded because an unreported landing is exactly
the residue this epic exists to catch.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| Fixture-scoped daemon-routing neutralization | shipped-as-specified | PR #1061, merged; branch and worktree removed |
| Deterministic re-runnable population census | shipped-added-value | Derives the affected call-site set **from the AST**, not from filename or token matching |

⭐ **Census: 661 call sites examined, 0 currently affected — and the plan said plainly why that zero
is not reassuring.** *"The zero is a property of current stub discipline, not of the structure — 28
of 41 relevant call sites sit at `execution_mode='auto'`, so the population is one un-stubbed sibling
away from being non-zero again. The census script is the durable deliverable; the number it currently
prints is not."*

That is the correct handling of a zero, and it is the exact discipline this epic keeps having to
enforce elsewhere. **A count of 0 from a derived population is a measurement; a count of 0 from an
unexamined population is an assumption.**

## Metrics and Anomalies

- `signal_qgate_pending_count`: 0 · `signal_automated_review_count`: 1 ·
  `signal_script_failure_clusters_count`: 1
- ⛔ **Every build in this plan was forced `--execution-mode in_process`** — a daemon-routed build
  false-greens this plan's own suite. **Any follow-up plan touching the routing seam inherits that
  constraint.**

## Routing and Merge Behavior

⛔ **Review coverage thin — one substantive review out of three configured bots:**

- `pr-agent` (required) — participated, one "no major issues detected" guide
- `sourcery` — explicitly refused on hard quota
- `coderabbit` — **check completed but produced NO comment credited as review evidence**

⭐ The plan itself invoked the standing rule correctly: *"a completed check is not a review."* This
is a direct instance of PLAN-116 Defect D, and the coderabbit case is a **fourth** distinct shape —
check green, no comment at all.

⭐ **Its landing message stated its own epistemic position correctly**: *"Merge state at emission:
NOT yet merged — the epic must reconcile the landing after the merge completes."* Written by the same
pre-merge `lessons-capture` step that produced PLAN-112's incorrect "PR #1055, merged." **Same
structural constraint, opposite honesty** — which proves the ordering defect is survivable by
convention, and that the correct form already exists in the codebase.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` = 1061; `landing` = landings/PLAN-110.md;
      `plan_marshall_plan_id` = build-tests-do-not-neutralize-daemon-routing
- [x] Landing found by scan, not by report — recorded as such
- [x] Unblocks the sibling's PLAN-127 (test tree + conftest surface)

## Follow-Ups

1. ⛔ **The staged spec's central premise was STALE.** PLAN-110 claimed ~8 tests fail spuriously
   because nothing stubs the daemon routing probe. Both named modules **already** patched
   `factory._route_to_daemon` inline — landed in `aafcd1928` / PR #949, **before the spec was
   staged**. Its declared PLAN-105 dependency was also stale. ⭐ **The plan proceeded on the
   re-measured premise, not the staged one — which is the correct response, and is exactly the
   emit-time re-grounding practice this epic adopted.** Recorded as evidence that practice pays.
2. ⛔ **PLAN-105 is superseded WITHOUT HAVING LANDED, and its gap is LIVE** — the dispatched-leaf
   search-primitive gap bit this plan's own phase-5 leaf directly. **The plan recommends re-queuing
   it.** Open question for the operator.
3. **Independent FOURTH observation of the `architecture-refresh` dual classification** — found in
   passing, not fixed, "needs an owner". Now owned: PLAN-113 D5a/D5d here, PLAN-121 in the sibling.
4. **Post-merge PR revisit obligation on #1061** — the plan flagged that the merge is likely to
   outrun any late review.

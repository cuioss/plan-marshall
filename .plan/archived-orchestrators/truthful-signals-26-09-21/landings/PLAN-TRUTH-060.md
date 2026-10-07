# Landing Analysis: PLAN-TRUTH-060 — the daemon baseline interpreter is unregistrable and its safe default unreachable

epic: truthful-signals
workstream: WS-01
pr: #1122 (`263f216d9`, on `origin/main`)

> Reconciled at the pre-restart check, not from an operator paste — the landing was found by
> corroborating `origin/main` while verifying restart safety. Recorded as a lead-turned-fact.

## Deliverable Fidelity vs Spec

Corroborated against the merge commit body and the file stats of `263f216d9`.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| Make the permissive default reachable | shipped-as-specified | `marshalld.py` — `Daemon.__init__` stores `baseline_interpreter` **verbatim** instead of `baseline_interpreter or sys.executable`, so with `build_daemon` passing nothing the verifier reaches its canonical `python3`/`python` basename set. |
| Settle the "registered baseline" claim | shipped-modified — **the claim was REFUTED, not implemented** | `_marshalld_verifier.py` — the module docstring, `_interpreter_ok` and `verify_submit` were **corrected**: no registration surface ever carried an interpreter field. ⭐ The spec assumed a registration field existed and was unreachable; the truth is it never existed. |

⭐ **The plan's own framing was half wrong and the landing says so.** This epic's title asserted the
baseline was *"unregistrable"*; the fix establishes there was **nothing to register** — `command[0]` is
checked daemon-wide as an argv shape, not against a per-project registration. **A defect whose remedy
is a documentation correction rather than a code change is still a real defect**, and this one had a
code half too (the `or sys.executable` substitution).

## Deliverables — COMPLETED FROM THE FINALIZE REPORT (2026-08-08, after the initial reconciliation)

The initial record was written from `origin/main` alone and saw 2 deliverables in the commit body. The
finalize report names **4/4**, and the two it adds are the ones that matter to this epic:

| # | Deliverable | Note |
|---|-------------|------|
| 1 | Remove the `sys.executable` substitution in `Daemon.__init__` | as recorded |
| 2 | Correct the "registered baseline" claim across docs + docstrings | as recorded |
| 3 | **Matched positive/negative control tests** | ⭐ the negative control is what makes the fix falsifiable |
| 4 | **Live re-grounding measurement reproducing the defect FIRST** | ⭐⭐ the plan reproduced the defect before fixing it — the discipline this epic exists to enforce, actually applied |

⭐ **Recording the correction, not just the correction's result**: a landing record built from a squash
commit body under-counts deliverables, because a squash flattens them. **A commit body is a summary of
a plan, not an enumeration of it.**

⚠ **Two operator decisions shaped the outcome and are NOT in the spec**: the `uv.lock` refresh (real
stale repo state, not churn — settling the earlier `uv.lock +176` lead in the *dependency-change*
direction), and an **S1.2 narrowing that SUPERSEDED settled decision D1** — `_interpreter_ok`'s no-pin
branch now requires a bare `python3`/`python` with **no path separator**, constraining *location* as
well as *name*. That surfaced a latent test-fixture assumption (`sys.executable` in the idempotent-submit
acceptance test), fixed to the production-shaped bare name. ⛔ **A settled decision was superseded
mid-run; the spec no longer describes what shipped.**

## Metrics and Anomalies

- 3h35m worked / 4.6M tokens. 23 finalize steps done, 1 skipped (`adr-propose`, lane off in manifest
  step-params — an explicit configuration, not a failure).
- `pre-push-quality-gate`: 1 bundle + whole-tree gates green, **17,791 tests**.
- Rebased onto **17 upstream commits** at sync-baseline — a long-lived branch.

## Routing and Merge Behavior

- Merged to `origin/main` as `263f216d9`; a `gh-readonly-queue/main/pr-1122-…` ref is present, so it
  went through the merge queue.
- ⛔⛔ **REVIEW COVERAGE WAS THIN, AND THE BARRIER PASSED ANYWAY — reported by the run, and it is the
  sharpest thing in this landing.** `automatic-review` recorded *"quorum met (participation only)"*:
  **CodeRabbit never reviewed any HEAD at all (rate-limited)**, and **pr-agent and sourcery both scored
  `participated_but_empty`.** The required set for this project is **`pr-agent` alone** ⇒ **quorum was
  satisfied by a bot that filed nothing.**
  ⭐ **This is exactly the shortfall `PLAN-TRUTH-061` shipped a disclosure for, occurring on a later
  PR** — and it is the concrete form of the standing caveat that *a required set of exactly one has no
  redundancy*. ⚠ **`participated_but_empty` is a participation state, not a review verdict**; the
  barrier is explicitly not a review-quality gate, and the operator accepted the thinness knowingly.
  ⇒ **Routed to `review-apparatus`** — PR/review subject wins the routing test outright.
- `review-retrospective` returned **`verdict unmeasurable`** — consistent with the above: there was no
  review substance to compare.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped `1122`
- [x] row `landing` stamped `landings/PLAN-TRUTH-060.md`
- [x] The `manage-build-server` cache-vs-source divergence found at the pre-restart content check is
      explained by this landing — see Follow-Ups.

## Follow-Ups

**1. This landing explains the ONE divergent file in the pre-restart content check.** The pinned cache
`0.1.1326` matched source on **359 of 360** `.md` files; the single mismatch was
`manage-build-server/SKILL.md`, where **source is ahead** — carrying exactly this PR's corrected
interpreter-contract prose. ⇒ **The cache is one sync behind for this file**, and a restart would seat
the pre-#1122 build-server SKILL body. ⭐ **This is the content conjunct CIS asked for (`-024`) earning
its place on its first use** — the stamp-based checks all passed while a real staleness sat in one file.

**2. The `wrong_interpreter` Open Defect is now addressed at the daemon.** ⚠ Do **not** retire the
ledger's related entries on this landing alone: the epic recorded that the 08-07 `upgrade` *masked* the
fault by relaunching under a `python3`-basenamed interpreter, so **a green build is not evidence the
fix works.** The discriminating test is a daemon launched under a non-`python3` basename.

**3. `PLAN-TRUTH-005`** (marshalld self-reload on version signal) shares `manage-build-server`. It is
staged and now **unblocked on this surface** — re-ground it against `263f216d9` before emitting.

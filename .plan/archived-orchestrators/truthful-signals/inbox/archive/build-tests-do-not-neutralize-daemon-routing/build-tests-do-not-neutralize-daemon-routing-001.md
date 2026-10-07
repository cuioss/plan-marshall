envelope_version=1
sender_type=plan
sender_id=build-tests-do-not-neutralize-daemon-routing
epic=truthful-signals
kind=landing
created=2026-07-29T17:00:55Z

## What landed

**Plan**: `build-tests-do-not-neutralize-daemon-routing` (PLAN-110, epic `truthful-signals`)
**PR**: #1061 — `test(build-execute): fixture-scope daemon-routing neutralization`
**Branch**: `feature/build-tests-do-not-neutralize-daemon-routing`
**HEAD at emission**: `59e213f0a4b2490515f84ba57064873249943b48`
**Merge state at emission**: NOT yet merged — the epic must reconcile the landing after the merge completes.

## Shipped

Fixture-scoped daemon-routing neutralization for the build-factory test surface, plus a deterministic, re-runnable population census that derives the affected-call-site set from the AST rather than from filename or token matching.

Final census: **661 call sites examined, 0 currently affected**. The zero is a property of current stub discipline, not of the structure — 28 of 41 relevant call sites sit at `execution_mode='auto'`, so the population is one un-stubbed sibling away from being non-zero again. The census script is the durable deliverable; the number it currently prints is not.

## Residue the epic should track

1. **The staged spec's central premise was stale.** PLAN-110 claimed ~8 tests fail spuriously because nothing stubs the daemon routing probe. Both named modules **already** patched `factory._route_to_daemon` inline — landed in `aafcd1928` / PR #949, *before* the spec was staged. The spec's declared PLAN-105 dependency was also stale (the ledger's PLAN-105 is closed-superseded and unrelated to daemon routing). The plan proceeded on the re-measured premise, not the staged one.

2. **PLAN-105 is superseded WITHOUT HAVING LANDED, and its gap is live.** The dispatched-leaf search-primitive gap that PLAN-105 described bit this plan's phase-5 leaf directly. **Recommend re-queuing it.**

3. **Doc-contract drift found in passing, NOT fixed (out of scope):** `architecture-refresh.md` declares itself INLINE (its Tier-1 prompt needs `AskUserQuestion`) while `dispatch-inline-split.md` rosters it under Dispatched steps. Two source-of-truth docs disagree about the same step. Needs an owner.

4. **Review coverage on #1061 was thin — do not read the green finalize as three-way confirmation.** One substantive automated review out of three configured bots:
   - `pr-agent` (required): participated, one "no major issues detected" guide.
   - `sourcery`: explicitly refused on hard quota.
   - `coderabbit`: check completed but produced **no comment** credited as review evidence.

   Per the standing rule that `ci pr comments` is necessary but not sufficient — a completed check is not a review. This landing carries a **post-merge PR revisit obligation**: the merge is likely to outrun any late review.

5. **Every build in this plan was forced `--execution-mode in_process`.** A daemon-routed build false-greens this plan's own suite (see the separate candidate-lesson). Any follow-up plan touching the routing seam inherits that constraint.

## Signals at finalize

- `signal_qgate_pending_count`: 0
- `signal_automated_review_count`: 1
- `signal_script_failure_clusters_count`: 1

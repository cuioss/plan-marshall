# Landing: PLAN-22 lock-staleness-scope-guard

- **PR:** #959 (`5f67782d6 fix(manage-locks): fail-closed staleness inference on manual release`) — merged to main
- **Workstream:** WS-10 pipeline-integrity-hardening
- **Granularity:** full ship
- **Verified against ground truth:** commit on main + `git show --stat` corroborates every claimed deliverable file (orchestrator, 2026-07-21).

## Deliverable fidelity vs spec

| Deliverable | Shipped | Verdict |
|-------------|---------|---------|
| D1 — staleness queries main-checkout store; unresolvable/worktree-scoped → `unknown`, never `stale`; release refuses on `unknown` | `_locks_core.holder_staleness(holder)` three-valued verdict (fresh/stale/unknown); `merge_lock release --require-stale` refuses fail-closed on fresh/unknown, removes only on stale via observed-file eviction arbitration (no blind unlink — closes a TOCTOU window); `check` surfaces a `staleness` field. Co-located unit tests (`test_locks_core.py`, `test_merge_lock_conditional_release.py`). | ✅ as specified |
| D2 — enumerate CWD-keyed store-resolution call sites, fix-or-justify | `standards/cwd-keyed-store-resolution-audit.md` enumeration; fixed `manage-status` `cmd_list` (`_status_query.py`) + `git-workflow` `worktree-list` to propagate a scope qualifier; justified the already-sound `manage-lessons` resolver as no-change | ✅ as specified |
| D3 — encode invariant, tie to ADR-009, retire lesson | `standards/scope-limited-negative-is-unknown.md` invariant tied to ADR-009 (the `...fails_closed_with_an_explicit_unknown_state.adoc` update; no new ADR); #948 incident watch retired | ✅ as specified |
| Split from D1 — #948 sibling-worktree regression | `test_merge_lock_staleness_sibling_worktree.py` — cwd-independence regression driving real main-anchored resolution | ✅ |

Diff: 13 files, +1278/-14 — 4 test files, 2 new standards docs, ADR-009 adoc, core `_locks_core.py`/`merge_lock.py`, `manage-status` + `git-workflow` D2 fixes.

## Routing / merge behavior

- **Light lane self-escalated to deep** — correct: D2's codebase-wide CWD-keyed enumeration exceeded the bounded light-lane read set.
- **Review barrier:** 2 gemini comments were genuine on-theme fail-closed hardening (catch `OSError` in `holder_staleness`; normalize a null scope) — applied inline, verified, re-pushed. Sourcery rate-limit notice accepted (noise). CodeRabbit surfaced a **phantom FAILURE with no check-run** — dispositioned via `merge_state=unstable` (not `blocked`) as non-required; merge queue merged on the green `verify / conclusion`.
- **Gates:** all green throughout; Sonar 0 new-code issues; security-audit 0 findings.
- Post-merge: plugin cache synced (10 bundles → 0.1.1170), on-main executor regenerated.

## Reconciliation actions

- Queue: PLAN-22 → shipped, pr=959.
- **Watch retired:** "merge-lock staleness judged from a worktree-scoped store" (#948 incident) — now enforced-in-code (fail-closed `unknown`). The generalized CWD-keyed hazard is closed by the D2 audit + D3 invariant.
- Inverse-of-PLAN-15 relationship confirmed: #940 hardened the auto-reclaim path; #959 covers the manual-release path.

## New leads surfaced (folded, not lost)

- **New lesson:** completeness-guard should distinguish a *structurally-absent* bot from an *in-progress* one — a refinement of PLAN-21's D2 completeness guard (shipped #957). Recorded as a WS-10 watch (candidate fold into a PLAN-21 follow-up or PLAN-29's review-barrier neighborhood).
- **Architecture hint:** Sonar `project_key` lives in `marshal.json`, not with credentials (informational).

# Landing Analysis: PLAN-69 — Executor version split (marker-aware vs marker-blind resolvers)

epic: truthful-signals
workstream: WS-01
pr: #1013 (https://github.com/cuioss/plan-marshall/pull/1013) — main at `144d6848`

> Landing record. Claims verified against shipped source at HEAD and the live plugin cache, not the
> finalize narrative.

## Deliverable Fidelity vs Spec

2/2 shipped; 20/20 finalize steps; 12672 tests green.

| Deliverable | Verdict | Evidence |
|---|---|---|
| D1 — single-source the selector, route every call site, add Guard 4 | shipped-as-specified | `select_live_version_dir` is the sole authority; `find_bundles` / `resolve_bundle_path` / `collect_script_dirs` now supply only an eligibility predicate. `.orphaned_at` retained but **reconciled on read**, so a marker on a retention-pinned dir can no longer suppress it. Guard 4 at `generate_executor.py:952` refuses to write an executor whose emitted paths span >1 version dir per bundle, leaving any prior executor byte-identical |
| D2 — end-to-end version-split regression coverage | shipped-as-specified | version-split regression suite |
| *(added)* correct the refuted invariant in `provisioning-fail-closed-audit.md` | shipped-additional, sanctioned | a documented claim that no longer held — corrected in the same change rather than left to drift |

**Guard 4's failure mode is the right one**: it refuses to emit and leaves the previous executor
byte-identical, rather than emitting a best-effort mixed one. That is fail-closed in the shape ADR-009
asks for, on the surface that previously produced a *downgraded* executor while `preflight` reported
`fresh`.

## ⭐ The finding that matters: the anti-vacuous-guard fix SHIPPED A NEW VACUOUS GUARD

`_split_bundle_version` originally scanned for the **first version-shaped path segment**, so a
version-shaped **ancestor directory** above the cache root, or a bundle whose own name starts with
`N.N` — *a naming convention this repo documents and pins in a test* — collapsed to the wrong key and
made **Guard 4 silently non-firing**.

- OBSERVED at HEAD — the shipped fix anchors on the known cache root instead
  (`generate_executor.py:706-730`): relativize against `base_path`, then *"the first two segments ARE
  the bundle and its version dir"*. The docstring now names both mis-splitting inputs explicitly and
  states the consequence: *"Either returns the wrong key and silently defeats the provenance guard."*
- **A plan whose entire purpose was to make a false-green structurally impossible introduced a fresh
  false-green inside its own guard.** That is the epic's flagship archetype reproducing *inside a fix
  for the archetype* — the sharpest instance recorded so far.

**How it was caught is the actionable part.** `pre-submission-self-review` ran **13 checks over 50
candidates and reported clean**; `finalize-step-simplify` reported **0 findings**. **Two independent
bots caught it.** The in-house structural review is precisely the machinery that should own
"a newly added guard's predicate is unreachable" — it reported clean on a live instance. Filed as
lesson `2026-07-27-08-001` and **staged as PLAN-81** (below).

## Metrics and Anomalies

- 3h35m worked / 3.5M tokens; deploy-target emitted 1118 files at **0.1.1224**; sync succeeded and the
  executor was regenerated.
- **Review worked properly on this PR** — 3 comments → fixed → **0 on re-review**, 2 reviewers
  compared in the retrospective. A welcome contrast to #1014's 0-of-3.
- Anomaly — **a phase-5 leaf SELF-CERTIFIED the Step 11c exit-verify gate rather than yielding it.**
  Its reasoning held and CI independently confirmed the tree, so no harm landed; but this is the same
  self-certification pattern this epic targets, and *"it was right this time"* is not a control.
  Recorded as a watch.

## Routing and Merge Behavior

- Merged via queue; worktree removed; main clean at `144d6848`.
- Surface collisions: none. PLAN-69 ran concurrently with PLAN-70/54/55 inside `tools-script-executor`.

## Reconciliation Actions

- [x] status.json — PLAN-69 `launched` → `shipped`, `pr=1013`, `landing=landings/PLAN-69.md`
- [x] epic.md reconciled; resume_anchor + START-HERE regenerated
- [x] **PLAN-81 staged** for the self-review gap
- [x] PR-Agent quality read corrected to n=2 mixed; **behavioural proof genuinely DISCHARGED**
- [x] **PLAN-75's D0 blocker cleared** (below)

## Follow-Ups

### ✅ PLAN-75's D0 gate is now runnable — the stale-cache cause is gone

OBSERVED — the live cache `0.1.1224` now carries `order: 61` **and** `mutates_source: true` for
`finalize-step-preference-emitter`, matching source. The `0.1.1194` pin that declared `order: 80` is
no longer what a session loads. **PLAN-75's D0 can now re-compose against a clean cache and settle
Defect B.** Expectation, stated in advance so the result is falsifiable: the step should sort to its
61 slot and Defect B should close, leaving Defect A alone.

### ✅ PR-Agent: behavioural proof DISCHARGED, and the quality read corrected

**Its finding here was valid and sharper than CodeRabbit's on the same defect** — it named the
concrete in-repo trigger and the silent-bypass consequence. Two consequences:

1. **The behavioural proof is genuinely discharged this time.** Unlike #1012 (where "ran" ≠
   "published") and #1014 (silent behind a green check), PR-Agent **published a valid finding on
   ordinary traffic**. That is the observed artifact I said was owed.
2. **The "low signal" read is withdrawn.** Prior experience was a single false positive (API-Sheriff
   #103). It is now **n=2 and mixed**, not settled — and on this instance it *outperformed* CodeRabbit.
   Do not carry "PR-Agent is low signal" forward as an established fact.

### ⚠ Two lessons filed for defects this plan surfaced but did not own — one needs verification

- `2026-07-26-16-001` — `get-module-context` treats a normal phase-3 state as a failure. Ordinary
  false-positive; no plan staged.
- `2026-07-26-20-002` — **test-authored ledger entries can satisfy the production freshness gate.**
  ⚠ **Strong theme fit and potentially serious** — a gate that a test fixture can satisfy is a
  false-green channel by construction. **NOT staged**: the claim is a lesson title, unverified
  first-party, and this epic has just been burned twice by staging on unverified premises. **Verify
  the mechanism at its named gate before staging**; if it holds, it is a plan in its own right.

### Watch — phase-5 self-certification of an exit-verify gate

A leaf certified its own Step 11c gate instead of yielding. No harm this time. Recorded because it is
the epic's own subject matter appearing in its own execution machinery; if it recurs, it is a plan.

### Operator-owed

`marshal.json` provisioning stamp remains stale (`0.1.1192` vs installed `0.1.1224`) — advisory since
finalize entry. `/marshall-steward` reconciles it.

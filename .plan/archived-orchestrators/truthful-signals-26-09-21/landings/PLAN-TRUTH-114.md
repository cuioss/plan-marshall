# Landing analysis — PLAN-TRUTH-114

**Plan:** `move-back-guard-resolves-through-its-own-tree` · **WS-01**
**PR:** [#1361](https://github.com/cuioss/plan-marshall/pull/1361) · **merged** as `5f972ac15`
**Analyzed:** 2026-08-27 · landing message `-009` (`revision: 1`, amended) · `landing-check: complete: true`

## Corroboration

| Claim | Verdict | Evidence |
|---|---|---|
| PR #1361 merged | **corroborated** | `ci pr view` → `state: merged` |
| `5f972ac15` is main | **corroborated** | `git log origin/main -1` |
| Landing payload complete | **corroborated** | `landing-check` → `complete: true`, `missing_keys` empty |
| `scope_creep_check` inert — readers/tests, no writer | **corroborated, first-party** | see below |

⭐ **The landing arrived AMENDED (`revision: 1`)** — the sanctioned `inbox amend` path, not a successor
message and not a silent edit. First use of that surface observed in this epic.

## Deliverable fidelity

8 of 8 shipped. 22 of 23 finalize steps done, 1 correctly `skipped` (`era-stamp-fill`, no sentinel owed).
19 commits, 18 files, +2,741/−116, 2 loop-backs of 3, **0 pending findings at close**.

⭐⭐ **`total_billing_weighted=130855281` is carried as a fact.** D-098-d recorded that billing-weighted
had no schema key one landing ago; this landing carries it. **That half of D-098-d is closed by
observation** — the typed-facts half (`record-metrics` writing no `facts` sub-dict) still needs checking.

## ⭐⭐ My own HYPOTHESIS was refuted, in the direction that made the defect worse

`-114`'s spec carried: *"`git worktree remove` issued with `-C {worktree}` against `{worktree}` itself
fails rather than succeeding, which would mean the guard's fail-open is caught downstream."* **Probed
and REFUTED: rc=0, tree destroyed, in 4/4 geometries — with and without `--force`, cwd inside and
outside.** ⇒ **There was no downstream backstop; the fail-open guard stood alone.**

⛔ **Three documents asserted the opposite** (*"git refuses to operate on a worktree that is a shell's
cwd"*), all removed in one revision. ⚠ **One of those documents is what this orchestrator quoted to the
operator as reassurance while staging this plan.** The spec's own guard clause held — it said a
destructive authorization depending on a downstream tool's incidental refusal is not a guard — but the
reassurance was still passed on. **Record it: a doc-sourced comfort is not a probe.**

## ⛔ The headline hand-off — corroborated first-party and worse than reported

**`scope_creep_check` is structurally inert on EVERY plan.** A repo-wide sweep of `marketplace/` and
`test/` for `plan_creation_sha` returns:

| Site | Kind |
|---|---|
| `phase-5-execute/scripts/scope_creep_check.py`:205 | **reader** |
| `phase-5-execute/SKILL.md`:576 | doc |
| `test/plan-marshall/phase-5-execute/test_qgate_persist_contract.py`:73 | **test, hand-constructs the field** |
| `test/plan-marshall/phase-5-execute/test_scope_creep_could_not_look.py`:46 | **test, hand-constructs the field** |

**No writer, anywhere.** ⇒ Every plan takes the `no plan_creation_sha` branch, so **no plan has ever had
scope-creep coverage.** This plan proved it: an undeclared file escaped into the footprint and was caught
only incidentally by `baseline-reconcile`.

⭐⭐ **And the tests hand-construct the key — the SAME archetype as D-098-b, in two consecutive
landings.** A green suite over a shape production never emits. There is even a test named
`test_scope_creep_could_not_look.py` asserting the could-not-look branch — **the only branch that ever
executes in production.**

## Reconciliation actions

- Queue row `PLAN-TRUTH-114` → `shipped`; `pr` = 1361; `landing` = this file.
- Seven handed-forward defects recorded as epic Open Defects D-114-i…D-114-o.
- `scope_creep_check` folded to `PLAN-TRUTH-101` sub-shape C (a declared consumer whose producer does
  not exist) — its third member.
- 8 candidate-lessons drained: 5 folded, 2 into a new spec, 1 routed out.
- Sourcery/pr-agent coverage → `review-apparatus`; `search --content` count defect and the 6-finalize
  instrumentation gap → `code-intelligence-substrate`.

## Parallelization

`-114` ran concurrently with `-098` under the R=2 override, across the glob blind spot. **Both landed;
no collision materialised in either landing.** ⇒ The override is recorded as successful — and still not
a licence to read glob-silence as disjointness (`-113`).

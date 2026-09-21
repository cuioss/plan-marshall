# Plan-ID Rename Map — `truthful-signals`

Authoritative old↔new mapping for the 2026-07-30 re-issue of this epic's **staged** plans to the
epic-scoped `PLAN-TRUTH-{NNN}` form. `status.json` `plans[]` remains the machine authority; this
document exists so a reader who finds an old id in a historical artifact can resolve it.

## Why the old ids still appear, and where

⛔ **`logs/` and `inbox/archive/` were deliberately NOT rewritten.** They are append-only audit
records; rewriting them to match a later naming decision would destroy the evidence they exist to
hold. `landings/` was likewise left intact — a landing report is a record of what was true when it was
written. **This table is the resolution mechanism for all three.**

⇒ **If you find an old id, do not "fix" the historical document. Resolve it here.**

## Renamed — 18 staged plans, ordinals in `status.json` `plans[]` array order

| Old id | New id | Slug |
|---|---|---|
| PLAN-113 | **PLAN-TRUTH-001** | gates-do-not-refire-over-the-loop-back-diff |
| PLAN-97 | **PLAN-TRUTH-002** | inert-thinking-directives-in-dispatched-docs |
| PLAN-96 | **PLAN-TRUTH-003** | migration-shims-have-no-expiry |
| PLAN-85 | **PLAN-TRUTH-004** | invented-plan-scoping-flags-are-an-overgeneralized-convention |
| PLAN-58 | **PLAN-TRUTH-005** | marshalld-self-reload-on-version-signal |
| PLAN-52 | **PLAN-TRUTH-006** | baseline-reconcile-persists-merge-commit |
| PLAN-67 | **PLAN-TRUTH-007** | key-order-canonicalization-unreachable-and-false-green |
| PLAN-68 | **PLAN-TRUTH-008** | executor-preflight-stamp-not-resolution |
| PLAN-74 | **PLAN-TRUTH-009** | surface-every-knob-in-marshal-json |
| PLAN-59 | **PLAN-TRUTH-010** | fail-closed-signal-integrity |
| PLAN-63 | **PLAN-TRUTH-011** | provider-logging-path-containment |
| PLAN-107 | **PLAN-TRUTH-012** | canonical-block-diverges-from-argparse-choices |
| PLAN-108 | **PLAN-TRUTH-013** | hook-timeout-unit-confusion |
| PLAN-65 | **PLAN-TRUTH-014** | landed-residue-promotion-sweep |
| PLAN-49 | **PLAN-TRUTH-015** | rename-marshall-orchestrator-to-plan-orchestrator |
| PLAN-118 | **PLAN-TRUTH-016** | skills-carry-incident-history-as-normative-prose |
| PLAN-201 | **PLAN-TRUTH-017** | detect-artifacts-offers-a-live-audit-trail-as-safe-to-delete |
| PLAN-204 | **PLAN-TRUTH-018** | configurable-display-timezone-for-rendered-timestamps |

## Created under the new scheme — no old id exists

| New id | Slug | Origin |
|---|---|---|
| **PLAN-TRUTH-019** | build-gate-coverage-parity | The **build-gate half of the former PLAN-60**, returned by `review-apparatus` on 2026-07-30 after that epic split it and kept only the review half as its `PLAN-PR-011`. ⚠ **Not a rename** — PLAN-60's row stays `transferred` because its other half lives on elsewhere. |

Next free id: **PLAN-TRUTH-020**.

## NOT renamed, and why — the rule is per-lifecycle-state, not per-plan

⛔ **Never rename a launched or shipped plan.** A running plan's `request.md` `source_id` is a persisted
pointer to its spec path on disk, and nothing re-derives it. The same argument covers any row whose id
is already cited by an external, immutable artifact (a merged PR, a landing report).

| State | Rows | Reason the id is frozen |
|---|---|---|
| shipped (39) | PLAN-27, 41–48, 51, 53–56, 62, 66, 69, 70, 75, 79–81, 86–90, 92–94, 99, 101–103, 109–112, 114 | Cited by merged PRs and by `landings/PLAN-NN.md` |
| running (3) | PLAN-57, PLAN-202, PLAN-203 | Live `source_id` pointer to the spec path |
| launched (1) | PLAN-115 | Already handed to the lifecycle |
| superseded (1) | PLAN-105 | `landings/PLAN-105.md` closure record names it; PR #1046 closed unmerged |
| transferred (5) | PLAN-60, PLAN-100, PLAN-116, PLAN-117, PLAN-119 | Re-issued in `review-apparatus` under `PLAN-PR-{NNN}`; see the cross-epic table below. ⛔ **These five ids are PERMANENTLY SPENT — never reissue them.** The rows remain as the audit record and still occupy the ids; an earlier claim that they "return free to the 50-119 band" was false when written and is retracted (caught by `review-apparatus-005`). A reissue would create a duplicate id and `queue --transition` would silently mutate whichever row it reached first. |

## Cross-epic resolution — ids that moved on the OTHER side

Our ledger cites sibling plans. Both siblings re-scoped their ids on the same day, so these mappings
are needed to read our own older entries:

| Our reference | Now reads | Note |
|---|---|---|
| `code-intelligence-substrate` PLAN-03 `content-search-seam` | **PLAN-CIS-001** | Owns the seam that superseded our PLAN-105 |
| `code-intelligence-substrate` PLAN-121 | **PLAN-CIS-011** | ⛔ Carries the hard constraint that **our PLAN-TRUTH-001 lands first**. The ids moved on both sides; the constraint did not. |
| `code-intelligence-substrate` PLAN-13 | **PLAN-CIS-009** | Owns the doc half of the "11 accepted / 6 documented" item — do not re-file it here |
| our PLAN-116 (transferred) | **their PLAN-PR-001, -002, -005, -006, -007** | ⚠ **Split into FIVE.** Its Defect A and Defect B duplicated two specs `review-apparatus` had already staged — found only by reading the spec, not the summary. |
| our PLAN-119 (transferred) | **their PLAN-PR-008** | Still carries the operator-owed accepted-coverage-gap decision at D3 |
| our PLAN-117 (transferred) | **their PLAN-PR-009** | Sequences behind our PLAN-115; **they need its PR number** |
| our PLAN-100 (transferred) | **their PLAN-PR-010** | Ranked 3rd of 11 there; its stale PLAN-92 blocker was discharged on their side |
| our PLAN-60 (transferred) | **their PLAN-PR-011** + our **PLAN-TRUTH-019** | Split: review half theirs, build-gate half returned to us |

## Verification performed

The rename was verified against the executor rather than read from a doc:

- `inbox detect` on the new pointers returns `orchestrated: true` / `detection: orchestrated`.
- ⛔ The **lowercase** probe `plan-truth-018-…` returns `detection: unrecognised_id` — the grammar is
  `PLAN-{SLUG}-{DIGITS}` with `{SLUG}` = 2–8 **UPPERCASE** alphanumerics. A lowercase token silently
  detaches the plan from its epic, so it writes **no inbox message at finalize**.
- Old ids return `plan_not_found` from `queue --transition`, confirming the queue no longer resolves them.
- The `plans[]` rewrite was diffed old→new: **68 rows out, 67 in plus 1 added, no row lost**, and every
  shipped / running / launched / superseded / transferred row byte-identical.

## One correction this rename surfaced

⭐ **PLAN-105 was carrying `status: staged` while being closed-superseded**, with an unstamped `landing`
field, and it was therefore offered as an emit candidate earlier the same day. It was corrected to
`superseded` with its `landing` and `pr` (#1046, closed unmerged) stamped during this pass. **The rename
found it because renaming forces you to enumerate what you actually have** — a queue read had walked
past it repeatedly.

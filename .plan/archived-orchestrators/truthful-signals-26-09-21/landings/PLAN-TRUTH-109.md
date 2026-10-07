# Landing — PLAN-TRUTH-109 (PR #1369)

**Plan**: `findings-read-absent-plan-dir-returns-clean-zero`
**PR**: #1369 · **merge commit**: `09f92b5e8` · **state**: merged
**Source**: reconciled in two passes — first from PR state alone (the report had not been supplied), then enriched from the operator's landing report. Every claim below that the report asserts was re-checked first-party before being recorded.

## Deliverable fidelity

3/3 shipped. The plan's premise was measured, not assumed: **four live plans reported four clean zeros over 178 real findings** because an absent findings store was indistinguishable from an empty one. D1 routed every findings operation through one explicit store handle; D2 added the matched control and swept the tests pinning the old contract; D3 extended the pre-commit freshness gate to discriminate build scope rather than notation alone.

⭐ D2's shape is the one worth keeping: a **matched control** plus a sweep for tests that *pinned the defect*. This epic's recurring finding is that a test suite passes because it encodes the broken contract; D2 treats that as the default hypothesis rather than an afterthought.

## ⛔⛔ The report's most severe claim is REFUTED — no lesson was destroyed

The report states: *"A lesson was destroyed during the run. `2026-08-27-16-001` — logged retained, now `not_found`, **no tombstone**, corpus 12 → 11. It matches a previously recorded destructive-remove instance, so **n ≥ 2**, and it's a **live data-loss path**."*

**Checked first-party. Three of those four claims are false:**

| Claim | Verdict | Evidence |
|---|---|---|
| `2026-08-27-16-001` returns `not_found` | **corroborated** | `manage-lessons get` → `error: not_found` |
| corpus 12 → 11 | **corroborated** | `manage-lessons list` → 11 |
| **no tombstone** | ⛔ **CONTRADICTED** | `.plan/local/lessons-learned/.tombstones/2026-08-27-16-001.json` exists, 757 bytes, written `2026-08-30T02:23:52Z` |
| **destructive-remove, n ≥ 2, live data-loss path** | ⛔ **CONTRADICTED** | The tombstone records a *complete, correct* retirement |

The tombstone reads:

```json
"reason": "residue promoted to automatic-review/standards/bot-participation-contract.md
           (plan a-refusal-is-recorded-as-a-refusal-the-record)",
"status": "removed",
"coverage_verdict": "completely_covered",
"covering_clause": "…/automatic-review/standards/bot-participation-contract.md -> Detecting a decline -> …"
```

⇒ **The lesson was retired correctly by a DIFFERENT plan** — `a-refusal-is-recorded-as-a-refusal-the-record` (**review-apparatus `PLAN-PR-025`**), running concurrently. Its `lessons-housekeeping` step promoted the residue into a standing skill *and then* retired the lesson with a full tombstone carrying the coverage verdict and the covering clause. **That is the designed behaviour working.** No content was lost; it lives in `bot-participation-contract.md`.

## ⭐⭐ The REAL finding — a sibling plan mutated the shared corpus under this plan's feet

The lessons corpus is **global and main-anchored**; plans are **epic-scoped and run in separate worktrees**. `-109` logged `2026-08-27-16-001` as retained, later observed it gone, and — having no visibility into a concurrently-running plan in another epic — concluded destruction with no tombstone.

⛔ **Nothing tells a plan that a sibling plan retired a lesson it was tracking**, and nothing points a plan at the tombstone that would have answered the question. Both of `-109`'s own housekeeping numbers and PR-025's are individually correct (`-109`: 1 removed / 12 retained; PR-025: 1 removed → 11); only their *interleaving* is unrepresented.

⭐ This is this epic's own theme produced by the parallelism the operator enabled on 2026-08-29: **a confident signal — "destroyed, no tombstone, live data-loss path" — that its own inputs do not support.** The plan had the means to check (the tombstone was on disk before it wrote the claim) and did not.

⚠ Folded onto **`PLAN-TRUTH-110`** as an adjacent instance; not staged as its own spec (n=1, and the class is close to what `-110` already owns). Recorded as an epic Open Defect: **cross-plan interference on the shared lessons corpus is invisible to every plan involved.**

## Reviewer coverage — the counter-example, and it is a strong one

⭐⭐⭐ **Waiting for CodeRabbit paid for itself.** The run closed `#1367` unmerged and reopened as `#1369` to recover a review, and that review produced **5 findings which 5 internal self-review passes had missed** — including **a `RuntimeError` escaping a guard whose own function documented a `(None, reason)` contract**, in *the code this plan added*, i.e. an instance of the plan's own target defect class.

⛔ **Had the run merged on the contentless quorum, it would have shipped.** That is a first-party counter-instance to any argument for dropping a reviewer on empty-output grounds, and it is routed to **`review-apparatus`** under the three-way rule.

## Process errors the run's own audits caught — both already corrected

1. **Five findings "routed to the epic" in `resolution_detail` prose with no actual inbox message.** ⭐ The plan's own diagnosis is the standing rule verbatim: *a ledger cannot see another ledger's prose*. A routing claim is only real when a message exists.
2. **`create-pr` left `pr_number: 1367` recorded after the plan landed as `#1369`.** ⭐ This is why the orchestrator stamps PR ids from **PR state**, never from the landing narrative — and it did: the queue row carries `1369`, corroborated via `ci pr view` before the report arrived.

## Metrics

26h50m wall / 9h14m worked / 7.1M tokens · 13 commits · 0 pending findings · 15 messages to the epic inbox.

## Reconciliation actions

- Row `running → shipped`; `pr: 1369`, `landing` stamped; `plan_marshall_plan_id` carried.
- `PLAN-TRUTH-091`, `-101`, `-116` lose their collision with this plan.
- ⚠ **`PLAN-TRUTH-091`'s 100/G1 claim must be re-derived** — it reads `manage-findings/SKILL.md`, inside this plan's surface, and was corroborated at `5f972ac15`, *before* this landing.
- `deploy-target` emitted **v0.1.1568**, which is the version that re-opened the registry pin gap to six.

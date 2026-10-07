# Landing — PLAN-TRUTH-113 (PR #1366)

**Plan**: `disjointness-gate-reads-declared-surface-wrong`
**PR**: #1366 · **merge commit**: `b758d5c02` · **state**: merged (corroborated first-party via `ci pr view`, head branch `feature/disjointness-gate-reads-declared-surface-wrong`)
**Source**: operator paste, corroborated against git and the CI abstraction before any ledger write.

## Deliverable fidelity

5/5 shipped, matching the staged spec's arms. The landed shape is **narrower and better than the spec asked for**: the spec framed the fix as correcting a weak reader, and the landing instead **retired the competing parse entirely** — `pm-plugin-development`'s shipped `classify_spec` was relocated to `plan-marshall:script-shared` and every consumer re-pointed at it. That is the one-reader outcome the spec's D2 hoped for, achieved by deletion rather than by reconciliation.

⭐ **The spec's own central claim is confirmed by the fix's shape.** Two live readers parsed one `## Expected Surface` section and disagreed; the WEAK one (`_expected_surface_paths`, a repo-path regex requiring a `/` and a trailing `.ext`) was the one both live consumers used. A spec the shipped classifier resolves to concrete paths therefore rendered `(no expected surface)` and passed the disjointness gate as colliding with nothing.

⭐⭐ **This orchestrator observed that defect live, twice, while the plan ran** — recorded at R133 and R138. `PLAN-TRUTH-105` contributes zero rows to `file_overlap_matches` because its Expected Surface declares directories only, and the regenerated Ordered Queue rendered `(no expected surface)` for `-105`/`-111`/`-119` while dropping `-109`'s `**` glob entries. Both are first-party corroborations of the shipped premise, made independently of the plan.

## What changed for the gate

- The absent-or-unresolvable declaration now resolves to a distinct **`indeterminate`** state rather than to a clean pass (ADR-019). ⛔ This is the correction that matters to this orchestrator: the `next` verb's disjointness test previously could not distinguish *"declared nothing"* from *"collides with nothing"*.
- The gate now publishes **which surfaces it compared and their population**, so a zero is attributable.

## Metrics and anomalies

| | |
|---|---|
| Wall / worked | 24h32m / 6h18m (n=5/6) |
| Tokens | 6,111,067 — spans populations |
| Billing | 168,227,697 |
| 6-finalize share | **16h57m wall, 14h18m idle, 91.6M billing (54.5% of the run)** |

⛔ **The idle figure is the anomaly and it is this session's own subject.** 14h18m of the 18h14m total idle sits in finalize. That is the stopping behaviour folded onto `PLAN-TRUTH-107` as instances 7–9 (R140/R141), measured here rather than reported: the plan was under an explicit unattended instruction and both finalize autonomy knobs were `true`.

## Routing and merge behaviour

Rebased onto `origin/main` over 3 upstream commits; queue-merged with the rebase deferred to the queue, corroborated after merge. No collision materialised with `-109`, which was running concurrently and landed as #1369 — the disjointness pairing (plan-orchestrator vs manage-findings) held.

⚠ **Reviewer coverage was degraded and is disclosed as such**: the final commit was reviewed by pr-agent alone — CodeRabbit quota-exhausted, Sourcery structurally refusing a diff this size. `automatic-review` reports `1 reviewed, 1 empty, 1 refused-structural`. ⛔ The pre-submission self-review was **stopped by operator choice, not satisfied** — no full-scope round returned zero. Both facts are recorded so the green is not read as a completed review.

## Reconciliation actions

- Row `running → shipped`; `pr` and `landing` stamped; `plan_marshall_plan_id` already carried.
- **`PLAN-TRUTH-100` is UNBLOCKED by this landing** — its 2-file collision was with this plan (R137). It was refused on disjointness, never on capacity, so the landing is precisely what frees it.
- `PLAN-TRUTH-099` and `PLAN-TRUTH-115` likewise lose their collision with this plan.
- 5 finalize-machinery findings carried to the epic inbox (msg 013 + 4 lessons-capture), **undrained at the time of writing**.

## Carried findings — not yet dispositioned

Three of the five are **one conflation**: a review-bot rate-limit refusal handled as review evidence at three call sites — `fffb89` counts it as a completion signal, `942346` stores it as a triageable finding, `071a67` lets its `reviewed_commit_sha` suppress the very re-review that would cure it. ⭐ That is a single mechanism with three consumers, and it belongs to the **`review-apparatus`** epic under the three-way routing rule (PR/review wins outright) — routed at drain, not here.

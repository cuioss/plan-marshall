# Landing Analysis: PLAN-CIS-027 — Graph Merge Drops Every Resolver Edge

epic: code-intelligence-substrate
workstream: WS-02
pr: #1079 — https://github.com/cuioss/plan-marshall/pull/1079

> Landing record. Every claim below was corroborated against ground truth before it was
> written: `origin/main` (`5c41364a5`), the merge commit's own diff, and — for the founding
> defect — a **live probe of the shipped command**, not the plan's success report.

## ⭐ The founding defect is CLOSED, and it was probed live

The epic's founding defect was: *29 resolver edges, zero graph edges; `impact` empty for every
module; all 12 modules both roots AND leaves.* Standing rule 2 forbids accepting the plan's own
report on this, because #1074 previously reported it closed while it was not. Probed at
`5c41364a5` in the main checkout:

| Signal | Before | Live now |
|--------|--------|----------|
| `architecture graph` `edge_count` | **0** | **24** |
| `impact --module pm-dev-java` | empty | **9 modules** |
| roots / leaves | all 12 in both | roots 2, leaves 3 |

⭐ **The 29-vs-24 gap is arithmetic, not loss.** Resolver counts are per-resolver contributions
(markdown 24 + maven 0 + python 5 = 29); the merged graph holds **24 unique edges**, of which
exactly **5 carry `["markdown", "python"]`** as producers. 29 − 5 dual-producer overlaps = 24.
The two numbers reconcile exactly, so the merge is not silently dropping a residue. **Recorded
so a future reader does not re-open 29≠24 as a defect.**

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — derive the mechanism | shipped-as-specified | `_cmd_client_query.py` § `_declared_dependencies`. ⛔ **None of the three candidate mechanisms named in the request was right** — the real cause is a presence-vs-meaning confusion: `architecture init` seeds an empty `internal_dependencies` stub into every module, and a key-membership test read all 12 as "declared with zero dependencies". |
| D2 — fix | shipped-as-specified | Only a **non-empty** list declares, at **both** precedence sources (`enriched.json` overlay and `derived.json`), through one shared helper consumed by `_build_deps_and_producers` and `_derive_edges` — so the enrichment-skip population and the discard population cannot drift. |
| D2 hardening (ADR-014, added-unplanned) | added-unplanned | `_declared_suppression_notes` appends a `declared:`-prefixed note to the **losing resolver's own report**. A declared-wins overwrite can no longer be silent. |
| D3 — correct the false-closed evidence | shipped-as-specified | `test_graph_family_bundle_project.py` (+161) now asserts against the **merged graph**, not the merge stage's output. New `test_graph_resolver_provenance.py` (+158). |
| D4/D5 — contract + doc surfaces | shipped-as-specified | Roster-coupled counts removed from 5 surfaces; `ext-point-derivation-resolver.md` § Current implementations is now the single enumeration point. |

**Footprint**: 8 files, 396 insertions, 55 deletions — exact, zero drift in either direction.

## Metrics and Anomalies

- Finalize was **1,767,890 tokens across 12 dispatched steps — more than phases 1–5 combined
  (1,505,604)**. ⛔ The plan's own `metrics.md` Total understates actual spend by **2.17x**
  (`n=4/6`, `6-finalize` unrecorded) — see Open Defect: the retrospective is scheduled at the one
  moment that floor is furthest from the truth.
- ⚠ A build run was **killed at 411s** by the wrapper's internal ceiling while the
  architecture-resolved envelope promised **441s**; the outer routed status reported
  `duration_seconds=0`. The suite needed 330s and passed under an explicit 570s override.
  **Handled correctly — not blind-retried** (provenance established first). Promoted as a lesson.
- ⛔ **`sonar-roundtrip` never ran**: `execution_profile=standard` prunes every `lane: full` step.
  A `bug_fix` touching production code in `manage-architecture` shipped without a Sonar roundtrip.
  Designed behaviour, recorded as an observation for the operator, not a defect.

## Routing and Merge Behavior

- **Review: two bots, not three.** CodeRabbit 1 actionable comment (operator SPLIT disposition —
  test site fixed, doc site declined with recorded rationale `ee3ca3`/`7a802f`/`14b0d9`); pr-agent
  no issues; **Sourcery absent**. Consistent with the standing `review-apparatus` concern.
- ⛔ **The participation signal was not sound, even though the outcome was right.** The
  `automatic-review` step called `github_pr fetch_findings` with an undeclared `--enabled-bots`
  flag; the call was rejected `exit_code=2` and the step still reported `done` 90 seconds later.
  The merge was blocked anyway — but only because the pre-merge barrier **re-derived**
  participation independently. Routed to `review-apparatus`.
- Pre-submission self-review found and fixed 1 finding in-run. CI green. No rebase conflicts.

## Parallelization Consequences

The CIS-027 / CIS-028 pairing held: **no collision**. Their surfaces stayed disjoint
(`manage-architecture` vs `phase-6-finalize`), and the feared `extension-api/standards/`
same-namespace-different-file touch did not materialise into a conflict. **Recorded as a
successful disjointness call** — the pairing heuristic was right here.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` → `1079`; row `landing` → `landings/PLAN-CIS-027.md`; row `plan_marshall_plan_id` stamped
- [x] epic.md Ordered Queue reconciled; founding defect retired from Open Defects
- [x] PLAN-CIS-029 hard gate on CIS-027 **released**
- [x] PLAN-CIS-004 and PLAN-CIS-026 gates **released**
- [x] resume_anchor updated; START-HERE regenerated

## Follow-Ups

- **11 candidate-lessons + 3 sibling findings drained alongside this landing** — dispositions in
  the epic decision log; 6 promoted to the corpus, the rest folded into CIS-010/011/016/020/028.
- ⛔ **`derived.json` question answered by elimination, not by CIS-027.** The store still contains
  **zero `derived.json` files**, and CIS-027 did not need to touch that. The zero-edge defect is
  now closed *without* it, so the absence is **not** the cause. It remains an open question for
  PLAN-CIS-029, downgraded from suspect to curiosity.
- **`declared:` suppression notes are a new consumer-visible signal** — any epic plan reading
  resolver reports should expect them on a resolver whose edges lost to a declaration. It is
  evidence of a *deliberate* discard, not a failure.
- **Post-merge PR revisit owed on #1079** — the merge routinely outruns the review.

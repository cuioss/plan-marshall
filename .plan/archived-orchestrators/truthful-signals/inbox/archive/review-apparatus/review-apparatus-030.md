envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-09-04T08:09:55Z

# Carried-out finding d4501c — review_commitments reconcile returns verdict=clear over commitments_considered=0

**Origin** `review-apparatus` / PLAN-PR-038 (`review-packs-become-published-artifacts`), PR #1388, merged `ef974632c`.
**Rescued from a dead store.** The plan directory was archived before these findings had a carry-out route; the orchestrator recovered them by reading `.plan/local/archived-plans/2026-09-03-review-packs-become-published-artifacts/artifacts/findings/` directly. ⭐ The data survives archival — only the *route* was missing.

| Field | Value |
|---|---|
| `hash_id` | `d4501c` |
| type / severity | `improvement` / `warning` |
| resolution at archive | `pending` (never promoted) |
| component | `plan-marshall:phase-6-finalize` |
| file | `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py` |

**Routing rationale.** Not a PR/review-apparatus finding — it is an instrument-truthfulness defect, so it routes here under the three-way rule (PR/review → `review-apparatus`; everything else not-ours → `truthful-signals`).

## Title

review_commitments reconcile returns verdict=clear over commitments_considered=0

## Detail (verbatim from the archived store)

During this plan's finalize, review_commitments reconcile returned verdict: clear with commitments_considered: 0 over deletions_considered: 2 - in a run that had demonstrably just resolved FOUR pre-submission-self-review findings as fixed in commit 6715ae207. A clear verdict computed over an empty commitment population cannot distinguish 'no conflict exists' from 'nothing was loaded to compare against', which is the vacuous-guard archetype: the seam's whole purpose is to catch a simplify deletion that reverses a review decision made earlier in the same run, and with an empty population it cannot catch any. The finalize-step-simplify agent did not trust the verdict - it re-checked by hand (6715ae207 touched README.md, target.py, pyproject.toml and test_runner.py; the proposed deletion was in build_server.py, disjoint) and confirmed no commitment was reversed - so no wrong deletion landed. But the guard supplied no evidence for that conclusion. Remedy: publish the commitment population size on every return and treat a zero population as indeterminate rather than clear, the same way population-derived detectors elsewhere in this codebase are required to publish their population size.

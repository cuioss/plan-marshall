envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-09-04T08:09:55Z

# Carried-out finding 5a5761 — references.affected_files under-records loop-back fix work, so every affected_files-derived finalize step under-scopes

**Origin** `review-apparatus` / PLAN-PR-038 (`review-packs-become-published-artifacts`), PR #1388, merged `ef974632c`.
**Rescued from a dead store.** The plan directory was archived before these findings had a carry-out route; the orchestrator recovered them by reading `.plan/local/archived-plans/2026-09-03-review-packs-become-published-artifacts/artifacts/findings/` directly. ⭐ The data survives archival — only the *route* was missing.

| Field | Value |
|---|---|
| `hash_id` | `5a5761` |
| type / severity | `improvement` / `warning` |
| resolution at archive | `pending` (never promoted) |
| component | `plan-marshall:manage-references` |
| file | `marketplace/bundles/plan-marshall/skills/manage-references/SKILL.md` |

**Routing rationale.** Not a PR/review-apparatus finding — it is an instrument-truthfulness defect, so it routes here under the three-way rule (PR/review → `review-apparatus`; everything else not-ours → `truthful-signals`).

## Title

references.affected_files under-records loop-back fix work, so every affected_files-derived finalize step under-scopes

## Detail (verbatim from the archived store)

Observed twice on this plan, at HEAD 7ddf3963 and again at 23179a2f9. finalize-step-plugin-doctor read affected_files, got 11 paths with no skill directory among them, and would have taken its documented skip-clean exit - writing a HEAD-bound record asserting the plan genuinely touched no skill. git diff 7ddf3963..23179a2f9 shows the commits touched two marketplace skill directories that affected_files does not record: build-server-client and script-shared. The step refused the skip and ran whole-tree instead. ROOT CAUSE: sync-affected-files re-derives the declared footprint from the solution outline's structured deliverable data by set union. Loop-back fix tasks created by the finalize triage are NOT in the outline, so their paths never enter the declaration - the refresh at the loop-back admission gate ran and reported added_count 0 with total 11, which is faithful to the outline and wrong about the tree. The union-only contract means the key can never narrow, but it also means it never learns paths the outline did not predict. IMPACT: any finalize step deriving scope from affected_files under-scopes on any plan whose scope moved during execute, and each such step's skip-clean exit writes a false assertion rather than a detectable gap. plugin-doctor happens to cross-check against git; a step that trusts the read does not. Candidate remedies: union the realized footprint (manage-references capture-realized-footprint / the git-derived worktree state) into affected_files at the loop-back refresh, or have the affected_files reader publish a provenance field so a consumer can tell an outline-derived declaration from a tree-corroborated one.

# Landing Analysis: PLAN-19 — Repoint ingested epic citations at durable references

epic: multiplattform
workstream: WS-02
pr: [#1374](https://github.com/cuioss/plan-marshall/pull/1374) — merged as `ad8297fa63d3c7d4a32b3b1997aadd4e4fc69b3f`

> Landing record for one shipped plan. Every claim in the operator's narrative was treated as a
> lead and settled against ground truth — the merged diff, PR/CI state, the on-disk run report,
> and the adapted RUNBOOK. This was the **first run of the OpenCode lane hand-off**, so the lane
> itself is analyzed here alongside the deliverables.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| **D1** — `AGENTS.md`, stop naming a plan directory | shipped-as-specified | `AGENTS.md:7` now reads "tracked in the `multiplattform` orchestrator epic; the cross-cutting constraints are stated in that epic's planning documents (machine-local, not version-controlled)". Reader still learns the source of truth (`marketplace/targets/`, `TARGET_REGISTRY`) |
| **D2** — `transforms.md`, **verify-only, already closed** | verified-already-satisfied | Not edited this run, correctly. The re-scope recorded at ingestion held |
| **D3** — `doc/adr/011`, resolve both citations | shipped-as-specified | §1 constraints restated inline as the ADR's own statement; the `020-target-scoped-components.md` citation (a path that never existed) repointed at `marketplace/targets/component_targets.py` |
| **D4** — `rule-provenance.md`, durable provenance | shipped-as-specified | Line 267 attribution replaced with `marketplace/targets/component_targets.py` (PR #1313) |

**Realized surface: exactly 3 files** — `AGENTS.md`, the ADR, `rule-provenance.md` (`git show --stat`). This matches the declared Expected Surface with **no under-declaration** — the opposite of PLAN-04's result, and the first clean surface match in this epic.

### Two premise drifts, both handled correctly

- **D1's "two prose statements" was already down to one.** The spec described both `AGENTS.md:7` and the second statement as naming `doc/plans/multiplattform/`. At run time only line 7 still needed work; line 74 had already been repointed at the orchestrator epic by an earlier commit, and the diff touches one line accordingly. This is the same drift the ingestion's own verdict recorded ("four citing files at `2cd1a19c`, three at `3bc01075`").
- **`AGENTS.md:39` correctly left alone.** It names `doc/plans/` generically for the standalone-plan-lane rule, which `3bc01075` deliberately kept. The run did not over-reach into it — exactly as claim label 1 required.

## Metrics and Anomalies

- **Tokens: unavailable** — OpenCode lane, outside the plan-marshall lifecycle, no `manage-metrics` record. Not estimated.
- **CI:** 11 checks, `overall_status: success`. `verify / verify` **SKIPPED ×2** — the documented docs-only footprint gate firing correctly on a three-doc change, not a failure. `generate-check` (OpenCode Generation Gate) **passed in CI**.
- **History rewrite:** the branch was force-pushed down to a single commit `dba8b7cf1` carrying deliverables only, after the plan/report were relocated out of version control. The merged squash `ad8297fa6` holds exactly the three files — verified independently here, not taken from the report.
- **Merge path:** merge queue (SQUASH). `safe-merge` was **correctly refused** because the base carries a required merge queue — the refusal is the mechanism working, not a fault.
- **Anomalies:** none in the deliverables.

## Routing and Merge Behavior

- **Review:** 3-of-3 expected bots participated — `sourcery-ai` (approved, no issues), `cuioss-review-bot`, `coderabbitai`. CodeRabbit obtained, so no `skip-bot-review` label was needed.
- **F2 — the finding that changed the lane.** CodeRabbit observed that the plan, living in version-controlled `doc/plans/`, opened by citing `.plan/local/opencode` — a git-ignored path absent from a clean clone — and on re-raise sharpened it: *the plan's own rule that a version-controlled document may not cite `.plan/` was violated by its own first two lines, and the plan was not self-sufficient in a clean clone.* That is a correct and sharp finding. The operator resolved it at the root rather than rebutting it: **all OpenCode plans now live under the git-ignored `.plan/local/oc-plans/` tree**, so the rule no longer applies to them and the self-sufficiency objection is moot.
- ⛔ **F1 — MISDIAGNOSED by the run, and initially accepted by this analysis. The generator gate was runnable all along.** F1 reported `generate.py --target all` as unexecutable because `uv` is not on `$PATH`. `uv` is indeed not on `$PATH` — but that is the wrong probe: **pyprojectx installs `uv` itself** (`[tool.pyprojectx.main] requirements = ["uv"]`, commented *"uv is the sole tool pyprojectx installs"*), and it is provisioned at `.pyprojectx/uv-0.9.16/uv`. `./pw generate` works on this host. The verification item was therefore skipped on a false premise rather than genuinely blocked. **Root cause is a documentation trap, not a host gap:** `AGENTS.md:74` and `CLAUDE.md:115` both instruct the bare `uv run python marketplace/targets/generate.py` form, so an agent following them literally fails and concludes the generator is unavailable. Recorded as an Open Defect against those two files; deliberately not folded into any plan. ⚠️ **Nothing was actually missed in this landing** — the run changed no generated-target content, and CI's `generate-check` ran and passed regardless. The cost was a false blocker that briefly held PLAN-16, PLAN-05 and PLAN-11.
- **Verification loop:** converged on round 1, exit `verifier-clear`, no budget extensions.

## Reconciliation Actions

- [x] row `status` → `landed` — `orchestrator queue --transition PLAN-19 --status landed`
- [x] row `pr` stamped `#1374`, `landing` stamped `landings/PLAN-19.md`, `plan_marshall_plan_id` stamped `n/a` — one `queue --set-row` call each
- [x] **emit-form annotation corrected** — the plan path changes from `doc/plans/` to `.plan/local/oc-plans/`; every future emitted command in this epic uses the new path
- [x] `author-cloud-plan` Open Defect **downgraded with evidence** (see Follow-Ups)
- [x] F1 **retracted as a misdiagnosis**; the real root cause recorded as an Open Defect against `AGENTS.md:74` / `CLAUDE.md:115`
- [x] epic.md reconciled; both generated blocks regenerated; `resume_anchor` updated

## Follow-Ups

- ⚠️ **The emit contract changed mid-flight and the ledger now reflects it.** Emitted commands must name `.plan/local/oc-plans/multiplattform/{NNN}-{slug}/plan.md`. The `{NNN}` convention and the derive-from-spec preamble are unchanged; only the tree moved. A command emitted against the old `doc/plans/` path would now author into a location the RUNBOOK no longer recognises.
- **Consequence worth holding: the run report is no longer version-controlled.** RUNBOOK § Recording discipline now states the report "is a local record (git-ignored); it does not land with the PR". Landings in this lane therefore arrive as an **operator paste**, never as an inbox message — the RUNBOOK forbids the run from writing outside its own plan directory, so the `inbox/` OUTBOX is structurally unused here. ⛔ Do not wait on an inbox message for an OpenCode landing. The orchestrator *can* read the report directly — read-only analysis, and it was used as ground truth for this record. ⚠️ **The filename changed after this landing:** reports were `report-NN.md` at the time of this run, and are now a fixed `report.md` (a resumed run appends a run section rather than creating a numbered sibling). This plan's own report was renamed accordingly.
- **`author-cloud-plan` Open Defect is substantially resolved — downgraded, not carried forward as stated.** The epic recorded it as "cites the retired template four times, so the cloud lane can no longer author a plan." Re-derived at HEAD: `_template/plan.md` appears **exactly once** (line 29), and that occurrence is a *historical retirement note* stating the rules are now "stated here and cited nowhere else". The OWNED-ELSEWHERE section does carry those rules inline. What genuinely remains is a **wording** defect: two sentences (lines 177, 205) still say "the template owns …" for a referent that no longer names a file. The lane can author a plan; the defect is cosmetic, not blocking. ⚠️ **The run report repeated the ledger's overstated version** — a stale defect entry propagated into a run's output, which is the cost of leaving a resolved defect standing.
- **Minor residue, neither blocking nor tracked as a defect:** an empty `doc/plans/multiplattform/` directory survives the relocation (git-invisible, working tree still clean), and the local branch `chore/repoint-ingested-epic-citations` was not deleted after the queue removed the remote. Both are one command each to clear.
- **RUNBOOK class R3 is now unreachable in this lane.** The label-decision table still classifies "any path under `doc/plans/`" as reviewable. Since this lane's plans are git-ignored they can never appear in a diff, so R3 can no longer match. Harmless, and still correct for an actual cloud-lane run — noted so a future reader does not mistake it for live behaviour.

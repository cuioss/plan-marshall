# Landing Analysis: PLAN-CIS-018 — main_sha records the pinned cwd

epic: code-intelligence-substrate
workstream: WS-04
pr: 1286
merge_commit: `7612c3a`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/310-main-sha-records-the-pinned-cwd/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 4 of 5 deliverables confirmed. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

The resolver split (`_current_repo_root` vs a new `_main_repo_root`) is real, correct on the default production path, and mutation-proven **at the resolver itself** rather than only through the capture. **But under a non-canonical `PLAN_BASE_DIR` override all three `main_*` columns still follow cwd**, and the new capture-time refusal misses it from a worktree subdirectory because it compares paths by equality rather than containment.

## Premise verdict

⛔⛔ **THE LEDGER'S STANDING QUESTION IS ANSWERED BY THE RUN ITSELF, NOT MERELY BY THE AUDIT.** The plan's claim-label table split *mechanism* from *symptom* and the run confirmed exactly that split — **the stated mechanism is REFUTED, the symptom is CONFIRMED**. D1 re-verified first-party that `_capture_main_sha` already passed an explicit tree argument (no-op territory); **the real defect was one layer down**, in the root-resolution helper inferring the root by walking up from a base directory that resolves to the worktree under a pinned cwd. ✅ **The run fixed the real defect and correctly avoided the forbidden add-another-explicit-tree-argument no-op.**

## Gaps carried out of this landing

**9 total — 0 high, 5 medium, 4 low.** No high-severity entries.

- A new, narrower instance was found (G1): under any `PLAN_BASE_DIR` override not literally `*/.plan/local`, the fix's own override branch delegates back to the cwd-following resolver. **Rated medium, not high, because no production code sets that variable** — it is a documented test/user hook, so the fix is complete on the shipped default path.
- **G3: a second cwd-walk-up root resolver of the identical shape lives unfixed** in the project-local audit skill, outside the swept `marketplace/` scope.
- **G4: D4's rule instructs a direct `.plan/` file read**, violating the repo's standing scripts-only access rule, when `phase_handshake list` already projects everything needed.

## Inconsistencies found, and what was verified

- None beyond the audit's own; the mechanism refutation was made first-party by the run.

## Residue

D4's population count for affected historical rows is correctly **blocked** (the corpus is machine-local and was unreachable), with the documented-rule fallback shipped instead.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-018 --status shipped`
- [x] row `pr` stamped `1286` — `orchestrator queue --set-row PLAN-CIS-018 --field pr --value 1286`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-018 --field landing --value landings/PLAN-CIS-018.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

⭐ **The blocked population count is now derivable locally.** G3's second resolver routes to **PLAN-CIS-049** (`510`); G4's access-rule violation routes to **PLAN-CIS-054** (`560`). ⭐ The mutation-restore hazard this run found (git-checkout restore silently reverting uncommitted fixes) **shipped as its own contract fix.**

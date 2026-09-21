# PLAN-17: fast-ci-footprint-gating

epic: plan-optimization
workstream: WS-05

> Staged plan spec. Operator-requested 2026-07-19, patterned on the cuioss-organization maven
> workflows (`/Users/oliver/git/cuioss-organization/.github/workflows/`). This is the CI-LAYER
> sibling of PLAN-11 (which gates the LOCAL phase-5 build by footprint) — same philosophy, different
> surface. Re-ground citations at outline.

## Objective

Make plan-marshall's CI (and therefore the merge gate) fast for non-building changes: a change whose
footprint is only `.plan/**`, `**.md`, `**.adoc`, `doc/**` (and peers) must NOT trigger the full
`pyprojectx-verify` build+tests, while a change touching buildable source (`**.py`, deps, workflows)
still runs the full verify — mirroring how the org's maven projects already path-gate their CI.

## Reference pattern (verified 2026-07-19)

The org reusable workflows use a **merge-queue-SAFE three-job structure** (do NOT use bare
`paths-ignore` — see the trap below):
- **`gate`** (always runs) — computes an output `run: true|false`.
- **`verify`** — `if: needs.gate.outputs.run == 'true'` (the heavy build/tests).
- **`conclusion`** (`if: always()`, `needs: [gate, verify]`) — the AGGREGATE the branch protection
  REQUIRES; reports SUCCESS when the gate deliberately skipped verify, FAILS when gate or verify
  failed. This is what lets a skipped build still satisfy a required check.

Today the reusable `reusable-pyprojectx-verify.yml` `gate` decides on **push-dedup** (open same-repo PR
covers the commit), NOT footprint; the org's `reusable-maven-build.yml` is where the path-based skip
lives. plan-marshall's `python-verify.yml` DELEGATES to the org reusable workflow (pinned SHA) and its
branch protection requires `verify / verify`.

## Deliverables

### D1 — footprint gate for plan-marshall CI (merge-queue-safe)

Add a footprint decision so the heavy verify is skipped when ALL changed paths are non-building
(`.plan/**`, `**.md`, `**.adoc`, `doc/**`, …), using the gate→conclusion aggregate so the required
check still reports success. **Because plan-marshall only owns its caller (`python-verify.yml`), not
the org reusable workflow, the outline MUST choose the seam:** (a) a caller-level `gate` + conditional
`uses:` + `conclusion` job in `python-verify.yml` (self-contained in plan-marshall); OR (b) contribute
the path-filter to `cuioss-organization/.github/workflows/reusable-pyprojectx-verify.yml` upstream +
bump the pin (org-wide benefit, cross-repo). **Acceptance:** a `.plan`/md/adoc-only PR reports the
required check green WITHOUT running the pyprojectx build; a `**.py` PR runs the full verify.

> **⚠ Merge-queue trap (the PLAN-09 class):** bare `paths-ignore` on `pull_request`/`merge_group`
> makes the workflow NOT run → a required check never reports → the merge queue stalls forever
> (exactly the bricks-main class PLAN-09 fixed for `merge_group`). The gate→conclusion aggregate
> (always reports) is mandatory; `paths-ignore` alone is forbidden.

### D2 — reconcile the required-check name + merge-queue ruleset

If D1 introduces the aggregate (`verify / conclusion`-style), the branch-protection / merge-queue
required check must move from `verify / verify` to the always-reporting aggregate — a ruleset
provisioning change on the same surface as PLAN-09 / the steward merge-queue provisioning. Update
CLAUDE.md's branch-naming/CI note accordingly. **Acceptance:** the required check is the aggregate
that reports on skipped runs; the merge queue admits a footprint-skipped PR without stalling.

## Design / scope forks (do NOT pre-answer)
- **Seam** — caller-level gate (self-contained) vs upstream reusable-workflow contribution (org-wide).
- **Scope** — this plan is plan-marshall's OWN repo CI. PROVISIONING the pattern for consumer
  maven/pyproject projects (steward-provisioned gate + required-check config) is a NOTED FOLLOW-UP,
  out of scope here unless the outline folds it in deliberately.
- **Footprint definition MUST match PLAN-11** — the CI "non-building footprint" and PLAN-11's local
  phase-5 "pure-doc footprint" should share one classification so local and CI never disagree.
  Cross-reference PLAN-11 at outline.

## Expected Surface
- `.github/workflows/python-verify.yml` (gate/conclusion jobs) [+ possibly an org-reusable contribution]
- branch-protection / merge-queue ruleset required-check name (steward / `ci repo` provisioning)
- CLAUDE.md CI note
- tests: hard to unit-test workflows — verify by driving a docs-only PR + a py PR (behavioral)

## Dependencies and Sequencing
- Depends on: none hard; SHARES the footprint definition with PLAN-11 (coordinate so they agree).
- Overlaps with: PLAN-11 (footprint classification — align, not a file collision); the merge-queue
  ruleset surface touched by PLAN-09 (shipped) / steward. Disjoint from the other staged plans.

## Hand-Off Command
```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-17-fast-ci-footprint-gating.md"
```

## Status Trail
- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-17.md is recorded}

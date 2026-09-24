envelope_version=1
sender_type=plan
sender_id=implement-opencode-enforcement-parity
epic=process-compliance
kind=finding
created=2026-09-23T21:21:29Z

envelope_version=1
sender_type=plan
sender_id=implement-opencode-enforcement-parity
epic=process-compliance
kind=finding
created=2026-09-23T21:15:00Z

# Finding: manage-architecture working-side module enumeration is blind in linked worktrees — diff-modules reports existing modules as removed, discover --apply plan deletes their curated descriptors, and the regression gate greenlights it on partial coverage

Epic: process-compliance
Plan: implement-opencode-enforcement-parity
Phase observed: phase-6-finalize, architecture-refresh Tier 0

## Summary

`manage-architecture diff-modules --pre-ref origin/main --project-dir {worktree}` reported `removed[10]` (all bundle-backed modules) while every one of those modules exists on disk in the worktree (`_project.json` lists all 12 keys; all 12 `enriched.json` files present; all 10 bundles present under `marketplace/bundles/`). The same call on the main checkout reports `removed[0]`. Acting on the false reading, `discover --force --apply plan` wrote a `module_removed x10` projection: 10 curated `enriched.json` files deleted plus the index gutted (11 files, 859 deletions). The `descriptor-regression-check` backstop then returned `regressive: false` — having examined only 2 modules (`modules_examined: 2`, exactly the 2 the broken scan can see). Followed mechanically, the step would have committed the deletion of 10 modules' curated descriptors. The commit was refused and the tree restored.

## Facet A — Working-side enumeration misses bundle-backed modules under worktree --project-dir

`diff-modules` on main: `added[0] removed[0] changed[12]` (the `changed[12]` is the documented derived-less-baseline noise). On the linked worktree: `added[0] removed[10] changed[2]` — the 10 missed modules are precisely the bundle-backed ones; only `default` and `documentation` (non-bundle modules) resolve. On-disk evidence contradicts the reading on all three surfaces (index keys, descriptor files, bundle source trees). The enumeration path is worktree-blind; the mechanism (index read vs dir scan vs inventory) needs a code-level fix, but the observable contract is broken regardless of mechanism.

## Facet B — The regression gate shares the blindness and cannot backstop it

`descriptor-regression-check` returned `regressive: false, violations: [], modules_examined: 2` over a delta that deletes 10 curated files. A gate whose coverage (`modules_examined`) excludes the deleted modules cannot attest the delta is benign, yet its boolean is consumed as exactly that attestation by the step's 3d commit branch. The gate must either enumerate with the same (fixed) reader as theostep commits, or refuse `regressive: false` whenever its examined set does not cover the delta's touched modules.

## Suggested fixes

1. Fix the working-side module enumeration so a linked worktree resolves identically to the main checkout (single reader for diff-modules, discover, and the regression gate).
2. Until fixed, make `descriptor-regression-check` fail closed on partial coverage: `regressive: false` requires `modules_examined` to cover every module the delta touches; otherwise return `status: error` (check could not run over the delta) rather than a benign verdict over a subset.
3. Consider a discover-side guard: refuse an `applied: plan` projection whose `module_removed` set names modules whose source trees still exist.

## Evidence

- Worktree diff-modules output: `added[0] removed[10]{plan-marshall,pm-dev-frontend,pm-dev-frontend-cui,pm-dev-java,pm-dev-java-cui,pm-dev-oci,pm-dev-python,pm-documents,pm-plugin-development,pm-requirements} changed[2]{default,documentation} unchanged[0]`.
- Main diff-modules output: `added[0] removed[0] changed[12]`.
- discover output: `attribution: plan_attributable, applied: plan, delta_classes: module_removed x10 plan`.
- Post-discover porcelain: `M _project.json` + `D` x10 enriched.json, 859 deletions.
- Regression output: `regressive: false, modules_examined: 2`.
- Worktree HEAD at the time: 6aab0b350 (clean tree before discover ran).

# PLAN-03: Compliant paths for forced violations

epic: process-compliance
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-03-{plan_slug}.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Close the three forced-violation gaps where the compliant path did not cover the use
case: a sanctioned orchestrator-spec read path (`corpus read --slug --plan`) or a
recorded AGENTS.md carve-out; a generator-bootstrap exception with template-content
staleness detection; and a wrapper filter passthrough for fast targeted signal. Each
gap gets a sanctioned path or a visible exemption — never silent improvisation.

## Deliverables

1. Sanctioned orchestrator-spec read path (`corpus read`) or recorded AGENTS.md carve-out, resolving the three-rules-one-action precedence gap.
2. Generator-bootstrap exception + template-content staleness detection for fresh-clone/stale-cache cases.
3. Wrapper filter passthrough form for fast targeted signal (sanctioned alternative to direct `.venv` pytest).
4. Tests pinning each path and each refusal-without-path.

## Claim Labels

- OBSERVED: Three deviations share one root cause — the compliant path did not cover the use case — read at `.plan/local/orchestrator/process-compliance/epic.md` § `Inherited Material D`
  - verdict: corroborated | checked_at: 6e239a13762514dc8e1f3fbceeb70b3d21ebac06 | by: process-compliance/cleanup | rescoped: n/a | evidence: epic Inherited Material D records three deviations sharing the no-compliant-path root cause
- OBSERVED: No manage verb exposes a spec body (three rules, one action, no precedence) — read at `.plan/local/orchestrator/process-compliance/epic.md` § `Inherited Material D`
  - verdict: corroborated | checked_at: 6e239a13762514dc8e1f3fbceeb70b3d21ebac06 | by: process-compliance/cleanup | rescoped: n/a | evidence: epic Inherited Material D records the three-rules-one-action gap with no spec-body verb
- HYPOTHESIS: The orchestrator corpus group is the seam for the sanctioned read path — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` § `corpus` (verify-at-outline)
  - verdict: corroborated | checked_at: 1e2aa916a | by: process-compliance/analyze | rescoped: n/a | evidence: corpus read verb landed at orchestrator.py cmd_corpus_read (PR #1542) — the sanctioned read path was built at the hypothesized seam
- HYPOTHESIS: The wrapper passthrough belongs at the pyprojectx executor filter layer — confirm/refute at `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/pyproject_build.py` § `run --command-args` passthrough (verify-at-outline; corrected 2026-09-18: no `filter` symbol, mechanism is command-args)
  - verdict: corroborated | checked_at: 1e2aa916a | by: process-compliance/analyze | rescoped: n/a | evidence: filter passthrough landed at build.py module-tests --filter over pyproject_build run --command-args (PR #1542) — the hypothesized executor filter layer
- Verify-first clause: The consuming phase must settle both HYPOTHESES against the implementing source before scoping — refutation loops back to re-scope.
  - verdict: unverifiable | checked_at: 6e239a13762514dc8e1f3fbceeb70b3d21ebac06 | by: process-compliance/cleanup | rescoped: n/a | evidence: procedural instruction to the consuming phase, not a checkable world premise; no implementing-source check applies

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — corpus read seam
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/pyproject_build.py` — wrapper passthrough layer (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py` — generator contract surface
- OBSERVED: `test/plan-marshall/plan-orchestrator/` — regression tests for the read path

## Dependencies and Sequencing

- Depends on: PLAN-02 (worktree seam settled; ordering only)
- Overlaps with: none
- Adjacent to: WS-05 dispatch surfaces — contracts vs. invocation paths, no file overlap

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/process-compliance/plans/PLAN-03-compliant-paths.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## Re-grounding instruction

Re-verify every Claim Label against the implementing source at HEAD during outline;
settle each HYPOTHESIS via `corpus set-verdict` before scoping. If the sanctioned
read path is refused by design, record the AGENTS.md carve-out instead and log the
rationale.

## Adjacency and overlap notes

If the generator-bootstrap exception contradicts "never by direct path", scope the
exception narrowly (fresh clone / stale cache with detection) rather than widening
direct-path use.

## Incorporated lessons

- None moved for this spec in the lesson sweep. The argparse-rejection cluster
  (2026-09-11-19-001, 2026-09-04-17-008) and the canonical-forms mechanism
  (2026-09-12-17-001) were retired from the shared corpus with tombstones
  (verdict `superseded`, class shipped as PR #1507): re-staging them here stays out
  of scope per the epic annotations.

## Folded inbox evidence (drain 2026-09-18, no new file surface)

- `finalize-machinery-002` + `git-branch-mechanics-001` item 1: post-merge stale
  main-checkout executor ran pre-fix code (PR #1509) — the P3 mirror image (live
  executor gone stale under a merge vs stale cache bypassed). Carry into
  deliverable 2 as the second staleness instance: post-merge executor regeneration
  as a finalize/move-back step, or a pre-invocation content-hash check.
- `lessons-pipeline-001`: opencode session read `.plan/` ledger trees direct (no
  sanctioned read verb exists for orchestrator trees) — live forced-violation
  evidence for deliverable 1 (P2 `corpus read` path). Enforcement half
  (executor-side refusal / permission-doctor rule) is noted as candidate mechanism
  for the implementing plan to scope, not a new deliverable here.
- `plan-06-anchors-and-mutex-001` item 1: third instance of the same gap (launched
  plan read staged spec via direct reads; `manage-plan-documents` plan-scoped,
  `orchestrator corpus` has no read verb). Proposed repair already matches
  deliverable 1: read-only `orchestrator spec read --slug --plan`, or an explicit
  carve-out naming the hand-off pointer as sanctioned direct-read material.
- `plan-07-session-identity-001` V2: fourth instance (session opened with direct
  `Read` on orchestrator spec + `.plan` listings, remediated to executor-only).
  Recurrence count for deliverable 1 now stands at four independent sessions.
- `phase-gates-001` item 1 (paste 2026-09-18): fifth instance — the PLAN-01
  implementing session itself opened with direct `Read` of this epic's ledger
  files before switching to executor-only access. Self-reported and remediated
  in-run; recurrence count now five.

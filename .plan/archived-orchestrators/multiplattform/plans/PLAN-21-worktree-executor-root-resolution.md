# PLAN-21: The worktree executor-regeneration trap

epic: multiplattform
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for hand-off.
> Lives at `plans/PLAN-21-worktree-executor-root-resolution.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command; it never launches the
> plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and
> carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

A git worktree under `.plan/local/worktrees/{name}` has no `.plan/local` of its own, because
`.plan/` is gitignored and never travels with a branch. `_resolve_plan_root()` resolves the plan
root by walking **up** from the current working directory to the nearest `.plan/local` ancestor —
so from inside such a worktree the walk succeeds, silently, against the **main checkout's**
`.plan/local`. Any operation that then writes plan-root-relative state writes it into the main
checkout instead of the worktree. Observed live during the PLAN-11 run: the runbook's
"regenerate executor" stale-gate remedy rewrote the main-checkout executor, and the failure it
was meant to fix (`unknown --add-row`, an executor still pinned to plugin-cache `0.1.1611`)
presented as a branch defect when it was nothing of the kind. This plan makes that escape
**loud instead of silent**, and documents the trap and its override where a developer will find
them.

⛔ This is a **detectability** plan, not a re-architecture of root resolution. The walk-up
behaviour is correct and deliberate for its primary callers (CI runners, fresh clones, and
consumer installs have no `.plan/local` and legitimately resolve upward — the docstring at
`file_ops.py`:269 says so). What is wrong is that the one case where walking up is certainly
incorrect — the cwd is inside a `worktrees/` subtree of the very `.plan/local` being resolved —
is indistinguishable from the cases where it is right.

## Deliverables

1. **D1 — Make the worktree escape detectable at `_resolve_plan_root()`.** When the walk-up
   resolves a `.plan/local` whose own `worktrees/` subtree CONTAINS the starting working
   directory, that is a provable escape: the caller is inside a worktree of the very checkout it
   just resolved. Surface it rather than returning it silently. ⛔ **Do not change the resolution
   for any other caller** — CI runners, fresh clones, and consumer installs must keep resolving
   upward exactly as they do today.
   *Done when:* a call originating inside `<plan-root>/.plan/local/worktrees/{name}/` is
   distinguishable from one originating in a tree with no `.plan/local` at all; the message names
   the resolved root, the originating worktree, and `PLAN_TRACKED_CONFIG_DIR` as the override;
   red-first tests cover BOTH the escape case and a matched negative (a genuine no-`.plan/local`
   ancestor, which must be unaffected).
2. **D2 — Document the trap and the override.** Record, in the developer doc that already
   describes the `.plan/` layout and the `worktrees/{plan-id}/` tree, that a worktree carries no
   `.plan/local`, that root resolution therefore walks up into the main checkout, and that
   `PLAN_TRACKED_CONFIG_DIR={worktree}/.plan` is the override that pins it. Name the observed
   symptom (an executor regenerated in the wrong tree) so a reader can match it.
   *Done when:* a developer who hits the symptom can reach the cause and the override from
   `doc/developer/repository-layout.adoc` without reading `file_ops.py`.

## Claim Labels

- OBSERVED: `_resolve_plan_root()` resolves by walking up from cwd to the nearest `.plan/local`
  ancestor, and its own docstring states the fallback rationale (CI runners / fresh clones /
  consumer installs) — read at `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py`:263 § `_resolve_plan_root`
- OBSERVED: `PLAN_TRACKED_CONFIG_DIR` is an existing, already-honoured override in this same
  module — read at `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py` (3 occurrences). ⛔ This plan
  introduces NO new environment variable; it makes the existing one discoverable at the moment it
  is needed.
- OBSERVED: the worktree tree is `.plan/local/worktrees/{plan-id}/` and `.plan/local` is
  gitignored — read at `doc/developer/repository-layout.adoc`:97 and `.gitignore`:45
- OBSERVED: the failure is not hypothetical — it occurred during the PLAN-11 run and was
  initially misread as a branch defect. Recorded at `landings/PLAN-11.md` § Follow-Ups (F3) and
  in the epic's resume anchor as the eighth member of the orchestrator/executor tooling cluster.
- HYPOTHESIS: `get_executor_path()` (`file_ops.py`:296) and `get_base_dir()` (`file_ops.py`:~375)
  are the two callers through which the escape actually reaches a write, since both are
  documented as resolving through the same plan root — confirm/refute by reading both call sites
  before scoping D1's surfacing point (verify-at-outline). ⛔ If the escape is better surfaced at
  one of these callers than inside `_resolve_plan_root()` itself, take that placement and record
  why; D1's done-condition is the *detectability*, not the line it lands on.
- Verify-first clause: **the exact failure mode of D1 is deliberately left to the outline.** A
  hard raise may break a legitimate caller this spec has not enumerated — the `NO_PLAN` sentinel
  path and the test-harness stand-in are both named in this module's docstrings. The plan must
  read the caller set and choose between raising, warning, and returning a flagged result, then
  state the choice and the enumeration that justified it. A refutation of the "no legitimate
  caller runs from inside a worktree" premise loops back to re-scope D1.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py` — D1
- OBSERVED: `test/plan-marshall/tools-file-ops/test_file_ops.py` — D1's red-first tests
- OBSERVED: `doc/developer/repository-layout.adoc` — D2

⚠️ **Surface authoring note, recorded because this epic has a measured under-declaration
pattern** (PLAN-04: 1 undeclared path, PLAN-15: 6, PLAN-11: 15). All three entries above were
swept against HEAD `8f6066cab` before staging: `file_ops.py` and `test_file_ops.py` both returned
live hits from `architecture search --content`, and `repository-layout.adoc` was read directly.
None is a guess. ⛔ If D1's verify-first clause moves the surfacing point to a different module,
that is a surface CHANGE and the spec's declaration is updated in the same act — not left to the
landing to reconcile.

## Dependencies and Sequencing

- Depends on: none. The mechanism is present at HEAD and independent of every staged plan.
- Overlaps with: **none among the four staged candidates.** PLAN-10 declares
  `test/plan-marshall/tools-file-ops/**` as a recursive glob, which CONTAINS this plan's
  `test_file_ops.py`. ⛔ **Not concurrent with PLAN-10** — and note that the exact-path matcher
  cannot see this containment, so `corpus cross-check` will report the pair clean. This
  sequencing note is the only thing that records it.
- Adjacent to: test-quality **PLAN-130**'s open PR #1435 (112 paths). Measured at staging: #1435
  touches `test/plan-marshall/tools-file-ops/test_safe_main_canonical.py` but NOT
  `test_file_ops.py`, NOT `file_ops.py`, and NO `doc/` path at all — so this plan is disjoint
  from it. ⛔ Re-measure before launch: #1435 was still open at staging and its footprint can
  grow.
- Adjacent to: the **runbook mirror**, which is deliberately NOT a deliverable here. The OpenCode
  runbook's stale-gate remedy is the other place this trap should be documented, but
  `.plan/local/opencode/RUNBOOK.md` is gitignored and untracked (`.gitignore`:45), so no PR can
  carry the edit. It folds into the epic's standing *"RUNBOOK contract edits live on ONE MACHINE
  ONLY"* gap rather than being invented as a shippable deliverable this plan cannot ship.

## Hand-Off Command

⛔ This epic emits **OpenCode runbook commands**, not `/plan-marshall` pointers — the ledger's
EMIT FORM directive in `epic.md` § Queue annotations is authoritative and this section is a
convenience copy that loses on any divergence.

```text
Plan: .plan/local/oc-plans/multiplattform/210-worktree-executor-root-resolution/plan.md
Staged orchestrator spec: .plan/orchestrator/multiplattform/plans/PLAN-21-worktree-executor-root-resolution.md

Execute it per the runbook at .plan/local/opencode/RUNBOOK.md — it is the working contract
(Step 3 authors the plan from the staged spec; Steps 4–9 then apply). Do not delete the
orchestrator spec; it remains the source record.
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

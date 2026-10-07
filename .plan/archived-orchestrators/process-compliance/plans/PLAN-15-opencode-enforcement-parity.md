# PLAN-15: Opencode enforcement parity

epic: process-compliance
workstream: WS-06

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-15-{plan_slug}.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Ship opencode-native enforcement parity with Claude Code: a two-tier
(`deny` for never-legitimate, `ask` for rarely-legitimate) permission map plus a
`tool.execute.before` guard plugin mirroring R1–R4, scoped by a
role × surface × path matrix (plan-executor vs orchestrator vs reviewer) so the
run-3 bypass class (direct pytest/git, shell file-ops, direct `.plan` reads,
`/tmp` staging, `rm` via Bash) is refused or prompted on opencode instead of
passing silently.

## Deliverables

1. Two-tier permission map in `opencode.json` (deny-list for never-legitimate
   commands/paths, ask-list for rare escapes), with per-agent overrides for the
   executor vs orchestrator rows of the matrix.
2. `tool.execute.before` guard plugin under `.opencode/` implementing the R1–R4
   equivalent (shell chaining, shell file-ops, generated-executor edits,
   hard-coded builds) with throw-to-block semantics and audit logging.
3. Role × surface × path matrix documented (who × what × where), preserving the
   orchestrator's small-ops carve-out (git/CI read-side, read-only analysis) and
   the plan-executor's worktree + `.plan/temp/` confinement.
4. Module tests proving each deny refuses, each ask prompts, and each
   orchestrator carve-out still passes; docs updated for the opencode path.
5. Steward handoff: per-project application documented as a singular
   steward action (wizard/upgrade ensure-op reusing deliverables 1–2), so no
   future project needs a plan for this — this plan builds the mechanism once.

## Claim Labels

- OBSERVED: opencode honors per-tool `allow`/`ask`/`deny` with pattern matching
  and per-agent overrides, and explicit `deny` holds under `--auto` — read at
  `opencode.json` § `permission` (verify-at-outline: consuming phase re-reads
  the live schema, which is versioned upstream).
- OBSERVED: opencode plugins expose `tool.execute.before` with throw-to-block
  semantics — read at `.opencode/commands/` § `sync-opencode.md` plugin layout
  plus upstream plugin docs (verify-at-outline against the installed opencode
  version's hook surface).
- HYPOTHESIS: the run-3 bypass class (direct pytest/git, shell file-ops,
  direct `.plan` reads, `/tmp` staging) traverses exactly the `bash`/`read`/
  `edit` tool surfaces the guard plugin observes — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py`
  § `OPENCODE_DEFAULT_PERMISSIONS` (verify-at-outline).
- HYPOTHESIS: a role × surface × path matrix can scope deny/ask without
  breaking the orchestrator's read-side carve-outs — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py`
  § `permission_settings_path` (verify-at-outline).
- Verify-first clause: the consuming phase re-verifies the opencode permission
  schema version and the `tool.execute.before` hook surface against the
  implementing sources before scoping; refutation loops back to re-scope.

## Expected Surface

- OBSERVED: `opencode.json` — permission map lives here
- OBSERVED: `.opencode/commands/` — guard plugin ships under `.opencode/`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` — opencode runtime defaults and permission settings path
- OBSERVED: `test/plan-marshall/platform-runtime/` — module tests for the parity behavior

## Dependencies and Sequencing

- Depends on: none (adjacent to shipped PLAN-07-opencode-repairs, which it extends without re-staging)
- Overlaps with: PLAN-13-finalize-mechanism-defects (both touch `platform-runtime`
  area; sequence, do not parallelize — different files, same neighborhood)
- Adjacent to: WS-05 dispatch surfaces (`inject_project_dir.py`,
  `phase-5-execute/standards/operations.md`) which stay untouched

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-15-opencode-enforcement-parity.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

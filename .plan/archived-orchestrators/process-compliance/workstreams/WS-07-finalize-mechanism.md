# WS-07: Finalize-mechanism structural defects

epic: process-compliance

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-07-{slug}.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Own the phase-6-finalize mechanism defects that are neither opencode-specific (WS-06)
nor worktree-materialization (WS-02): the `emit-landing` fail-closed epic guard
contradicting `archive-plan`'s irreversibility, `archive-plan`'s SKILL.md documenting
the wrong archive path (missing the `local/` segment), a forked finalize subagent
inheriting a worktree-pinned cwd and stranding `branch-cleanup`, `pr_title` staleness
after a gate deliverable removes scope, and the unconfirmed `session_binding` orphan-sweep
hypothesis (may be removing its own cwd-lookup index directory every finalize). Closes
when the finalize dispatcher's structural contradictions are closed and the orphan-sweep
hypothesis is settled one way or the other.

## Scope

- In scope: `emit-landing`/`archive-plan` contradiction, archive-plan doc-path defect,
  forked-subagent cwd inheritance, `pr_title` re-derivation, `session_binding` orphan-sweep
  investigation
- Out of scope: opencode runtime gaps (WS-06), worktree-materialization flag/guards (WS-02),
  landing-facts machine-readable block enforcement (WS-06/PLAN-11)

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-13-finalize-mechanism-defects | staged | Four structural defects plus the orphan-sweep hypothesis |

## Sequencing and Surface Notes

- PLAN-13 touches `phase-6-finalize/standards/{emit-landing,archive-plan}.md` and
  `platform-runtime/scripts/session_binding.py` — no overlap with WS-06's opencode-only
  surface or WS-02's `prepare_execute`/phase-5-dispatch surface.

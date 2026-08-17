# Aspect: Invariant Outcomes Summary

Presents the pluggable invariants captured during phase handshakes (defined in `plan-marshall:plan-marshall:_invariants.py`). Facts come from `summarize-invariants.py`; this document tells the LLM how to report them.

## Invariants in Scope

From `INVARIANTS` registry:

| Name | Applies | Captured Value |
|------|---------|----------------|
| `main_sha` | always | Main checkout HEAD SHA |
| `main_dirty` | always | Main checkout dirty-file count |
| `worktree_sha` | worktree plans | Worktree HEAD SHA |
| `worktree_dirty` | worktree plans | Worktree dirty-file count |
| `task_state_hash` | always | Stable SHA of task graph reduced form |
| `qgate_open_count` | always | Open Q-Gate findings count per phase |
| `config_hash` | always | Stable SHA of the `plan` config section of `marshal.json` (phase-independent) |
| `phase_steps_complete` | always | SHA of required-steps list OR failure |

## Inputs

`summarize-invariants.py` reads `status.metadata.phase_handshake` (or the legacy `status.metadata.invariants` path if the handshake key is absent). It does NOT re-run capture — the values are whatever phase transitions already persisted.

## TOON Fragment Shape

```toon
aspect: invariant_summary
status: success
plan_id: {plan_id}
phases[*]{phase,invariants_present,invariants_missing}:
  1-init,[main_sha,main_dirty,task_state_hash,qgate_open_count,config_hash,phase_steps_complete],[]
  6-finalize,[main_sha,main_dirty,worktree_sha,worktree_dirty,task_state_hash,qgate_open_count,config_hash,phase_steps_complete],[]
drift[*]{invariant,from_phase,to_phase,detail}:
  main_sha,3-outline,4-plan,"HEAD changed mid-plan (unexpected for worktree plan)"
findings[*]{severity,message}:
  info,"All phase handshakes recorded"
  warning,"main_sha drift between outline and plan phases"
```

## LLM Interpretation Rules

- A `missing` invariant for a phase the plan actually executed is an `error` — the phase did not complete its handshake.
- `main_sha` drift is a `warning` for worktree plans (the worktree should isolate the plan from main) and `info` for non-worktree plans.
- ⛔ **A `main_sha` drift entry whose `to_phase` is `5-execute` is NOT actionable on a worktree-backed plan whose handshake rows predate the main-anchored resolution fix.** The `main_sha` capture used to resolve its tree cwd-relatively, and from phase-5 onward the orchestrator's working directory is pinned to the plan's worktree, so the `5-execute` row recorded the **feature-branch** HEAD under a column named for main. Every worktree-backed plan therefore produced exactly one guaranteed-false `main_sha` drift entry at the `4-plan → 5-execute` boundary while main had not moved. Report such an entry as a **known capture artifact**, never as evidence that main moved mid-plan, and never as a finding against the plan. Drift at any *other* boundary of the same plan is unaffected — the planning-phase rows ran with cwd on main and are correct.
  - **Identifying an affected row without a reference:** the row is self-diagnosing. When `main_sha` equals `worktree_sha` on a row that carries both columns, the two columns describe one tree, which is only possible under the pre-fix resolution. No archived corpus, no fix date, and no plan metadata are needed to make the call.
  - **Post-fix rows cannot carry this artifact:** `main_sha` is now read main-anchored, and a row whose two commits are equal is refused at capture time (`worktree_sha_equals_main_sha`) rather than persisted. A drift entry at this boundary on a post-fix row is therefore a real signal.
  - The stored rows are **not rewritten**: the quarantine is interpretive, applied when the summary is read.
- `qgate_open_count > 0` in the final finalize row is a `warning` — findings were left unresolved.
- `phase_steps_complete` = `FAILED` (sentinel from `PhaseStepsIncomplete`) is an `error`.

## Finding Shape

```toon
aspect: invariant_summary
severity: info|warning|error
invariant: {name}
message: "{one-line}"
```

## Out of Scope

- Re-running invariant capture (values are read-only here).
- Phase handshake protocol details — see `plan-marshall:ref-workflow-architecture` standards.

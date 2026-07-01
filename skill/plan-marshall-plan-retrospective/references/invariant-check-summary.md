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
| `config_hash` | always | Stable SHA of phase config |
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
- Phase handshake protocol details — see `plan-marshall:plan-marshall:ref-workflow-architecture` standards.

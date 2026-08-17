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
- ⛔ **A row where `main_sha` equals `worktree_sha` has a `main_sha` that cannot be trusted to be main's HEAD.** The `main_sha` capture used to resolve its tree cwd-relatively, and from phase-5 onward the orchestrator's working directory is pinned to the plan's worktree, so a row captured after that pin recorded the **feature-branch** HEAD under a column named for main. Any drift entry into such a row may therefore be an artifact of the mislabel rather than evidence that main moved.
  - ⛔ **The fingerprint marks the row as AMBIGUOUS — it does not by itself convict.** A second, entirely benign state produces the same equal pair: a worktree-backed plan whose feature branch carries no commit of its own, whose HEAD is therefore still the commit it branched from. `phase-5-execute` Step 2.5 materializes the worktree unconditionally, before the `early_terminate` short-circuit, so every analysis-only plan reaches its phase-5 boundary in exactly that state. Such a row is **correct**, and its `main_sha` really is main's HEAD — so a drift entry beside it can be a real "main moved mid-plan" signal, which happens whenever a sibling plan merged while this one was in flight.
  - **Settle it by branch containment, which is the only evidence that separates the two.** Ask whether the `main_sha` the row records is reachable from the integration branch. A commit that never reached main is the mislabelled feature-branch HEAD: the row is an artifact and any drift entry into it is false. A commit that *is* on main means the row is sound and the drift entry is a genuine signal to report. The stored rows carry nothing else that distinguishes the two cases, so a verdict asserted without this check is a guess.
  - ⛔ **Do not key the judgement on which boundary the entry sits at.** It is tempting to say the artifact always appears at `4-plan → 5-execute` and that earlier boundaries are therefore trustworthy — both halves are false. `plan-marshall/workflow/execution.md` re-anchors cwd into the worktree in its Step 0 entry-preflight and *then* issues `capture --phase 4-plan`, which **upserts** the stored row; so a plan re-entered across sessions has its `4-plan` row re-captured from the worktree too, moving the false entry back to `3-outline → 4-plan` and leaving `4-plan → 5-execute` clean. Which rows are affected depends on which were last written after a cwd pin, and the corpus does not record that.
  - **A post-fix row needs no containment check.** `main_sha` is now read main-anchored, so it is main's HEAD whatever the working directory; and a row whose two columns resolved to the same tree is refused at capture time (`main_capture_read_the_worktree`) rather than persisted. A post-fix row may still legitimately show the equal pair — the commit-less-branch case above — but its `main_sha` is sound, so every drift entry on it is a real signal.
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

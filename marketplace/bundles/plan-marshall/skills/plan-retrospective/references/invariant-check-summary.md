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
- `main_sha` drift is a `warning` for worktree plans and `info` for non-worktree plans. ⚠ The warning does **not** mean the worktree failed to isolate the plan: `main_sha` describes the integration target, which moves whenever a sibling plan merges while this one is in flight, and the worktree isolates the plan's *work* from main rather than freezing main. See `plan-marshall:plan-marshall` → `references/phase-handshake.md` § Blocking classification for why these boundaries are scoped the way they are.
- ⛔ **A row where `main_sha` equals `worktree_sha` (both columns present) has a `main_sha` of UNKNOWN provenance, and the corpus cannot resolve it.** Report a drift entry adjacent to such a row as **unverifiable**: do not count it as a finding, and do not assert that main moved. Say which row is ambiguous and why. Both directions are errors here — dismissing a real "main moved mid-plan" signal, and reporting a mislabel as one.
  - **Where the ambiguity comes from.** The `main_sha` capture used to resolve its tree cwd-relatively, and from phase-5 onward the orchestrator's working directory is pinned to the plan's worktree, so a row captured after that pin recorded the **feature-branch** HEAD under a column named for main. But a second, entirely benign state produces the identical equal pair: a worktree-backed plan whose feature branch carries no commit of its own, whose HEAD is therefore still the commit it branched from. `phase-5-execute` Step 2.5 materializes the worktree unconditionally, before the `early_terminate` short-circuit, so every analysis-only plan reaches its phase-5 boundary in exactly that state — and its row is **correct**.
  - ⛔ **Three discriminators suggest themselves and all three fail. Do not use them.**
    - **The boundary.** `plan-marshall/workflow/execution.md` re-anchors cwd into the worktree in its Step 0 entry-preflight and *then* issues `capture --phase 4-plan`, which **upserts** the stored row — so a plan re-entered across sessions has its `4-plan` row re-captured from the worktree too, moving the ambiguity back a boundary. Which rows are affected depends on which were last written after a cwd pin, and nothing records that.
    - **The stored columns.** No column records which tree a value was read from. That is the whole defect.
    - **Branch containment** — asking whether the recorded `main_sha` is reachable from the integration branch. This is the one that looks decisive and is the most dangerous, because it inverts at exactly the moment the rule is read. This summary runs as a `post_run_review` step (`order: 995`), i.e. **after the merge gate**, and the archived-corpus readers run later still. The default PR merge strategy is a **merge commit** (`tools-integration-ci` `pr merge --strategy`), which makes every feature-branch commit an ancestor of main; a rebase or fast-forward merge does the same. So a mislabelled `main_sha` reads as "on main" and containment returns *sound* for precisely the rows it was meant to convict. Only a squash merge preserves the distinction, and that is not the default — a rule for arbitrary consumer repositories cannot rest on a non-default merge strategy.
  - **What would settle it is not in the corpus:** whether the row was captured before or after the main-anchored resolution fix. If that is known from outside the record, a pre-fix row with the fingerprint is the artifact and a post-fix one is the benign case. Absent that, `unverifiable` is the honest verdict and the only one this data supports.
  - **A post-fix row is sound — with one exception.** `main_sha` is read main-anchored, and a row whose two columns resolved to the same tree is refused at capture time (`main_capture_read_the_worktree`). The exception is a run with a base-dir override active (`PLAN_BASE_DIR`, a documented user override, or `set_base_dir()`): the resolver then follows the working directory, and from a **subdirectory** of the worktree it resolves to that subdirectory — which is not equal to `worktree_path`, so the refusal does not fire and a mislabelled row persists. Treat a post-fix row's fingerprint as sound only when no override was in play.
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

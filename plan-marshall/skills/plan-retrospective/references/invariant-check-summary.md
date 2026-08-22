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

`summarize-invariants.py` reads **`{plan_dir}/handshakes.toon`** — the canonical row store owned by `plan-marshall:plan-marshall:phase_handshake`. It does NOT re-run capture; the values are whatever the phase transitions already persisted.

⚠ Its TOON output carries invariant **names** per phase (`invariants_present` / `invariants_missing`) plus `drift[]` and `findings[]` — **not** per-row column values, and `phase` / `captured_at` / `override` / `override_reason` are stripped as row metadata. A check that needs a stored **value** (the one below does) must read `handshakes.toon` directly; the summary alone cannot supply it.

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
- ⛔ **A drift entry on `main_sha` may be an artifact of a resolution defect rather than evidence that main moved. Settle it from the stored row before reporting it either way.** ⚠ This check needs two column values the summary output does not carry, so **open `{plan_dir}/handshakes.toon`** (§ Inputs) and read them from the destination row of the drift entry.
  - **Step 1 — the fingerprint.** Does the row carry both `main_sha` and `worktree_sha`, holding the **same** commit? If not, the entry is an ordinary signal; report it normally. If so, the row's `main_sha` is of uncertain provenance — continue.
  - **Step 2 — the era, from `captured_at`.** The `main_sha` capture used to resolve its tree cwd-relatively, and from phase-5 onward the orchestrator's working directory is pinned to the plan's worktree, so a row written after that pin recorded the **feature-branch** HEAD under a column named for main. Compare the row's `captured_at` against when the main-anchored resolution fix landed in this repository. **Written before it** → the row is the artifact: the drift entry is false, report it as such, and do not count it as a finding. **Written after it** → the row is sound and the entry is a real signal to report.
  - ⭐ **`captured_at` is the discriminator that works, and it works because `capture` upserts.** A re-entered plan's row is re-stamped when it is re-written, so `captured_at` dates *the write whose resolution semantics produced the value* — which is exactly the question. That property is what defeats the alternatives below.
  - ⛔ **Three other discriminators suggest themselves. All three fail — do not use them.**
    - **The boundary.** `plan-marshall/workflow/execution.md` re-anchors cwd into the worktree in its Step 0 entry-preflight and *then* issues `capture --phase 4-plan`, which upserts the stored row — so a plan re-entered across sessions has its `4-plan` row re-captured from the worktree too, moving the artifact back a boundary. Nothing records which rows that happened to.
    - **The fingerprint alone.** It does not convict: a worktree-backed plan whose feature branch carries no commit of its own has both HEADs on the commit it branched from, and its row is **correct**. `phase-5-execute` Step 2.5 materializes the worktree unconditionally, before the `early_terminate` short-circuit, so every analysis-only plan reaches its phase-5 boundary in that state. This is why Step 2 exists.
    - **Branch containment** — asking whether the recorded `main_sha` is reachable from the integration branch. This is the one that looks decisive and is the most dangerous, because it **inverts at the moment this rule is read**. This summary runs as a `post_run_review` step (`order: 995`), i.e. after the merge gate, and archived-corpus readers run later still. The default PR merge strategy is a **merge commit** (`tools-integration-ci` `pr merge --strategy`), which makes every feature-branch commit an ancestor of main — so a mislabelled `main_sha` reads as "on main" and containment returns *sound* for precisely the rows it should convict. (Squash and rebase both preserve the distinction, because both rewrite or discard the feature SHAs; the **default** does not, and a rule for arbitrary consumer repositories cannot rest on a non-default strategy.)
  - **A post-fix row is sound — with one exception.** `main_sha` is read main-anchored, and a row whose two columns resolved to the same tree is refused at capture time (`main_capture_read_the_worktree`). The exception is a run with a base-dir override active (`PLAN_BASE_DIR`, a documented user override, or `set_base_dir()`): the resolver then follows the working directory, and from a **subdirectory** of the worktree it resolves to that subdirectory — which is unequal to `worktree_path`, so the refusal does not fire and a mislabelled row persists.
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

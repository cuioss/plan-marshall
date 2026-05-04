# Phase Handshake

Drift-detecting handshake between phase transitions. Each phase's completion captures a fingerprint of key invariants; the next phase's entry re-evaluates reality and refuses to continue on mismatch. Invariants are pluggable — adding one is a single tuple appended to a registry list.

## Why

Phase skills occasionally drift between what they *report* they did and what the next phase *observes*. Examples: a task summary claims file edits while the tree is clean; a phase advances while Q-Gate findings are still open; phase config changes mid-run. A lesson that prescribes "run `git status` manually" is a ritual, easy to skip. The handshake replaces the ritual with a mechanical guardrail.

## Script surface

Executor notation: `plan-marshall:plan-marshall:phase_handshake`

```
phase_handshake capture --plan-id X --phase P [--override --reason "text"]
phase_handshake verify  --plan-id X --phase P [--strict]
phase_handshake list    --plan-id X
phase_handshake clear   --plan-id X --phase P
```

All subcommands return TOON.

### `capture`

Runs every applicable invariant and writes (or replaces) the row for `phase` in `handshakes.toon`. `--override --reason X` marks the row as an authorized override.

```toon
status: success
plan_id: X
phase: 5-execute
override: false
worktree_applicable: false
invariants:
  main_sha: 3823a0dd…
  main_dirty: 0
  task_state_hash: a1b2c3…
  qgate_open_count: 0
  config_hash: d4e5f6…
```

`--override` without `--reason` returns `status: error, error: missing_reason`.

### `verify`

Compares a stored capture against a freshly-computed one. Three possible statuses:

| Status | Meaning | Caller action |
|---|---|---|
| `ok` | every captured invariant still matches | continue |
| `drift` | one or more invariants differ | **STOP** and surface `diffs[]` verbatim |
| `skipped` | no capture row exists for this phase | log warning and continue |

`--strict` makes `drift` exit with code 1; without the flag, drift is still `status: drift` in TOON but exit code is 0.

Drift shape:

```toon
status: drift
plan_id: X
phase: 5-execute
override: false
drift_count: 2
diffs[2]{invariant,captured,observed}:
  main_dirty,0,12
  main_sha,3823a0dd,15efe821
```

### `list` / `clear`

`list` returns every row in `handshakes.toon` projected to the canonical field set. `clear --phase P` removes exactly the row for `P` (others remain intact).

## Storage

File: `<base>/plans/{plan_id}/handshakes.toon` (owned exclusively by `phase_handshake`). Flat TOON, one row per phase, uniform array serialized via `toon_parser.serialize_toon`.

```toon
plan_id: recipe-plugin-compliance
handshakes[2]{phase,captured_at,worktree_applicable,override,override_reason,main_sha,main_dirty,worktree_sha,worktree_dirty,task_state_hash,qgate_open_count,config_hash,pending_tasks_count,phase_steps_complete}:
  5-execute,2026-04-14T17:42:57Z,false,false,"",3823a0dd…,0,"","",a1b2c3…,0,d4e5f6…,0,""
  6-finalize,2026-04-14T18:01:12Z,false,false,"",15efe821…,0,"","",a1b2c3…,0,d4e5f6…,0,e7f8a9…
```

Rationale for flat TOON over nested: simpler parsing, one row per phase, direct diff-ability. Adding a new invariant adds a new column; captures missing a column are treated as "not captured, skip comparison" during verify, so new invariants can roll out without invalidating history.

## Invariant registry

Defined in `_invariants.py` as `(name, applies_fn, capture_fn)` tuples.

| Invariant | `applies_fn` | `capture_fn` | Catches |
|---|---|---|---|
| `main_sha` | always | `git rev-parse HEAD` at main checkout root | any commit change |
| `main_dirty` | always | `git status --porcelain` line count at main checkout root | uncommitted drift |
| `worktree_sha` | `status.metadata.worktree_path` non-null | `git rev-parse HEAD` inside worktree | worktree/main confusion |
| `worktree_dirty` | same as above | `git status --porcelain` line count inside worktree | uncommitted drift inside worktree |
| `task_state_hash` | always | SHA256 of sorted `(number, status, step_outcomes, depends_on)` from `manage-tasks list` | tasks silently mutated |
| `qgate_open_count` | always | `filtered_count` from `manage-findings qgate query --resolution pending --phase P` | Q-Gate bypass |
| `config_hash` | always | SHA256 of stable-key JSON of `manage-config plan phase-P get` output | config swapped mid-run |
| `pending_tasks_count` | always | row count from `manage-tasks list --status pending` | premature transition with fix tasks still pending |
| `phase_steps_complete` | always (no-op when phase has no declaration) | See [resolution rule](#phase_steps_complete-resolution) | silently skipped intra-phase steps |

### `phase_steps_complete` resolution

The invariant reads a **static required step list** from the phase skill itself and validates it against `status.metadata.phase_steps[phase]` (written by `manage-status mark-step-done`).

**Resolution rule:**

1. Locate the phase skill directory by convention: `marketplace/bundles/plan-marshall/skills/phase-{phase}`, where `{phase}` is the phase key (e.g. `6-finalize`). The marketplace root is discovered via `marketplace_paths.find_marketplace_path()` so the rule works from either the checked-out source tree or the plugin cache.
2. Read the sibling file `standards/required-steps.md` inside that directory. If the file does not exist, the invariant is a **no-op** — capture returns `None` and the column stays empty, so phases that do not opt in pay no cost.
3. Parse the file as markdown: every line starting with `- ` (after stripping leading whitespace, and unwrapping a single pair of inline `` ` `` backticks) becomes one required step name. Blank lines, headings, and prose are ignored. Declaration order is preserved for stable hashing; completeness is checked as a set.
4. For each required step `S`, read `status.metadata.phase_steps[phase][S]`. The step **passes** only when the recorded outcome is exactly `done`. Missing entries and entries with any other outcome (including `skipped`) **fail**.

**Capture-time behavior:**

- **Pass**: the capture function returns a truncated SHA256 of the sorted required step list. If the required set changes between capture and verify, that counts as drift on this column.
- **Fail**: the capture function raises `PhaseStepsIncomplete(phase, missing, not_done)`. `cmd_capture` catches the exception and returns a structured error payload **without writing a row**:

```toon
status: error
error: phase_steps_incomplete
plan_id: X
phase: 6-finalize
missing[2]:
  - sonar-roundtrip
  - branch-cleanup
not_done[1]{step,outcome}:
  lessons-capture,skipped
message: "phase_steps_complete failed for phase '6-finalize': ..."
```

The phase skill MUST either call `manage-status mark-step-done` for each unrecorded step or acknowledge the skip (currently unsupported — skipping is a hard failure per the cwd handshake spec) before re-running capture.

**Verify-time behavior:** if the observed re-capture raises `PhaseStepsIncomplete`, `cmd_verify` surfaces it as a `drift` on the `phase_steps_complete` column with an `incomplete(missing=...,not_done=...)` observed value. Callers see the same structured signal regardless of whether the mismatch happened during capture or a later re-verify.

**`required-steps.md` format** (owned by each phase skill that opts in):

```markdown
# Required steps for phase-6-finalize

- commit-push
- create-pr
- automated-review
- sonar-roundtrip
- record-metrics
- archive-plan
- branch-cleanup
- validation
- lessons-capture
```

### Adding a new invariant

1. Add a capture helper in `_invariants.py`
2. Append a tuple `(name, applies_fn, capture_fn)` to `INVARIANTS`
3. Add the column name to `HANDSHAKE_FIELDS` in `_handshake_store.py`
4. Add a drift test case

No changes are required in `_handshake_commands.py`, `phase_handshake.py`, or any phase skill — unless the new invariant needs to raise a capture-time gate (as `phase_steps_complete` does). In that case, define a dedicated exception in `_invariants.py` and teach `cmd_capture`/`cmd_verify` to catch it, mirroring the `PhaseStepsIncomplete` pattern.

### Worktree applicability

`worktree_sha` and `worktree_dirty` apply iff `status.metadata.worktree_path` is set. `phase-1-init` writes that field when a plan uses a worktree and omits it otherwise, so per-plan worktree usage is already the single source of truth — the handshake does not look at global config.

## Integration with phase lifecycle

The actual call sites for `capture` and `verify` are the orchestrator workflow files [`plan-marshall:plan-marshall:workflows/planning.md`](../workflows/planning.md) (phases 1-init through 4-plan boundaries) and [`plan-marshall:plan-marshall:workflows/execution.md`](../workflows/execution.md) (4-plan→5-execute fallback and 5-execute→6-finalize boundaries). Each `manage-metrics phase-boundary` invocation in those workflows is followed by a `phase_handshake capture --phase {prev_phase}` call, and each next-phase entry runs `phase_handshake verify --phase {prev_phase} --strict` before any phase-specific work begins.

The abstract contract is documented in [`../../ref-workflow-architecture/standards/phase-lifecycle.md`](../../ref-workflow-architecture/standards/phase-lifecycle.md): the Phase Completion Protocol calls `capture` as its final step; the Phase Entry Protocol calls `verify --strict` immediately after the Q-Gate check. The orchestrator workflows are the canonical implementation of that contract — they wire capture/verify alongside the existing `manage-metrics phase-boundary` calls so a single workflow edit covers all six phases without touching any phase skill individually.

On `drift`: stop the phase, surface `diffs[]` verbatim, do not rationalize. Valid responses are an authorized override (`capture --override --reason X` followed by re-entry) or manual investigation. On `skipped`: log a warning and continue — first-time rollout and manual transitions produce this status; it is not an error.

## Non-goals

- **No global config lookup** for worktree applicability — `status.metadata.worktree_path` is the single source of truth.
- **No automatic remediation** on drift. `verify` reports; the caller decides. There is no `--fix` flag.
- **No backwards-compatibility shim** for rows missing newer invariant columns — missing columns are skipped during comparison.
- **No cross-plan handshakes** — each plan owns its own `handshakes.toon`.
- **No user-facing slash command** — this is a script-only surface consumed by the lifecycle protocols.

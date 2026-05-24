# Phase Handshake

Drift-detecting handshake between phase transitions. Each phase's completion captures a fingerprint of key invariants; the next phase's entry re-evaluates reality and refuses to continue on mismatch. Invariants are pluggable — adding one is a single tuple appended to a registry list.

> **Findings pipeline cross-reference**: the `pending_findings_blocking_count` invariant is the gate that backs the producer→store→consumer→gate flow. For the architectural synthesis (producers, store layout, consumer dispatch, extension contract), see [`ref-workflow-architecture/standards/findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md). This document owns the capture / verify mechanics, the row schema, and the structured error envelope.

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
handshakes[2]{phase,captured_at,worktree_applicable,override,override_reason,main_sha,main_dirty,main_dirty_files,worktree_sha,worktree_dirty,worktree_orphan,references_valid,task_state_hash,qgate_open_count,config_hash,pending_tasks_count,phase_steps_complete,pending_findings_by_type,pending_findings_blocking_count}:
  5-execute,2026-04-14T17:42:57Z,false,false,"",3823a0dd…,0,[],"","",false,b2c3d4…,a1b2c3…,0,d4e5f6…,0,"","build-error=0,test-failure=0,lint-issue=0,sonar-issue=0",0
  6-finalize,2026-04-14T18:01:12Z,false,false,"",15efe821…,0,[],"","",false,b2c3d4…,a1b2c3…,0,d4e5f6…,0,e7f8a9…,"build-error=0,test-failure=0,lint-issue=0,sonar-issue=0,pr-comment=0",0
```

Rationale for flat TOON over nested: simpler parsing, one row per phase, direct diff-ability. Adding a new invariant adds a new column; captures missing a column are treated as "not captured, skip comparison" during verify, so new invariants can roll out without invalidating history.

## Invariant registry

Defined in `_invariants.py` as `(name, applies_fn, capture_fn)` tuples. The parallel `INVARIANT_BLOCKING_SCOPE` map records each invariant's blocking scope (see [Blocking classification](#blocking-classification) below).

| Invariant | `applies_fn` | `capture_fn` | Blocking scope | Catches |
|---|---|---|---|---|
| `main_sha` | always | `git rev-parse HEAD` at main checkout root | `blocking_at: {5-execute}` (informational at every other boundary) | any commit change at the integration boundary |
| `main_dirty` | always | `git status --porcelain` line count at main checkout root | `blocking_at: {5-execute}` (informational at every other boundary) | uncommitted drift at the integration boundary |
| `main_dirty_files` | always | sorted list of dirty paths (filtered to exclude `.plan/`) | `blocking_at: {5-execute}` (informational at every other boundary) | layer-D leak detection (proper-superset rule in `_check_main_dirty_drift`) |
| `worktree_sha` | `status.metadata.worktree_path` non-null | `git rev-parse HEAD` inside worktree | `blocking_at_every_boundary` | worktree/main confusion |
| `worktree_dirty` | same as above | `git status --porcelain` line count inside worktree | `blocking_at_every_boundary` | uncommitted drift inside worktree |
| `worktree_orphan` | always | inverse-direction check (raises `WorktreeMetadataDrift` capture-time) | `blocking_at_every_boundary` | orphan worktree dir + metadata says no worktree |
| `references_valid` | always | SHA256 of `{present, top_level_is_dict, required_field_set}` from `manage-references read` | `blocking_at_every_boundary` | references.json deleted, corrupted to non-dict, or missing a required key (`branch`, `base_branch`, `modified_files`) |
| `task_state_hash` | always | SHA256 of sorted `(number, status, step_outcomes, depends_on)` from `manage-tasks list` | `blocking_at_every_boundary` | tasks silently mutated |
| `qgate_open_count` | always | `filtered_count` from `manage-findings qgate list --resolution pending --phase P` | `blocking_at_every_boundary` | Q-Gate bypass |
| `config_hash` | always | SHA256 of stable-key JSON of `manage-config plan phase-P get` output | `blocking_at_every_boundary` | config swapped mid-run |
| `pending_tasks_count` | always | row count from `manage-tasks list --status pending` | `blocking_at_every_boundary` | premature transition with fix tasks still pending |
| `phase_steps_complete` | always (no-op when phase has no declaration) | See [resolution rule](#phase_steps_complete-resolution) | `blocking_at_every_boundary` | silently skipped intra-phase steps |
| `task_graph_valid` | always | adjacency graph from `manage-tasks read` (cycle / dangling detection) | `blocking_at_every_boundary` | broken task graph blocking transition |
| `pending_findings_by_type` | always | per-type breakdown from `manage-findings list --type T --resolution pending` for every known type, serialized as `"build-error=N,test-failure=N,..."` | `blocking_at_every_boundary` | retrospective view of the queue at every boundary |
| `pending_findings_blocking_count` | always | sum of pending counts across the **per-phase** `blocking_finding_types` partition (see [resolution rule](#pending_findings_blocking_count-resolution)) | `blocking_at_every_boundary` | phase advance with blocking-type findings still pending |

### Blocking classification

Each invariant carries a `blocking_scope` value (in `INVARIANT_BLOCKING_SCOPE`) that controls whether drift between capture and re-verify counts toward `drift_count` and `diffs[]` (blocking) or is recorded passively in `handshakes.toon` as informational only. Three classifications are recognised:

| Classification | Effect on `cmd_verify` |
|---|---|
| `'blocking_at_every_boundary'` | Drift at any phase boundary raises `status: drift` and exits non-zero under `--strict`. Pre-classification default behaviour for every invariant. |
| `frozenset({...phase-keys...})` | Drift is blocking only at the named phase keys (the `--phase` argument value passed to `phase_handshake verify` — by the handshake's call convention this is the *captured* phase whose row is being re-verified, i.e. the phase the orchestrator is transitioning OUT of). Informational at every other phase. Example: `frozenset({'5-execute'})` blocks at the `5-execute → 6-finalize` boundary (`verify --phase 5-execute`). |
| `'informational_only'` | Drift is never blocking; the column is captured for retrospective analysis only. |

**Default for unmapped invariants**: `'blocking_at_every_boundary'`. New invariants added to `INVARIANTS` without a corresponding `INVARIANT_BLOCKING_SCOPE` entry retain the strict semantics until they are explicitly relaxed — `is_invariant_blocking_at_phase()` fails safe to blocking.

**`main_sha` / `main_dirty` / `main_dirty_files` rationale**: these three invariants describe state of the integration target branch (`main`/`master`), which can change between planning-phase boundaries (1→2, 2→3, 3→4, 4→5) for reasons unrelated to the in-flight plan — an unrelated commit lands on main during a long-paused planning phase, the operator's local main pulls in upstream changes, etc. Treating those changes as blocking forces a manual override / re-capture loop with no corresponding correctness gain: the planning artefacts (request, outline, task list) do not depend on the main SHA. At the `5-execute → 6-finalize` boundary, however, `main_sha` change DOES matter — it can invalidate the integration premise the just-built changes were merged on top of — so the three columns remain blocking there.

**Informational rows are persisted, not dropped**: classification affects *drift-counting*, not *persistence*. The `capture` output and `list` output continue to include every captured invariant column (including informational rows for `main_sha`/`main_dirty`/`main_dirty_files`) so retrospective analysis sees the full state at every boundary. `cmd_verify` returns informational drift in a separate `informational_diffs[]` payload alongside `informational_count` so callers that want to surface it explicitly can; the strict-exit path and the orchestrator's drift-recovery branch only ever read `drift_count` / `diffs[]`.

**Guarded boundaries for `pending_findings_blocking_count`** (a separate axis from blocking classification): the capture-time exception path described in [`pending_findings_blocking_count` resolution](#pending_findings_blocking_count-resolution) is orthogonal to the classification scheme above. The exception fires only at the configured guarded boundaries regardless of classification; the classification controls whether *value-drift* between capture and re-verify is reported as blocking drift or as informational drift.

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

### `pending_findings_blocking_count` resolution

The blocking-finding invariant is a **per-phase** partition: each phase decides which finding types — out of the 12-type taxonomy in `tools-file-ops/scripts/constants.py` — count as blockers for advancing past that phase. The partition lives in `marshal.json` at `plan.phase-{phase}.blocking_finding_types` (a list of finding-type strings).

**Resolution rule:**

1. Read `plan.phase-{phase}.blocking_finding_types` via `manage-config plan phase-{phase} get --field blocking_finding_types`. If the slot is unset, no types are considered blocking and the column captures `0`.
2. For each configured blocking type `T`, query the count of `pending` findings via `manage-findings list --plan-id X --type T --resolution pending` and sum the per-type `filtered_count` values.
3. The resolutions counted as **resolved** (and therefore non-blocking) are: `fixed`, `suppressed`, `accepted`, `taken_into_account`. Only `pending` contributes to the count.
4. The companion `pending_findings_by_type` row captures the count for **every** known type — independent of the phase's blocking partition — so retrospective analysis sees the full queue regardless of what each phase chose to gate on.

**Capture-time behavior:**

- **Pass** (count is `0`, OR `phase` is not a guarded boundary): the capture function returns the integer count and the column is recorded normally. Every capture point reads the row — the value carries informational weight at every boundary even when no block fires.
- **Fail** (count is `> 0` AND `phase` is a guarded boundary): the capture function raises `BlockingFindingsPresent(phase, blocking_count, per_type, blocking_types)`. `cmd_capture` catches it and returns a structured error payload **without writing a row**:

```toon
status: error
error: blocking_findings_present
plan_id: X
phase: 6-finalize
blocking_count: 2
blocking_types[5]:
  - build-error
  - test-failure
  - lint-issue
  - sonar-issue
  - qgate
per_type{build-error,test-failure,lint-issue,sonar-issue,qgate}:
  0,1,0,1,0
message: "pending_findings_blocking_count failed for phase '6-finalize': ..."
```

**Guarded boundaries:**

| Boundary | Where the strict-verify check fires |
|---|---|
| `5-execute → 6-finalize` | `manage-status transition --completed 5-execute` inlines `phase_handshake verify --phase 5-execute --strict`. On drift the transition returns the drift TOON, refuses to advance state, and exits 1 — mirroring the standalone strict-verify exit semantics. |
| `automated-review → branch-cleanup` (intra-finalize) | the `phase-6-finalize` orchestrator re-issues `phase_handshake capture --phase 6-finalize` between the two finalize sub-steps |
| `sonar-roundtrip → next` (intra-finalize) | same — the orchestrator re-issues capture between sub-steps |

Every other capture point (phases `1-init` through `5-execute`, plus finalize sub-steps not listed above) reads the row but does **not** raise — captures persist with the integer count for retrospective analysis. The blocking decision is *strictly* opt-in per the boundary set.

**Verify-time behavior:** if the observed re-capture raises `BlockingFindingsPresent`, `cmd_verify` surfaces it as a `drift` on the `pending_findings_blocking_count` column with an `blocking(count=...,blocking_types=...,per_type=...)` observed value. `--strict` turns this into a non-zero exit so the caller stops the boundary advance.

**Default seed:** `marshall-steward` writes the default partition into each phase slot on first wizard run (idempotent — only writes when `blocking_finding_types` is absent):

| Block at every phase boundary | Block only inside `6-finalize` | Never block (long-lived knowledge types) |
|---|---|---|
| `build-error`, `test-failure`, `lint-issue`, `sonar-issue`, `qgate` | `pr-comment` | `insight`, `tip`, `best-practice`, `improvement` |

Projects override by editing `marshal.json` directly. See `marshall-steward/scripts/determine_mode.py::seed_blocking_finding_types` for the seed implementation.

### Adding a new invariant

1. Add a capture helper in `_invariants.py`
2. Append a tuple `(name, applies_fn, capture_fn)` to `INVARIANTS`
3. Add the column name to `HANDSHAKE_FIELDS` in `_handshake_store.py`
4. Add a drift test case

No changes are required in `_handshake_commands.py`, `phase_handshake.py`, or any phase skill — unless the new invariant needs to raise a capture-time gate (as `phase_steps_complete` does). In that case, define a dedicated exception in `_invariants.py` and teach `cmd_capture`/`cmd_verify` to catch it, mirroring the `PhaseStepsIncomplete` pattern.

### Worktree applicability

`worktree_sha` and `worktree_dirty` apply iff `status.metadata.worktree_path` is set. `phase-1-init` writes that field when a plan uses a worktree and omits it otherwise, so per-plan worktree usage is already the single source of truth — the handshake does not look at global config.

### `worktree_metadata_drift` capture-time error

When `metadata.use_worktree` is truthy, capture asserts that `metadata.worktree_path` is non-empty AND filesystem-resolvable (the directory exists AND `git -C {path} rev-parse --show-toplevel` returns the same canonical path). When the assertion fails, `cmd_capture` returns a structured error payload **without writing a row**:

```toon
status: error
error: worktree_metadata_drift
plan_id: X
phase: 5-execute
worktree_dir: /path/to/worktree
use_worktree: true
message: "worktree_metadata_drift: metadata.use_worktree is set but worktree_path is unresolved"
```

**Trigger condition:** the plan opted into an isolated worktree (`metadata.use_worktree` truthy) but `metadata.worktree_path` is empty, points at a non-existent directory, or points at a path that is not a git worktree root.

**Detection fingerprint:** `phase_handshake` reports `metadata.use_worktree=None` (the metadata read swallowed a non-resolving notation and returned `{}`) while `manage-status read` shows a non-empty `metadata.use_worktree` value. The two readings disagreeing is the signature of this failure class.

**Root cause and resolution:** historically this error also fired spuriously when `metadata.use_worktree` was stored as the JSON string `"true"` instead of the boolean `true`. `manage-status metadata --set` now coerces boolean-typed metadata keys (`use_worktree`) from the raw CLI string to a JSON boolean before storage, so the stored value is always a proper boolean. A persistent `worktree_metadata_drift` after that fix indicates a genuine unresolved worktree path — repair `metadata.worktree_path` (re-run phase-5-execute Step 2.5 materialization) and re-enter the phase.

## Integration with phase lifecycle

The actual call sites for `capture` and `verify` are the orchestrator workflow files [`plan-marshall:plan-marshall:workflow/planning.md`](../workflow/planning.md) (phases 1-init through 4-plan boundaries) and [`plan-marshall:plan-marshall:workflow/execution.md`](../workflow/execution.md) (4-plan→5-execute fallback and 5-execute→6-finalize boundaries). Each `manage-metrics phase-boundary` invocation in those workflows is followed by a `phase_handshake capture --phase {prev_phase}` call. For non-guarded next-phase entries, the workflow runs a standalone `phase_handshake verify --phase {prev_phase} --strict` before any phase-specific work begins. For guarded boundaries (next phase in `_BLOCKING_BOUNDARIES`, currently `{'6-finalize'}`), the strict-verify step is inlined into `manage-status transition --completed {prev_phase}` so the workflow issues a single atomic call instead of a verify+transition pair — the transition refuses to advance state and exits 1 on drift, mirroring the standalone verify --strict contract.

The abstract contract is documented in [`../../ref-workflow-architecture/standards/phase-lifecycle.md`](../../ref-workflow-architecture/standards/phase-lifecycle.md): the Phase Completion Protocol calls `capture` as its final step; the Phase Entry Protocol calls `verify --strict` immediately after the Q-Gate check. The orchestrator workflows are the canonical implementation of that contract — they wire capture/verify alongside the existing `manage-metrics phase-boundary` calls so a single workflow edit covers all six phases without touching any phase skill individually.

On `drift`: stop the phase, surface `diffs[]` verbatim, do not rationalize. Valid responses are an authorized override (`capture --override --reason X` followed by re-entry) or manual investigation. On `skipped`: log a warning and continue — first-time rollout and manual transitions produce this status; it is not an error.

## Non-goals

- **No global config lookup** for worktree applicability — `status.metadata.worktree_path` is the single source of truth.
- **No automatic remediation** on drift. `verify` reports; the caller decides. There is no `--fix` flag.
- **No backwards-compatibility shim** for rows missing newer invariant columns — missing columns are skipped during comparison.
- **No cross-plan handshakes** — each plan owns its own `handshakes.toon`.
- **No user-facing slash command** — this is a script-only surface consumed by the lifecycle protocols.

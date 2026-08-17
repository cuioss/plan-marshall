# Phase Handshake

Drift-detecting handshake between phase transitions. Each phase's completion captures a fingerprint of key invariants; the next phase's entry re-evaluates reality and refuses to continue on mismatch. Invariants are pluggable — adding one is a single tuple appended to a registry list.

> **Findings pipeline cross-reference**: the `pending_findings_blocking_count` invariant is the gate that backs the producer→store→consumer→gate flow. For the architectural synthesis (producers, store layout, consumer dispatch, extension contract), see [`ref-workflow-architecture/standards/findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md). This document owns the capture / verify mechanics, the row schema, and the structured error envelope.

![Sequence diagram of the phase-handshake protocol. At phase N completion the orchestrator runs phase_handshake capture, which evaluates an invariant registry (main_sha, dirty count, task_state_hash, qgate_open_count, config_hash, pending_findings_blocking_count, phase_steps_complete) and writes a row to handshakes.toon. At phase N+1 entry the orchestrator runs phase_handshake verify with strict mode; the script reads the captured row, re-runs the invariants against live state, diffs, and returns either ok (continue), drift (surface diffs, exit 1, refuse to advance), or skipped (log warning, continue).](../../../../../../doc/resources/diagrams/handshake-protocol.svg)

## Why

Phase skills occasionally drift between what they *report* they did and what the next phase *observes*. Examples: a task summary claims file edits while the tree is clean; a phase advances while Q-Gate findings are still open; phase config changes mid-run. A lesson that prescribes "run `git status` manually" is a ritual, easy to skip. The handshake replaces the ritual with a mechanical guardrail.

## Script surface

Executor notation: `plan-marshall:plan-marshall:phase_handshake`

```text
phase_handshake capture        --plan-id X --phase P [--override --reason "text"]
phase_handshake verify         --plan-id X --phase P [--strict]
phase_handshake findings-check --plan-id X --phase P
phase_handshake list           --plan-id X
phase_handshake clear          --plan-id X --phase P
```

All subcommands return TOON.

### `capture`

Runs every applicable invariant and writes (or replaces) the row for `phase` in `handshakes.toon`. `--override --reason X` marks the row as an authorized override.

```toon
status: success
plan_id: X
phase: 5-execute
override: false
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

#### Loop-back auto-override (sanctioned re-entry drift)

A loop-back (`manage-status set-phase` to a phase that precedes the current one) guarantees drift by construction: the re-entered phases legitimately change the invariants recorded at the pre-loop-back capture, so the next guarded-boundary verify reports `status: drift` every time. `cmd_set_phase` therefore persists `metadata.loop_back_reentry = {from_phase, to_phase, at}` on every backward move, and `cmd_transition`'s inline guard consumes it at the **very next guarded boundary check, regardless of whether that check found drift** (the consume-on-next-guarded-verification contract):

- **Drift + marker** (the expected case): the transition re-captures the handshake automatically with `override=True` and the recorded reason `loop-back re-entry auto-override (scheduled by {from_phase} loop_back)`, clears the marker (persisted immediately, so the override fires exactly once per scheduled loop-back), emits a decision-log WARNING carrying the drift diff summary, and proceeds.
- **Clean verify + marker**: the marker is consumed without a recapture — the transition pops it, persists the cleared metadata, and emits a decision-log INFO line noting the marker was consumed on a clean guarded verification. This prevents a stale marker from surviving a clean boundary and incorrectly auto-overriding a later, genuinely unscheduled drift.

Scope limits:

- Expected-by-construction drift on a sanctioned loop-back re-entry is the ONLY auto-resolved case. Drift WITHOUT the marker keeps the blocking behavior unchanged — the operator-facing drift protocol below applies only to unscheduled drift.
- The marker never survives past the first guarded boundary check after the loop-back — it is consumed on that check's outcome either way (recapture on drift, plain clear on clean).
- The worktree-resolution, dirty-boundary and self-contradictory-row refusals (`VERIFY_REFUSAL_ERRORS`: `worktree_unresolved`, `worktree_metadata_drift`, `main_checkout_dirtied_during_plan`, `worktree_dirty_at_boundary`, `main_capture_read_the_worktree`) are NEVER bypassed by the marker — only invariant drift is auto-resolved.
- A failed re-capture blocks the transition (fail closed) with the re-capture's error payload.

### `findings-check`

Read-only single-invariant gate. Evaluates ONLY the `pending_findings_blocking_count` invariant (via [resolution rule](#pending_findings_blocking_count-resolution)) for `phase` and writes **no** handshake row. Unlike `capture` it never runs `capture_all`, so `phase_steps_complete` is never evaluated — the verb cannot short-circuit on `phase_steps_incomplete`. It exists for the pre-merge finalize gate (`branch-cleanup` § "Pre-merge blocking-findings store gate"), where the downstream finalize steps (`record-metrics`, `archive-plan`) have not run yet so the composite `capture` gate would always fail on `phase_steps_incomplete` before ever evaluating the blocking-findings invariant.

On a clean count:

```toon
status: success
plan_id: X
phase: 6-finalize
blocking_count: 0
```

On a pending blocking-type finding the verb returns the **same** structured error payload `capture` emits for `blocking_findings_present` (`blocking_count`, `blocking_types`, `per_type`, `message`), so the pre-merge `findings-check` caller and the composite `capture` gate present an interchangeable envelope. There is no `--strict` flag — the verdict is carried entirely in the TOON `status` field, and a `status: error` payload still exits 0 (mirroring the `capture` exit convention the callers already handle).

**Fails closed on an unevaluable invariant.** When the underlying blocking-count query cannot run (executor unreachable / partial query failure, surfaced as a `None` count), the verb returns `status: error, error: query_failed` rather than `status: success`. As a gate verb its sole output is the go/no-go verdict, so it cannot fail open: an unevaluable invariant must halt the merge, not silently proceed past the pre-merge gate in `branch-cleanup`. (The composite `capture` records the same `None` as an empty column for retrospective analysis — acceptable there because `capture`'s gate is the `BlockingFindingsPresent` raise, not the return value.) The caller treats `query_failed` as a halt-and-retry environmental failure (no findings to triage, no loop-back).

### `list` / `clear`

`list` returns every row in `handshakes.toon` projected to the canonical field set. `clear --phase P` removes exactly the row for `P` (others remain intact).

## Storage

File: `<base>/plans/{plan_id}/handshakes.toon` (owned exclusively by `phase_handshake`). Flat TOON, one row per phase, uniform array serialized via `toon_parser.serialize_toon`.

```toon
plan_id: recipe-plugin-compliance
handshakes[2]{phase,captured_at,override,override_reason,main_sha,main_dirty,main_dirty_files,worktree_sha,worktree_dirty,references_valid,task_state_hash,qgate_open_count,config_hash,unfinished_tasks_count,phase_steps_complete,pending_findings_by_type,pending_findings_blocking_count,pr_title_present}:
  5-execute,2026-04-14T17:42:57Z,false,"",3823a0dd…,0,[],"","",b2c3d4…,a1b2c3…,0,d4e5f6…,0,"","build-error=0,test-failure=0,lint-issue=0,sonar-issue=0",0,9f8e7d…
  6-finalize,2026-04-14T18:01:12Z,false,"",15efe821…,0,[],"","",b2c3d4…,a1b2c3…,0,d4e5f6…,0,e7f8a9…,"build-error=0,test-failure=0,lint-issue=0,sonar-issue=0,pr-comment=0",0,9f8e7d…
```

Rationale for flat TOON over nested: simpler parsing, one row per phase, direct diff-ability. Adding a new invariant adds a new column; captures missing a column are treated as "not captured, skip comparison" during verify, so new invariants can roll out without invalidating history.

## Invariant registry

Defined in `_invariants.py` as `(name, applies_fn, capture_fn)` tuples. The parallel `INVARIANT_BLOCKING_SCOPE` map records each invariant's blocking scope (see [Blocking classification](#blocking-classification) below).

| Invariant | `applies_fn` | `capture_fn` | Blocking scope | Catches |
|---|---|---|---|---|
| `main_sha` | always | `git rev-parse HEAD` at the main checkout root ([resolved main-anchored](#main-scoped-resolution)) | `blocking_at: {5-execute}` (informational at every other boundary) | any commit change at the integration boundary |
| `main_dirty` | always | `git status --porcelain` line count at the main checkout root ([resolved main-anchored](#main-scoped-resolution)) | `blocking_at: {5-execute}` (informational at every other boundary) | uncommitted drift at the integration boundary |
| `main_dirty_files` | always | sorted list of dirty paths at the main checkout root ([resolved main-anchored](#main-scoped-resolution); `.plan/` filtered on git trackedness — untracked plan state dropped, a tracked `.plan/` file retained as a real leak) | `blocking_at: {1-init, 2-refine, 3-outline, 4-plan}` (informational at 5-execute and 6-finalize) | layer-D leak detection (proper-superset rule in `_check_main_dirty_drift`) |
| `worktree_sha` | `_worktree_in_use` (delegates to `_worktree_materialized` with `phase=None` — see [Worktree applicability](#worktree-applicability)) | `git rev-parse HEAD` inside worktree | `blocking_at: {1-init, 2-refine, 3-outline, 4-plan}` (informational at 5-execute and 6-finalize) | worktree/main confusion |
| `worktree_dirty` | same as above | `git status --porcelain` line count inside worktree | `blocking_at: {1-init, 2-refine, 3-outline, 4-plan}` (informational at 5-execute and 6-finalize) | uncommitted drift inside worktree |
| `references_valid` | always | SHA256 of `{present, top_level_is_dict, required_field_set}` from `manage-references read` | `blocking_at_every_boundary` | references.json deleted, corrupted to non-dict, or missing a required key (`branch`, `base_branch`) |
| `task_state_hash` | always | SHA256 of sorted `(number, status, step_outcomes, depends_on)` from `manage-tasks list` | `blocking_at_every_boundary` | tasks silently mutated |
| `qgate_open_count` | always | `filtered_count` from `manage-findings qgate list --resolution pending --phase P` | `blocking_at_every_boundary` | Q-Gate bypass |
| `config_hash` | always | SHA256 of stable-key JSON of the `plan` section of `marshal.json` (phase-independent — the same config hashes the same at every boundary) | `blocking_at_every_boundary` | config swapped mid-run |
| `unfinished_tasks_count` | always | union count from `manage-tasks loop-exit-guard` (`pending_count + in_progress_count`) | `blocking_at_every_boundary` | premature transition with fix tasks still pending OR a mid-flight task abandoned by a previous dispatch |
| `phase_steps_complete` | always (no-op when phase has no declaration) | See [resolution rule](#phase_steps_complete-resolution) | `blocking_at_every_boundary` | silently skipped intra-phase steps |
| `task_graph_valid` | always | adjacency graph from `manage-tasks read` (cycle / dangling detection) | `blocking_at_every_boundary` | broken task graph blocking transition |
| `pending_findings_by_type` | always | per-type breakdown from `manage-findings list --type T --resolution pending` for every known type, serialized as `"build-error=N,test-failure=N,..."` | `blocking_at_every_boundary` | retrospective view of the queue at every boundary |
| `pending_findings_blocking_count` | always | sum of pending counts across the **hardcoded ACTIONABLE** finding-type set (see [resolution rule](#pending_findings_blocking_count-resolution)) | `blocking_at_every_boundary` | phase advance with actionable findings still pending |
| `pr_title_present` | always (no-op / empty column at `1-init` via internal phase gate) | present-sentinel hash `_hash_dict({'present': True})` of `metadata.pr_title`; raises `PrTitleMissing` when empty/missing at `2-refine`+ (see [error payload](#pr_title_missing-capture-time-error)) | `blocking_at_every_boundary` | missing or empty PR title from refine onward |

### Blocking classification

Each invariant carries a `blocking_scope` value (in `INVARIANT_BLOCKING_SCOPE`) that controls whether drift between capture and re-verify counts toward `drift_count` and `diffs[]` (blocking) or is recorded passively in `handshakes.toon` as informational only. Three classifications are recognised:

| Classification | Effect on `cmd_verify` |
|---|---|
| `'blocking_at_every_boundary'` | Drift at any phase boundary raises `status: drift` and exits non-zero under `--strict`. Pre-classification default behaviour for every invariant. |
| `frozenset({...phase-keys...})` | Drift is blocking only at the named phase keys (the `--phase` argument value passed to `phase_handshake verify` — by the handshake's call convention this is the *captured* phase whose row is being re-verified, i.e. the phase the orchestrator is transitioning OUT of). Informational at every other phase. Example: `frozenset({'5-execute'})` blocks at the `5-execute → 6-finalize` boundary (`verify --phase 5-execute`). |
| `'informational_only'` | Drift is never blocking; the column is captured for retrospective analysis only. |

**Default for unmapped invariants**: `'blocking_at_every_boundary'`. New invariants added to `INVARIANTS` without a corresponding `INVARIANT_BLOCKING_SCOPE` entry retain the strict semantics until they are explicitly relaxed — `is_invariant_blocking_at_phase()` fails safe to blocking.

**`main_sha` / `main_dirty` rationale**: these two invariants describe state of the integration target branch (`main`/`master`), which can change between planning-phase boundaries (1→2, 2→3, 3→4, 4→5) for reasons unrelated to the in-flight plan — an unrelated commit lands on main during a long-paused planning phase, the operator's local main pulls in upstream changes, etc. Treating those changes as blocking forces a manual override / re-capture loop with no corresponding correctness gain: the planning artefacts (request, outline, task list) do not depend on the main SHA. They are therefore scoped `blocking_at: {5-execute}` — blocking only at the `5-execute → 6-finalize` boundary, where a `main_sha` change DOES matter because it can invalidate the integration premise the just-built changes were merged on top of.

**`main_dirty_files` / `worktree_sha` / `worktree_dirty` rationale**: these three worktree-state drift invariants block at the *planning-phase* boundaries (1→2, 2→3, 3→4, 4→5) — scope `_WORKTREE_STATE_DRIFT_BLOCKING_PHASES` = `{1-init, 2-refine, 3-outline, 4-plan}` — and are informational at the phase-5+ boundaries. The reasoning is the inverse of `main_sha`/`main_dirty`: under the move-based, cwd-pinned hermetic worktree model (ADR-002), the worktree directory is materialized and the plan dir moved in at phase-5 start, after which the orchestrator's cwd IS the worktree and never leaves it. The sideways worktree-SHA/dirty comparison and the layer-D leak-into-main guard (`main_dirty_files`) are therefore structurally moot at the `5-execute → 6-finalize` boundary — plan work lands in the worktree by construction — but remain blocking at the planning-phase boundaries that still run on the main checkout, where a leak could legitimately occur.

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

- push
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

The blocking-finding invariant uses a **fixed, hardcoded** actionable-vs-knowledge rule defined as a constant in `plan-marshall/scripts/_invariants.py` — there is no per-phase configuration partition and no `marshal.json` key. Out of the 12-type taxonomy in `tools-file-ops/scripts/constants.py`, the **ACTIONABLE** set — `build-error`, `test-failure`, `lint-issue`, `sonar-issue`, `qgate`, `pr-comment` — counts as blockers; the **KNOWLEDGE** set — `insight`, `tip`, `best-practice`, `improvement` — never blocks. This is not a naive "any pending finding blocks" rule: knowledge types are excluded by the fixed actionable-set membership test.

**Resolution rule:**

1. The actionable finding-type set is the hardcoded constant in `_invariants.py`; no `marshal.json` read occurs. Knowledge types are never counted.
2. For each actionable type `T`, query the count of `pending` findings via `manage-findings list --plan-id X --type T --resolution pending` and sum the per-type `filtered_count` values. The `qgate` actionable entry is routed through the aggregated per-phase qgate query (see [qgate aggregation contract](../../ref-workflow-architecture/standards/findings-pipeline.md#qgate-aggregation-contract)).
3. The resolutions counted as **resolved** (and therefore non-blocking) are: `fixed`, `suppressed`, `accepted`, `taken_into_account`, `rejected` (the pending query filters `--resolution pending`, so every non-`pending` resolution — `rejected` included — is structurally non-blocking). Only `pending` contributes to the count.
4. The companion `pending_findings_by_type` row captures the count for **every** known type — independent of the actionable set — so retrospective analysis sees the full queue regardless of which types gate the boundary.

**Capture-time behavior:**

- **Pass** (count is `0`, OR `phase` is not a guarded boundary): the capture function returns the integer count and the column is recorded normally. Every capture point reads the row — the value carries informational weight at every boundary even when no block fires.
- **Fail** (count is `> 0` AND `phase` is a guarded boundary): the capture function raises `BlockingFindingsPresent(phase, blocking_count, per_type, blocking_types)`. `cmd_capture` catches it and returns a structured error payload **without writing a row**:

```toon
status: error
error: blocking_findings_present
plan_id: X
phase: 6-finalize
blocking_count: 2
blocking_types[6]:
  - build-error
  - test-failure
  - lint-issue
  - sonar-issue
  - qgate
  - pr-comment
per_type{build-error,test-failure,lint-issue,sonar-issue,qgate,pr-comment}:
  0,1,0,1,0,0
message: "pending_findings_blocking_count failed for phase '6-finalize': ..."
```

**Guarded boundaries:**

| Boundary | Where the blocking-findings check fires |
|---|---|
| finalize merge (pre-merge) | `phase-6-finalize/standards/branch-cleanup.md` § "Pre-merge blocking-findings store gate" issues `phase_handshake findings-check --phase 6-finalize` before the merge. A pending actionable finding returns `blocking_findings_present` (`status: error`, exit 0 — parse the TOON status), and the merge is blocked; `query_failed` blocks fail-closed. |
| finalize completion | `manage-status transition --completed 6-finalize` and a normal-completion `manage-status archive` call `_invariants.assert_finalize_findings_clean`, which evaluates this same invariant at `6-finalize` and refuses to mark the plan complete while an actionable finding is pending. |

Both firing sites evaluate the **single** blocking-findings invariant (via `findings-check` or `assert_finalize_findings_clean`) rather than the composite `capture`: mid-finalize the downstream steps have not all run, so a composite `capture` would short-circuit on `phase_steps_incomplete` before it ever reached the blocking-findings invariant — leaving the gate inoperative. The single-invariant path evaluates only `pending_findings_blocking_count`, so it cannot short-circuit.

**The arming condition is a state, not a call.** The blocking-findings raise fires ONLY on a `capture`/`findings-check` carrying `--phase 6-finalize`. Historically no orchestration step issued one — a `phase_handshake capture --phase 6-finalize` was never emitted, and the intra-finalize `findings-check` re-issue this table once claimed was never wired — so the finalize-phase gate was inert fleet-wide: a plan could complete or merge with actionable findings still `pending`, and *"the gate never ran"* was indistinguishable from *"the gate passed"*. The two firing sites above close that: the pre-merge `findings-check` is a call issued at a fixed point in `branch-cleanup`, and the completion boundary asserts the clean STATE unconditionally (armed by *reaching* the boundary), so a missing call is no longer a silent pass.

**The `5-execute → 6-finalize` transition is NOT a blocking-findings firing site.** `manage-status transition --completed 5-execute` inlines `phase_handshake verify --phase 5-execute --strict`, which detects *drift* on the captured `5-execute` row (including drift on the `pending_findings_blocking_count` column) and refuses to advance on drift. It does **not** raise `blocking_findings_present`: that raise fires only at `phase == '6-finalize'`, and the self-review findings the finalize gate exists to catch are filed *during* finalize, after this boundary. The blocking-findings gate therefore lives at the two finalize sites above, not at finalize entry.

Every other capture point (phases `1-init` through `5-execute`, plus finalize sub-steps not listed above) reads the row but does **not** raise — captures persist with the integer count for retrospective analysis. The blocking decision is *strictly* opt-in per the boundary set.

**Verify-time behavior:** if the observed re-capture raises `BlockingFindingsPresent`, `cmd_verify` surfaces it as a `drift` on the `pending_findings_blocking_count` column with an `blocking(count=...,blocking_types=...,per_type=...)` observed value. `--strict` turns this into a non-zero exit so the caller stops the boundary advance.

**Fixed actionable-vs-knowledge classification** (hardcoded in `_invariants.py`; not configurable, not seeded into `marshal.json`):

| ACTIONABLE (block when pending at a guarded boundary) | KNOWLEDGE (never block) |
|---|---|
| `build-error`, `test-failure`, `lint-issue`, `sonar-issue`, `qgate`, `pr-comment` | `insight`, `tip`, `best-practice`, `improvement` |

`pr-comment` is in the actionable set but, because the only guarded boundaries are the three finalize boundaries (below), it can only block once a PR exists. See `plan-marshall/scripts/_invariants.py` for the hardcoded set.

### Adding a new invariant

1. Add a capture helper in `_invariants.py`
2. Append a tuple `(name, applies_fn, capture_fn)` to `INVARIANTS`
3. Add the column name to `HANDSHAKE_FIELDS` in `_handshake_store.py`
4. Add a drift test case

No changes are required in `_handshake_commands.py`, `phase_handshake.py`, or any phase skill — unless the new invariant needs to raise a capture-time gate (as `phase_steps_complete` does). In that case, define a dedicated exception in `_invariants.py` and teach `cmd_capture`/`cmd_verify` to catch it, mirroring the `PhaseStepsIncomplete` pattern.

### Worktree applicability

A single materialization predicate (`_worktree_materialized` in `_invariants.py`) decides whether the worktree is in play, and both the invariant-applicability gate (`worktree_sha` / `worktree_dirty`) and the phase-entry worktree assertion (`_resolve_worktree_assertion`) consult it, so the two surfaces can never disagree. The worktree counts as materialized when **either** `status.metadata.worktree_path` is present and non-empty (the worktree directory was created and the path persisted at phase-5 Step 2.5), **or** the active phase is one of the materialization phases (`5-execute`, `6-finalize`) — the phase term covers the transient phase-5 window between phase entry and Step 2.5's path backfill, when the path is still empty but the worktree is conceptually already in play.

The invariant-applicability gate (`_worktree_in_use`) evaluates the predicate with `phase=None`, so it keys purely on the persisted `worktree_path`; the capture functions return `None` for an unpopulated path, so a pre-materialization capture records an empty column. The phase-entry assertion evaluates the predicate with the live phase, so it tolerates the empty-path window on phases 1-4 (per-plan worktree usage remains the single source of truth — the handshake never looks at global config) and fails closed from phase-5 onward.

### Main-scoped resolution

A column named for main is read from main. The three `main_*` captures resolve their tree through `_invariants._main_repo_root()`, whose property is **worktree-invariance**: it names the same main checkout from any tree in the repository, a linked worktree included. Under a base-dir override (`PLAN_BASE_DIR` / `set_base_dir()`) it honours the override; otherwise `git rev-parse --git-common-dir` names main's `.git` even from inside a linked worktree. Precedence has the shape `marketplace_paths.resolve_main_anchored_path` uses — override first, then git — that being the single sanctioned main-anchored exception (ADR-002).

⚠ Worktree-invariance is the accurate claim, not cwd-independence: `git rev-parse` runs in the process cwd, so the resolver names whichever *repository* the process is in. Within one repository it is invariant across main and every worktree, which is exactly what these columns need.

The distinction from the cwd-relative resolver is load-bearing. Every *other* resolution here is uniform cwd-relative, including `_invariants._current_repo_root()` — the resolver `_run_script` uses to reach the worktree-resident executor and the plan state moved in at phase-5 start. That one follows the pinned worktree **by design**, so a `main_*` column must not share it: from phase-5 onward the orchestrator's cwd IS the worktree, and a cwd-derived `main_sha` would silently record a feature-branch commit under a name that claims main. Reading one tree under both column names is what the [`main_capture_read_the_worktree`](#main_capture_read_the_worktree-capture-time-error) refusal catches.

When the main checkout cannot be resolved at all (not a git repository, git unavailable) the resolver returns `None` and the capture leaves the column **empty** — the registry's "not applicable" contract. It never falls back to the ambient working directory: an unresolvable main checkout is *unknown*, and filling the column with whichever tree the process happens to occupy is exactly the mis-resolution the main-anchored path exists to end.

### `main_capture_read_the_worktree` capture-time error

`main_sha` and `worktree_sha` describe two different trees. When they hold the same commit **and** both resolved to the same directory, one tree is being reported under two names — the row disproves itself with no external reference. `capture_all` raises `MainCaptureReadTheWorktree` and `cmd_capture` returns a structured error payload **without writing a row**:

```toon
status: error
error: main_capture_read_the_worktree
plan_id: X
phase: 5-execute
sha: 3823a0dd…
main_root: /repo/.plan/local/worktrees/my-plan
worktree_path: /repo/.plan/local/worktrees/my-plan
message: "phase 5-execute: the main-scoped capture read the plan worktree — main_sha == worktree_sha (3823a0dd…) and both resolved to /repo/.plan/local/worktrees/my-plan. A column named for main must be read from main; repair the main-anchored resolution (_main_repo_root) before re-entering the phase."
```

**Trigger condition:** both columns were captured — which is exactly "a `metadata.worktree_path` is persisted", since `worktree_sha` is gated on [`_worktree_in_use`](#worktree-applicability), a predicate that keys on that path and does **not** read `use_worktree` — AND they hold the same commit AND `_main_repo_root()` resolves to the same directory as `worktree_path`.

⛔ **Equal commits alone are NOT the trigger.** Two *distinct* trees can legitimately hold one commit: a worktree-backed plan whose feature branch carries no commit of its own has its HEAD still on the commit it branched from. That state is produced by the shipped flow — `phase-5-execute` Step 2.5 materializes the worktree unconditionally, *before* the `early_terminate` short-circuit, so an analysis-only plan never commits on its branch — and refusing it would hard-block a legitimate boundary with no override escape. Such a row is permitted and is **correct**: its `main_sha` genuinely is main's HEAD. The refusal is keyed on the same-tree resolution, which is the defect, not on the equality, which is only its symptom.

**Never fires on a plan with no worktree.** No persisted `worktree_path` means no `worktree_sha`, so there is nothing to compare.

**Resolution:** repair the main-anchored resolution ([above](#main-scoped-resolution)), then re-enter the phase. The payload's `main_root` and `worktree_path` name the two directories that collapsed.

`cmd_verify` returns the **same** payload from the same shared builder: `capture_all` runs the cross-field check itself, so a live re-capture that reproduces the state surfaces the refusal at the `capture_all` call rather than as a traceback. The error is in `VERIFY_REFUSAL_ERRORS`, so such a boundary refuses and is never auto-resolved by the [loop-back marker](#loop-back-auto-override-sanctioned-re-entry-drift).

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

### `pr_title_missing` capture-time error

The `pr_title_present` invariant guards that a commit-style PR title was authored at phase-2-refine Step 13 and persisted to `status.metadata.pr_title`, so phase-6-finalize `create-pr.md` has a deterministic `--title` source. At `1-init` the capture returns `None` (the title does not yet exist — refine authors it), so the column stays empty pre-refine. From `2-refine` onward, when `metadata.pr_title` is empty/missing/whitespace-only the capture raises `PrTitleMissing` and `cmd_capture` returns a structured error payload **without writing a row**:

```toon
status: error
error: pr_title_missing
plan_id: X
phase: 2-refine
message: "pr_title_present failed for phase '2-refine': metadata.pr_title is absent or empty — phase-2-refine Step 13 must author and persist a commit-style PR title via `manage-status metadata --set --field pr_title`"
```

**Trigger condition:** the active phase is `2-refine` or later AND `metadata.pr_title` is absent, empty, or whitespace-only (phase-2-refine skipped its Step 13 title-authoring obligation, or the field was clobbered downstream).

**Resolution:** re-run phase-2-refine Step 13 title authoring so a non-empty `pr_title` is persisted via `manage-status metadata --set --field pr_title`, then re-enter the phase. A present-sentinel hash (`_hash_dict({'present': True})`) encodes only the PRESENCE of the title, so a legitimate title edit between boundaries does NOT trip drift detection.

## Integration with phase lifecycle

The actual call sites for `capture` and `verify` are the orchestrator workflow files [`plan-marshall:plan-marshall:workflow/planning.md`](../workflow/planning.md) (phases 1-init through 4-plan boundaries) and [`plan-marshall:plan-marshall:workflow/execution.md`](../workflow/execution.md) (4-plan→5-execute fallback and 5-execute→6-finalize boundaries). Each `manage-metrics phase-boundary` invocation in those workflows is followed by a `phase_handshake capture --phase {prev_phase}` call. For non-guarded next-phase entries, the workflow runs a standalone `phase_handshake verify --phase {prev_phase} --strict` before any phase-specific work begins. For guarded boundaries (next phase in `_BLOCKING_BOUNDARIES`, currently `{'6-finalize'}`), the strict-verify step is inlined into `manage-status transition --completed {prev_phase}` so the workflow issues a single atomic call instead of a verify+transition pair — the transition refuses to advance state and exits 1 on drift, mirroring the standalone verify --strict contract.

The abstract contract is documented in [`../../ref-workflow-architecture/standards/phase-lifecycle.md`](../../ref-workflow-architecture/standards/phase-lifecycle.md): the Phase Completion Protocol calls `capture` as its final step; the Phase Entry Protocol calls `verify --strict` immediately after the Q-Gate check. The orchestrator workflows are the canonical implementation of that contract — they wire capture/verify alongside the existing `manage-metrics phase-boundary` calls so a single workflow edit covers all six phases without touching any phase skill individually.

On `drift`: stop the phase, surface `diffs[]` verbatim, do not rationalize. Valid responses are an authorized override (`capture --override --reason X` followed by re-entry) or manual investigation. Exception: expected-by-construction drift on a sanctioned loop-back re-entry is re-captured automatically with a recorded override reason (see [Loop-back auto-override](#loop-back-auto-override-sanctioned-re-entry-drift)) — the operator-facing drift protocol applies only to unscheduled drift. On `skipped`: log a warning and continue — first-time rollout and manual transitions produce this status; it is not an error.

## Non-goals

- **No global config lookup** for worktree applicability — the per-plan `_worktree_materialized` predicate (persisted `status.metadata.worktree_path` OR a materialization phase) is the single source, never global config.
- **No automatic remediation** on unscheduled drift. `verify` reports; the caller decides. There is no `--fix` flag. The one sanctioned exception is the [loop-back auto-override](#loop-back-auto-override-sanctioned-re-entry-drift), which re-captures with a recorded override reason exactly once per scheduled loop-back.
- **No backwards-compatibility shim** for rows missing newer invariant columns — missing columns are skipped during comparison.
- **No cross-plan handshakes** — each plan owns its own `handshakes.toon`.
- **No user-facing slash command** — this is a script-only surface consumed by the lifecycle protocols.

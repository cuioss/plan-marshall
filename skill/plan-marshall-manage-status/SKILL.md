---
name: plan-marshall-manage-status
description: Manage status.json files with phase tracking, metadata, and lifecycle operations for plans, the HEAD-bound and gap-class-bound merge-authorization record the pre-merge barrier gates on, the delete-plan lesson carry-back that resolves the corpus main-anchored and vetoes the deletion when a carried lesson did not land, plus the lean kind=orchestrator status store for orchestrator epics
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# Manage Status Skill

Manage status.json files with phase tracking, metadata, and lifecycle operations. Handles plan status storage (JSON), phase operations, metadata management, plan discovery, phase transitions, archiving, and routing. Additionally serves the lean `kind=orchestrator` status store: `create`/`read`/`metadata` accept `--store orchestrator`, and `update-field` sets the orchestrator schema's top-level fields — no phase-transition machinery applies to the orchestrator kind (see [status-lifecycle.md](standards/status-lifecycle.md)).

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Only valid phase status values: `pending`, `in_progress`, `done`
- Phase transitions must use `set-phase`, `update-phase`, or `transition` commands
- Metadata operations require explicit `--get` or `--set` flags

**Standards:** See [status-lifecycle.md](standards/status-lifecycle.md) for the phase state machine, plan lifecycle, and metadata conventions.
- Do not skip phase transition validation
- Phase transitions are sequential -- you cannot skip phases
- Routing context is read-only; use `get-routing-context` for combined state

## Storage Location

Status is stored in the plan directory:

```text
.plan/plans/{plan_id}/status.json
```

---

## File Format

JSON format for storage:

```json
{
  "title": "Plan Title",
  "current_phase": "1-init",
  "title_token": {"owner": "merge-lock", "state": "lock-owned", "set_at": "2026-01-01T00:00:00Z"},
  "phases": [
    {"name": "1-init", "status": "in_progress"},
    {"name": "2-refine", "status": "pending"},
    {"name": "3-outline", "status": "pending"},
    {"name": "4-plan", "status": "pending"},
    {"name": "5-execute", "status": "pending"},
    {"name": "6-finalize", "status": "pending"}
  ],
  "metadata": {
    "change_type": "feature",
    "use_worktree": true,
    "worktree_path": "/abs/path/.plan/local/worktrees/my-feature",
    "worktree_branch": "feature/my-feature"
  },
  "created": "2025-01-15T10:00:00Z",
  "updated": "2025-01-15T14:30:00Z"
}
```

### Schema Fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Plan title |
| `current_phase` | string | Current active phase |
| `title_token` | object (optional) | Transient title-token record `{owner, state, set_at}`. `state` ∈ `lock-waiting`, `lock-owned` (lock-coordination states surfaced as ⏳/🔒 glyphs), `build-busy` (the orchestration-busy state surfaced as a 🔨 icon-slot override, NOT a glyph). `owner` ∈ `build-hook`, `merge-lock`, `cli`. `set_at` is a UTC ISO-8601 instant and is the input to the 3600-second staleness rule — a record older than that reads as absent, and any writer may then overwrite it. Written by `title-token set` (last writer wins); removed by `title-token clear`, which is owner-scoped. Absent when no token is active. Consumed by the `manage-terminal-title` composer for glyph/icon selection; not a persisted plan field — it is ephemeral session state. `build-busy` is set/cleared by the `build-hook` render assist bracketing a Bash build window — see `manage-terminal-title/standards/terminal-title-architecture.md` § Channel Delivery Contract ruling (c) for the record contract. |
| `phases` | list | Phase objects with name and status |
| `metadata` | table | Key-value metadata (common fields: `change_type`, `confidence`, `domain`, `use_worktree`, `worktree_path`, `worktree_branch`) |
| `created` | string | ISO timestamp of creation |
| `updated` | string | ISO timestamp of last update |

### Phase Status Values

| Status | Description |
|--------|-------------|
| `pending` | Phase not yet started |
| `in_progress` | Phase currently active |
| `done` | Phase completed |

### Worktree Metadata Convention

`status.metadata` is the canonical source of truth for whether a plan
runs in an isolated git worktree. `create` seeds only `use_worktree`;
`worktree_branch` and `worktree_path` are persisted at phase-5
materialization, and `get-worktree-path` reads all three:

| Field | Type | When set | Description |
|-------|------|----------|-------------|
| `use_worktree` | bool | Always (seeded by `create`) | `true` when the plan runs in an isolated worktree, `false` when it runs against the main checkout. Never absent on plans created via `create`. |
| `worktree_path` | string | Persisted at phase-5-execute Step 2.5 (absent until then) | Absolute path to the worktree root. Used by `get-worktree-path`, build wrappers (`--plan-id` resolution), and phase-entry assertions. Phases 1-4 record no path; phase-5-execute Step 2.5 persists the resolved path once `git worktree add` runs. |
| `worktree_branch` | string | Persisted at phase-5-execute Step 2.5 (absent until then) | Feature branch ref (`feature/{plan_id}`) derived and checked out at materialization. Recorded for the audit trail and consumed by `workflow-integration-git` worktree subcommands. |

Downstream consumers MUST read these fields via `get-worktree-path`
rather than re-deriving the path from filesystem layout. Re-derivation
breaks if the platform-neutral worktree root constant ever changes
again, and it duplicates logic that `manage-status` already owns.

---

## Operations

Script: `plan-marshall:manage-status:manage-status`

### create

Create status.json with initial phases. Optionally records the
worktree intent (`use_worktree`) into `status.metadata`; the branch and
the resolved `worktree_path` are derived and persisted later, at phase-5
materialization.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status create \
  --plan-id {plan_id} \
  --title {title} \
  --phases {comma-separated-phases} \
  [--force] \
  [--use-worktree]
```

**Parameters**:
- `--plan-id` (required): Plan identifier (kebab-case)
- `--title` (required): Plan title
- `--phases` (required): Comma-separated phase names in execution order (e.g., `1-init,2-refine,3-outline,4-plan,5-execute,6-finalize`). Order matters — it determines progress calculation and transition sequence.
- `--force`: Overwrite existing status.json
- `--use-worktree` (optional): Mark the plan as running in an isolated git worktree. Seeds only `status.metadata.use_worktree=true`; the feature branch (`feature/{plan_id}`) and the resolved `worktree_path` are derived and persisted later by phase-5-execute Step 2.5 once `git worktree add` runs. When `--use-worktree` is omitted, `status.metadata.use_worktree=false` is seeded explicitly so downstream resolvers never have to treat absence-of-metadata as "main-checkout".

**Output — main-checkout** (TOON):
```toon
status: success
plan_id: my-feature
file: status.json
created: true
plan:
  title: My Feature
  current_phase: 1-init
use_worktree: false
```

**Output — worktree (intent recorded)** (TOON):
```toon
status: success
plan_id: my-feature
file: status.json
created: true
plan:
  title: My Feature
  current_phase: 1-init
use_worktree: true
```

The branch and `worktree_path` are absent here — phase-5-execute Step 2.5 derives `feature/{plan_id}` and persists both at materialization.

### read

Read entire status.json content.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {plan_id}
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
plan:
  title: My Feature
  current_phase: 2-refine
  phases: [...]
  metadata: {...}
```

### set-phase

Set current phase (marks phase as in_progress).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status set-phase \
  --plan-id {plan_id} \
  --phase {phase_name}
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
current_phase: 2-refine
previous_phase: 1-init
```

### update-phase

Update a specific phase's status.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-phase \
  --plan-id {plan_id} \
  --phase {phase_name} \
  --status {pending|in_progress|done}
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
phase: 1-init
phase_status: done
```

### progress

Calculate plan progress percentage.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status progress \
  --plan-id {plan_id}
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
progress:
  total_phases: 6
  completed_phases: 3
  current_phase: 4-plan
  percent: 50
```

**Progress formula**: `percent = floor(completed_phases / total_phases * 100)`. A phase counts as "completed" only when its status is `done`. Phases with status `in_progress` or `pending` are not counted.

### metadata

Get or set metadata fields.

**Set metadata**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} \
  --set \
  --field {field_name} \
  --value {value}
```

**Get metadata**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} \
  --get \
  --field {field_name}
```

**Output (set)** (TOON):
```toon
status: success
plan_id: my-feature
field: change_type
value: feature
previous_value: bug_fix
```

**Output (get)** (TOON):
```toon
status: success
plan_id: my-feature
field: change_type
value: feature
```

### mark-step-done

Record the outcome of a phase step inside `status.metadata.phase_steps`. Phase skills use this to persist intra-phase progress (e.g., discovery, drift-detection) so that resuming a phase can skip completed steps. Outcomes are `done`, `skipped`, `loop_back`, or `failed`. An optional `--display-detail` one-line string is persisted alongside the outcome so downstream renderers (phase-6-finalize vertical-steps block, etc.) can surface user-facing step summaries. Loop-back outcomes carry a mandatory `--loop-back-target` granularity classifier (see "Loop-back target classification" below).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} \
  --phase {phase_name} \
  --step {step_id} \
  --outcome {done|skipped|loop_back|failed} \
  [--display-detail "one-line user-facing detail"] \
  [--head-at-completion <sha>] \
  [--loop-back-target {5-execute|6-finalize}] \
  [--fact KEY=VALUE]... \
  [--force]
```

**Parameters**:
- `--plan-id` (required): Plan identifier
- `--phase` (required): Phase name (e.g., `5-execute`)
- `--step` (required): Step identifier within the phase (free-form string chosen by the phase skill)
- `--outcome` (required): `done`, `skipped`, `loop_back`, or `failed`
- `--display-detail` (optional at CLI level, required-by-convention for phase-6-finalize steps per the phase-6-finalize interface contract): One-line user-facing detail string. Persisted as `null` when omitted.
- `--head-at-completion` (optional): Git SHA captured at step completion. Persisted alongside outcome and consulted by resumable phase dispatchers (e.g., phase-6-finalize `pre-push-quality-gate`) to detect HEAD advancement.
- `--loop-back-target` (REQUIRED when `--outcome=loop_back`, FORBIDDEN otherwise): Loop-back target phase. Must be one of `5-execute` (full phase rollback for fix-task-required dispositions) or `6-finalize` (inline replay for inline-fixable dispositions). See "Loop-back target classification" below.
- `--fact` (optional, repeatable): Record one structured `KEY=VALUE` per-step fact. See "Structured step facts" below.
- `--force` (optional): Overwrite an existing differing outcome

**Structured step facts**:

`--fact` is repeatable; the accumulated pairs are parsed into a single `dict[str, str]` persisted under the record's `facts` key. This is what lets `display_detail` be a *rendering* of recorded facts rather than their sole record, so a retrospective can ask structured questions of a step record instead of parsing prose.

- **Parsing**: each token splits on the FIRST `=`. The value half may contain `=` and may be empty; only the key is constrained. A repeated key takes its last value.
- **Rejection**: a token with no `=`, or with an empty key, returns `status: error`, `error: invalid_fact` with the offending token echoed as `offending_token` — a malformed fact is never silently dropped.
- **Optionality**: omitting `--fact` entirely produces the byte-identical historical record shape (no `facts` key), so every pre-existing call site stays valid.
- **Which keys are legal**: the keys a step may record are declared by that step's `records_facts` frontmatter obligation — see [ext-point-finalize-step.md](../extension-api/standards/ext-point-finalize-step.md) § "Structured step facts" for the governing discriminator, the declaration-is-union / obligation-is-per-branch reconciliation rule, and the `work_performed` cross-cutting fact. This command does NOT validate keys against that declaration; it only parses and persists. The declaration-vs-wiring agreement is enforced by the finalize-step contract test, not here.

**Loop-back target classification**:

The `--loop-back-target` flag encodes the granularity invariant from the phase-6-finalize "Loop-back Target Contract" section. Two legal values:

- `5-execute` — full phase rollback for **fix-task-required** dispositions. Use when triage allocated one or more fix tasks (`fix_tasks_created > 0`) or deferred any findings to overflow (`overflow_deferred > 0`). The continuation hook re-dispatches `phase-5-execute` against the freshly-allocated fix tasks before re-entering the finalize FOR loop.
- `6-finalize` — inline replay for **inline-fixable** dispositions. Use when triage resolved every finding via SUPPRESS, narrow-rationale ACCEPT, or single-annotation FIX (no fix-task allocation, no overflow). The continuation hook stays in `6-finalize`, does NOT call `set-phase`, and re-fires the loop-back-marked step from the resumable re-entry check.

The flag is REQUIRED on every `loop_back` outcome (returns `error: missing_loop_back_target` when absent) and FORBIDDEN on every other outcome (returns `error: unexpected_loop_back_target`). The `argparse` `choices` enforce the two-value enumeration at parse time. There is no backwards-compat fallback — every loop-back-emitting call site MUST classify the disposition before persisting the outcome.

**Storage shape**:

```json
status.metadata.phase_steps[{phase}][{step}] = {
  "outcome": "done" | "skipped" | "loop_back" | "failed",
  "display_detail": <string> | null,
  "head_at_completion": <sha> | absent,
  "loop_back_target": "5-execute" | "6-finalize" | absent,
  "facts": {"<key>": "<value>", ...} | absent
}
```

Both the `metadata` and `phase_steps` containers are created on demand. A non-dict (bare-string) entry is rejected with `error: legacy_string_entry` — see conflict semantics below. The `head_at_completion`, `loop_back_target`, and `facts` keys are only present when the corresponding flag was supplied (per the `_build_entry` helper); `loop_back_target` is structurally guaranteed to be present iff `outcome == "loop_back"`.

**Semantics**:
- **Idempotent on identical outcome AND display_detail AND head_at_completion AND loop_back_target AND facts**: If the step already has the requested outcome and all five fields match, no file write occurs and `changed: false` is returned.
- **Detail / head / loop_back_target / facts update**: If the outcome matches but any of `display_detail`, `head_at_completion`, `loop_back_target`, or `facts` differ, the command updates the entry in place and returns `changed: true`. A re-call that changes ONLY the facts is therefore reported as a change, never silently swallowed.
- **Conflict on differing outcome**: If the step already has a different outcome and `--force` is not supplied, the command returns `error: conflict` with the existing outcome surfaced in the response. Supplying `--force` overwrites the existing value (and detail / head / loop_back_target / facts).
- **Bare-string entry rejection**: If the existing entry is a bare string rather than a dict, the command returns `error: legacy_string_entry` and refuses to write. Only the dict shape above is accepted.

> **Forward reference — `phase_steps_complete` invariant**: Downstream phase skills and verification helpers treat `status.metadata.phase_steps[{phase}]` as the authoritative record of which intra-phase steps have been marked `done` or `skipped`. A phase is considered `phase_steps_complete` when every step in the phase's declared step list has a dict entry with `outcome == 'done'`. The invariant reader rejects bare-string entries. Consumers must not fabricate entries by other means — always go through `mark-step-done`.

**Output — idempotent no-op** (TOON):
```toon
status: success
plan_id: my-feature
phase: 5-execute
step: discovery
outcome: done
display_detail: null
changed: false
```

**Output — state changed** (TOON):
```toon
status: success
plan_id: my-feature
phase: 5-execute
step: discovery
outcome: done
display_detail: Discovered 3 drift candidates across deliverables 2 and 4
changed: true
previous_outcome: null
previous_display_detail: null
```

**Output — state changed with facts** (TOON):
```toon
status: success
plan_id: my-feature
phase: 6-finalize
step: finalize-step-sync-baseline
outcome: done
display_detail: no-op rebase, already current with base
facts:
  action: noop
  upstream_commit_count: 0
  work_performed: true
changed: true
previous_outcome: null
previous_display_detail: null
previous_facts: null
```

**Output — conflict** (TOON):
```toon
status: error
plan_id: my-feature
error: conflict
phase: 5-execute
step: discovery
existing_outcome: skipped
requested_outcome: done
message: Step 'discovery' in phase '5-execute' already marked as 'skipped'; use --force to overwrite with 'done'
```

**Output — malformed fact** (TOON):
```toon
status: error
plan_id: my-feature
error: invalid_fact
phase: 6-finalize
step: finalize-step-sync-baseline
offending_token: work_performed
message: --fact expects KEY=VALUE with a non-empty KEY, got: 'work_performed'
```

**Output — legacy drift** (TOON):
```toon
status: error
plan_id: my-feature
error: legacy_string_entry
phase: 5-execute
step: discovery
existing_outcome: done
requested_outcome: done
message: Step 'discovery' in phase '5-execute' has legacy bare-string storage ('done'); migrate status.metadata.phase_steps to the dict shape {"outcome": ..., "display_detail": ...} before retrying.
```

### assert-step-recorded

Read-only verdict over `status.metadata.phase_steps[{phase}][{step}]`: does a terminal step record exist? The phase-6-finalize dispatcher calls this after every dispatched (Task-agent) step returns, to detect the silent gap where a step returns `status: success` but skips its mandated `mark-step-done` side-effect — the omission that otherwise stays invisible until the `phase_steps_complete` handshake deadlocks the phase transition with no per-step attribution. The verb performs **zero writes** to `status.json`.

A record counts as *recorded* iff a dict entry with a terminal `outcome` in `{done, skipped, loop_back, failed}` is present (a `loop_back` record counts as terminal for guard purposes — the dispatcher re-fires it via the resumable re-entry check). Bare-string legacy entries and missing entries both report `recorded: false`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status assert-step-recorded \
  --plan-id {plan_id} \
  --phase {phase_name} \
  --step {step_id} \
  [--require-terminal]
```

**Parameters**:
- `--plan-id` (required): Plan identifier
- `--phase` (required): Phase name (e.g., `6-finalize`)
- `--step` (required): Step identifier within the phase
- `--require-terminal` (optional): Escalate a missing terminal record to a `status: error` verdict instead of returning `recorded: false`. Two error branches are distinguished: `step_record_mismatched_key` when the queried step has no record BUT a terminal record exists under a different (near-miss) key in the same phase — the dispatched step recorded under the wrong key; `step_record_missing` when no terminal record exists under any key in the phase. The post-dispatch guard passes this flag so a missing record is a branchable failure verdict rather than a soft boolean.

**Output — recorded** (TOON):
```toon
status: success
plan_id: my-feature
phase: 6-finalize
step: automated-review
recorded: true
outcome: done
```

**Output — not recorded (no `--require-terminal`)** (TOON):
```toon
status: success
plan_id: my-feature
phase: 6-finalize
step: automated-review
recorded: false
outcome: null
```

**Output — missing record under `--require-terminal`** (TOON):
```toon
status: error
plan_id: my-feature
error: step_record_missing
phase: 6-finalize
step: automated-review
recorded: false
outcome: null
message: No terminal record for step 'automated-review' in phase '6-finalize': the dispatched step returned without recording a mark-step-done outcome (expected one of ['done', 'skipped', 'loop_back', 'failed']).
```

**Output — mismatched key under `--require-terminal`** (TOON): the queried step has no record, but a terminal record exists under a near-miss key in the same phase.
```toon
status: error
plan_id: my-feature
error: step_record_mismatched_key
phase: 6-finalize
step: plan-marshall:plan-retrospective
recorded: false
outcome: null
orphan_key: plan-retrospective
orphan_outcome: done
message: No terminal record for step 'plan-marshall:plan-retrospective' in phase '6-finalize', but a terminal record exists under the near-miss key 'plan-retrospective' (outcome 'done'). The dispatched step recorded its mark-step-done outcome under the wrong key — expected the queried step name 'plan-marshall:plan-retrospective'.
```

#### Canonical step-key contract (shared resolver)

`mark-step-done` (write) and `assert-step-recorded` (read) both route the `--step` value through the single shared resolver `canonicalize_step_key` (`script-shared/scripts/_step_key_canonical.py`) BEFORE touching `status.metadata.phase_steps`. The resolver reconciles a step id to the same canonical (bare) manifest key: it maps a promoted built-in-equivalent bundle id via `PROMOTED_BUILTIN_STEP_IDS` (`plan-marshall:automatic-review` → `automatic-review`), strips a leading `default:` prefix (`default:push` → `push`), and preserves `project:` / other `bundle:skill` ids verbatim; it is idempotent on already-canonical input.

Because the write key and read key are computed identically, the record/assert keys reconcile to the manifest `step_id` regardless of which spelling each caller used: a step recorded via `mark-step-done` with one variant (`default:push`) is resolved as a canonical MATCH by `assert-step-recorded` queried with the other variant (`push`) — `recorded: true`, no `step_record_mismatched_key`. The same resolver is consumed by `manage-execution-manifest`'s `record-step` handler and every manifest-bundle boundary-normalization call site, so execution-log keys, phase-step keys, and the manifest `step_id` all agree. The `step_record_mismatched_key` verdict is now reserved for a genuine mismatch — a typographic near-miss orphan (edit-distance) that is not a canonical variant — which stays the fail-loud verdict.

### merge-authorization

Bind a merge-gate authorization to the HEAD it was granted against AND to the gap class it was granted over, then refuse it once either stops matching. The record lives in `status.metadata.merge_authorizations`, keyed by authorization `kind`, beside the `phase_steps` map. It is deliberately **not** a `phase_steps` entry: those keys are the finalize step roster and feed the `phase_steps_complete` handshake, and the host step `default:branch-cleanup` correctly declares no `head_dependent` fact because it records an action performed rather than a HEAD-dependent verdict.

The authorization population — which kinds exist, which are bound by `grant`, which gap class each authorizes, and where each grant site lives — is declared by the **Merge-Authorization Roster** in [`phase-6-finalize/standards/branch-cleanup.md`](../phase-6-finalize/standards/branch-cleanup.md), not by this parser. `--kind` and `--gap-class` accept any non-empty token so a mechanism added to the roster later needs no parser change.

**Two conditions, not one.** HEAD-binding answers "is this ruling still bound to the tree in hand"; the gap class answers "was this ruling given over the gap I am reporting". Both are required, because several kinds are granted at sites that run BEFORE a given gate, at the SAME HEAD, over a DIFFERENT gap — so a consumer routing on HEAD-validity alone would find a valid record on essentially every merge and skip its own gate universally. See the roster's § "Gap classes — why HEAD-binding alone is not authorization".

#### merge-authorization grant

Persist a HEAD-bound, gap-class-bound authorization record. A re-grant at a new HEAD **overwrites** the record — that overwrite IS the sanctioned re-seek, so there is no revoke verb.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status merge-authorization grant \
  --plan-id {plan_id} \
  --kind {kind} \
  --head {sha} \
  --gap-class {gap_class} \
  --granted-over {gap_description} \
  --reason {reason}
```

**Parameters**:
- `--plan-id` (required): Plan identifier
- `--kind` (required): Authorization kind, as declared by the Merge-Authorization Roster (e.g., `barrier-ask-override`, `pre-merge-consent`, `red-ci-override`, `rereview-timeout-override`)
- `--head` (required): Git SHA the authorization is granted against
- `--gap-class` (required): The gap class this ruling authorizes past — the machine token naming WHICH gate the operator was answering (e.g., `review-barrier-gap`, `merge-action`, `red-ci-gate`, `rereview-timeout`). Each roster row declares the token its site must pass, via that row's `authorizes:` claim.
- `--granted-over` (required): What the authorization was granted over — the gap as the granting site saw it (e.g., the pending count and the `unproven_bots` list). Persisted verbatim so a later reader can re-evaluate the ruling against a later delta. This is the free-prose companion to `--gap-class`: prose for a human, token for routing. Routing never reads it.
- `--reason` (required): The operator's (or policy's) stated reason

**Output** (TOON):
```toon
status: success
plan_id: my-feature
kind: barrier-ask-override
head: 76c7200b6
gap_class: review-barrier-gap
granted_over: 2 unhandled, unproven_bots=pr-agent
reason: operator accepted the gap
granted_at: "2026-01-15T14:30:00Z"
```

`previous_head` is additionally reported when the grant overwrote a record already held under the same `kind`.

#### merge-authorization check

Return every authorization record with its HEAD verdict AND its admissibility for the gap class the caller is reporting. There is deliberately **no `--kind` flag**: the caller asks one question — "is there an admissible authorization for the gap I am reporting" — and a per-kind filter would let one valid authorization mask a lapsed sibling.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status merge-authorization check \
  --plan-id {plan_id} \
  --head {sha} \
  --gap-class {gap_class}
```

**Parameters**:
- `--plan-id` (required): Plan identifier
- `--head` (required): The HEAD the caller is about to merge
- `--gap-class` (required): The gap class the CALLER is reporting. Required rather than optional, so no caller can fall back to routing on HEAD-validity alone.

Per record the HEAD verdict is `valid` when `record.head` equals `--head`, and `lapsed` otherwise. Per record `admissible` is `true` only when the verdict is `valid` AND `record.gap_class` equals `--gap-class`. Both are **fail-closed**: a malformed record and a record from a superseded HEAD both resolve to `lapsed`, a record carrying no `gap_class` matches no class, and an empty store returns `any_authorized: false` / `any_admissible: false` with empty lists — `absent` is never collapsed into `valid`.

**Admissibility narrows the ROUTING, never the REPORT.** A `valid` record granted over a different gap stays in `authorized_kinds` (it really is bound to this tree) and is additionally listed in `inadmissible_kinds`, and a lapsed sibling still appears in `lapsed_kinds`. Nothing is filtered out, so a caller can always name exactly which ruling expired and which one is live but covers a different gap.

**Output** (TOON):
```toon
status: success
plan_id: my-feature
head: 76c7200b6
gap_class: review-barrier-gap
any_authorized: true
any_admissible: false
authorized_kinds[1]:
  - pre-merge-consent
lapsed_kinds[1]:
  - barrier-ask-override
admissible_kinds[0]:
inadmissible_kinds[1]:
  - pre-merge-consent
records[2]{kind,head,verdict,gap_class,admissible,granted_over,reason,granted_at}:
  barrier-ask-override,d4f1a02c9,lapsed,review-barrier-gap,false,2 unhandled unproven_bots=pr-agent,operator accepted the gap,2026-01-15T14:30:00Z
  pre-merge-consent,76c7200b6,valid,merge-action,false,operator confirmed merge of PR #42 at this HEAD,operator selected 'Yes merge',2026-01-15T14:41:00Z
```

### get-context

Get combined status context (phase, progress, metadata) in one call.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-context \
  --plan-id {plan_id}
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
title: My Feature
current_phase: 2-refine
total_phases: 6
completed_phases: 1
change_type: feature
```

**Note**: All metadata fields are promoted to top level for convenience (flattened from `metadata` object). The fields shown depend on what has been set via `metadata --set`.

### get-worktree-path

Resolve the persisted worktree path for a plan from `status.metadata`.
Allows callers (build wrappers, `git-workflow`, phase-entry assertions)
to look up the active worktree by `--plan-id` alone — without
re-deriving the path from filesystem layout, and without taking a
`--project-dir` argument.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-worktree-path \
  --plan-id {plan_id}
```

**Parameters**:
- `--plan-id` (required): Plan identifier

**Behavior** (tri-state, discriminated by `worktree_state`):
- When `metadata.use_worktree == false` (or metadata is absent) → `worktree_state: disabled`, `worktree_path: ''`. Callers interpret this as "plan runs against the main checkout".
- When `metadata.use_worktree == true` and `metadata.worktree_path` is set → `worktree_state: materialized`, `worktree_path: <abs>`. The worktree directory has been created.
- When `metadata.use_worktree == true` and `metadata.worktree_path` is missing/empty → `worktree_state: pending`, `worktree_path: ''`, `not_yet_materialized: true`. The plan opted into worktree mode but the directory has not been materialized yet (pre-materialization). Callers MUST fall back to the main checkout cwd.

The `worktree_unresolved` error path is owned by `phase_handshake verify`, which validates filesystem-resolvability of a non-empty `worktree_path`. This subcommand never returns that error; it returns `pending` for the pre-materialization state instead.

**Output — disabled (main checkout)** (TOON):
```toon
status: success
plan_id: my-feature
use_worktree: false
worktree_state: disabled
worktree_path: ""
```

**Output — materialized** (TOON):
```toon
status: success
plan_id: my-feature
use_worktree: true
worktree_state: materialized
worktree_path: /abs/path/.plan/local/worktrees/my-feature
worktree_branch: feature/my-feature
```

**Output — pending (pre-materialization)** (TOON):
```toon
status: success
plan_id: my-feature
use_worktree: true
worktree_state: pending
worktree_path: ""
not_yet_materialized: true
```

### list

Discover all plans, optionally filtered by current phase.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status list \
  [--filter PHASE]
```

**Parameters**:
- `--filter` (optional): Comma-separated phase names to filter by

**Output** (TOON):
```toon
status: success
total: 2

plans[2]{id,current_phase,status,location}:
my-feature,3-outline,in_progress,current
bugfix-123,5-execute,in_progress,worktree
```

Each entry carries a `location` field: `current` (the plan directory lives on the cwd checkout) or `worktree` (the plan directory was moved into its worktree at phase-5 entry, ADR-002). The merged list is deduped by plan id (a moved-in plan appears exactly once) and sorted by id.

**Concurrent-session visibility**: per [ADR-002](../../../../../doc/adr/002-Plan-scoped_operations_move_into_a_cwd-pinned_hermetic_worktree.adoc), a plan's non-git-controlled runtime state (its plan directory) MOVES into the plan's own worktree at phase-5 entry and moves back to main at finalize. While a plan is executing (phase-5+), its plan directory therefore lives in its worktree, not on main. `cmd_list` discovers both sources: it enumerates the main checkout's plans (`location: current`) AND scans `get_worktree_root()`'s child worktrees for moved-in plans (`location: worktree`), so a `list` run from the main checkout DOES surface a plan that is mid-flight in its worktree — the ADR-002 move-in is exactly why the worktree scan is necessary. See `marketplace/bundles/plan-marshall/skills/workflow-integration-git/standards/worktree-handling.md` for the worktree lifecycle that produces this property.

### transition

Mark a phase as done and advance to next phase. Validates phase ordering.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status transition \
  --plan-id {plan_id} \
  --completed {phase_name}
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
completed_phase: 3-outline
next_phase: 4-plan
```

### archive

Archive a completed plan (moves to `.plan/archived-plans/YYYY-MM-DD-{plan_id}`).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status archive \
  --plan-id {plan_id} \
  [--dry-run] \
  [--reason REASON]
```

`--reason REASON` persists a human-readable explanation to
`status.metadata.archived_reason` on the archived plan. The field is additive
(omitted when the flag is absent — no schema migration). Used by `plan-doctor`
rule `stuck-low-confidence-archive` as the canonical remediation flag so a
retrospective audit can distinguish intentional abandonment from neglect.
Example values: `low_confidence`, `scope_changed`, `superseded_by_<plan_id>`.

**Output** (TOON):
```toon
status: success
plan_id: my-feature
archived_to: .plan/archived-plans/2026-04-02-my-feature
```

### delete-plan

Delete an entire plan directory. Used when user selects "Replace" for an existing plan during plan-init.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status delete-plan \
  --plan-id {plan_id} \
  [--no-restore-lessons]
```

**Parameters**:
- `--plan-id` (required): Plan identifier
- `--no-restore-lessons` (optional): Skip the lesson carry-back entirely. Because the carry-back owns the veto below, opting out of the carry-back also opts out of the veto — the directory is deleted and any lesson it carries is discarded. The payload reports this branch as `lesson_carry_back_action: not_attempted` with `lesson_store_resolution: unresolved`: nothing was scanned and no store was resolved, so it may claim neither the benign scanned-and-empty zero nor a resolution it never performed.

#### Lesson carry-back (and the veto)

A plan directory can hold `lesson-*.md` files moved in by `manage-lessons convert-to-plan`, and for such a lesson the plan directory is the **only copy** — deleting the directory destroys it. `delete-plan` therefore runs a carry-back FIRST, moving every carried lesson back into the corpus, and that carry-back can **veto the deletion**.

The destination is resolved through the **main-anchored** lessons-store handle, never the cwd-keyed `base_path()`. A worktree-pinned `delete-plan` would otherwise restore into the worktree's own ephemeral corpus — a store that is discarded when the worktree goes away, which loses the lesson just as thoroughly as deleting it.

`lesson_carry_back_action` reports which kind of answer the carry-back is giving. Every value it shares with `manage-lessons restore-from-plan`'s `action` vocabulary carries the identical meaning there, so the two lesson-restore surfaces answer the "which kind of zero is this?" question the same way. The sets are **not equal**, and deliberately so: `not_attempted` is producible only here, because only `delete-plan` has an opt-out flag.

| `lesson_carry_back_action` | Meaning |
|----------------------------|---------|
| `restored` | The plan directory was scanned, DID carry lesson files, and **every** one of them landed in the corpus. `restored_lesson_ids` names them; `skipped_lessons` is empty. |
| `restore_incomplete` | The plan directory was scanned and carried lesson files, but at least one did **not** land. `restored_lesson_ids` is legitimately empty when none did. This is the state that fires the veto below. |
| `no_lesson_file` | The plan directory was scanned and carried none. The benign zero. |
| `plan_dir_unresolved` | The carry-back could not look — the directory is gone, or the main-anchored store did not resolve **and** the directory carried lesson files that consequently could not land. `lesson_store_resolution` says which. |
| `not_attempted` | `--no-restore-lessons` opted out: nothing was scanned, no store was resolved, and any carried lesson is discarded with the directory. `lesson_store_resolution` is `unresolved` and `lessons_dir` is empty. |

The last two are the two ways this payload can carry a zero that is **not** evidence the plan carried no lesson. Keeping them out of `no_lesson_file` is what lets an audit tell "deleted a plan that verifiably carried no lesson" from "deleted a plan whose lessons went unexamined" — the same distinction the carry-back exists to make, applied to the branch that can actually destroy one.

**Read both fields — neither answers both questions.** `lesson_carry_back_action` reports what the scan *found*; `lesson_store_resolution` reports whether the corpus was *reachable*. An unresolvable store over a directory that carried lesson files is `plan_dir_unresolved`, because those lessons could not land. The same unresolvable store over a directory carrying **none** is `no_lesson_file` — correctly, since the directory was scanned and there was nothing to land — and `lesson_store_resolution: unresolved` is what carries the could-not-look half of that answer. A consumer branching on `lesson_carry_back_action` alone would read the second case as a fully-verified benign zero.

**The veto**: when `skipped_lessons` is non-empty, at least one carried lesson did NOT land, so the plan directory still holds the only copy of it. The delete is **refused** with `error: lesson_carry_back_incomplete` and the directory is left intact. The refusal is what makes silent corpus loss unreachable on this path: a skipped lesson plus an unconditional delete would destroy the only copy with no signal anywhere. Resolve the cause (or pass `--no-restore-lessons` to delete and discard deliberately), then retry.

Each `skipped_lessons` row carries the `reason` that kept it from landing, over this closed vocabulary:

| `reason` | Meaning |
|----------|---------|
| `destination_exists` | The corpus already holds an entry under that lesson id. The destination is claimed with a no-replace create, so the collision test and the claim are one operation — an incumbent lesson can never be overwritten by a destination that appeared mid-carry-back. |
| `path_traversal` | The lesson id is traversal-shaped, or the destination it produces would land outside the corpus directory. |
| `store_unresolved` | The main-anchored lessons store did not resolve, so the carry-back could not reach the corpus at all. Every carried lesson gets this reason. |
| `unsafe_source` | The `lesson-*.md` entry is not a regular file — a symlink, directory, or other non-regular entry. Carrying it back would relocate whatever it points AT, removing an arbitrary external file, on the very path that deletes the plan directory next. Rejecting it as a reported skip (rather than following it) is what keeps that reachable-only-through-the-veto. |

**Output** (TOON format):

On success:
```toon
status: success
plan_id: my-feature
action: deleted
path: /path/to/.plan/local/plans/my-feature
files_removed: 5
lesson_carry_back_action: restored
lesson_store_resolution: main_anchored
lessons_dir: /abs/path/to/.plan/local/lessons-learned
lesson_restored: true
restored_lesson_ids[1]:
  - 2025-12-02-15-001
skipped_lessons[0]:
```

On refusal (a carried lesson did not land — the directory is NOT deleted):
```toon
status: error
plan_id: my-feature
error: lesson_carry_back_incomplete
action: refused
path: /path/to/.plan/local/plans/my-feature
lesson_carry_back_action: restore_incomplete
lesson_store_resolution: main_anchored
lessons_dir: /abs/path/to/.plan/local/lessons-learned
lesson_restored: false
restored_lesson_ids[0]:
skipped_lessons[1]{lesson_id,reason}:
  2025-12-02-15-001,destination_exists
message: 1 carried lesson(s) could not be restored (2025-12-02-15-001); the plan directory holds the only copy, so it was NOT deleted.
```

On error (plan not found):
```toon
status: error
plan_id: my-feature
error: plan_not_found
message: Plan directory does not exist: /path/to/.plan/local/plans/my-feature
```

**Use case**: Called by plan-init when user selects "Replace" to delete existing plan before creating new one. See `plan-marshall:phase-1-init/standards/plan-overwrite.md` for the full workflow.

**Warning**: This recursively deletes the entire plan directory including all subdirectories (logs, tasks, work artifacts). There is no undo. The carry-back veto is the one guard against that irreversibility taking a lesson with it.

### route

Get skill name for a phase.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status route \
  --phase {phase_name}
```

**Output** (TOON):
```toon
status: success
phase: 3-outline
skill: solution-outline
description: Create solution outline with deliverables
```

### get-routing-context

Get combined routing context (phase + skill + progress in one call).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-routing-context \
  --plan-id {plan_id}
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
title: Add caching layer
current_phase: 3-outline
skill: solution-outline
skill_description: Create solution outline with deliverables
total_phases: 6
completed_phases: 2
```

### planning-lane

Deterministic planning-lane router with two sub-verbs (`route` / `escalate`). Resolves `planning_lane ∈ {light, deep}` from cheap field reads plus a `request.md` regex — **zero codebase discovery, zero LLM cognition**. The default is `light`; any deep-precondition signal forces `deep`. Escalation is **one-way** (light may ratchet to deep, never deep→light).

**Routing-tier sequencing** — this `planning-lane` router is **Tier 2** of the routing model. Tier 1 recipe-match (`manage-config recipe-match`, phase-1-init Step 5c) runs **ahead** of this `planning-lane route` call (phase-1-init Step 8b): registry-wide recipe scoring precedes the light/deep lane decision. The router's own resolution logic is unaffected by Tier 1 — the sequencing note records ordering only. See `manage-config` Canonical invocations → `recipe-match` for the Tier 1 verb contract and `ref-workflow-architecture/standards/phase-lifecycle.md` for the routing-tier position in the lifecycle.

**route** — evaluate the signal set, resolve the lane, project the recommended execution-profile posture, and (with `--persist`) write `status.metadata.planning_lane` and `status.metadata.execution_profile`. Emits one decision-log line naming every signal value, the winning predicate, the projected posture, and the `scope_provenance` block (`distinct_path_count`, `fan_out_marker`, `band_rule`) — so both verdicts and the band rule that drove them are on one line.

The signal set (`deep` IFF any deep-precondition fires; otherwise `light`):

| # | Signal | Source (cheap read) | → deep when |
|---|--------|---------------------|-------------|
| S1 | `plan_source` | `status.metadata.plan_source` | source is free-form (absent/unset) **AND** S5 concreteness fails (`lesson`/`recipe` bias light) |
| S2 | `scope_estimate` | `references.scope_estimate` | ∈ {`multi_module`, `broad`, `none`, unset}. `surgical` and `single_module` do not fire S2, but only `surgical` counts as **narrow** — it alone earns the S3/S4 narrow-and-concrete carve-out, so a `single_module` request keeps its S3/S4 escalation. See the `scope-estimate-heuristic` row of the Scripts table for the band table that produces these values. |
| S3 | `change_type` | `status.metadata.change_type` | ∈ {`feature`, `feature_breaking`} (`bug_fix`/`tech_debt`/`enhancement`/`verification` → light) |
| S4 | `compatibility` | `marshal.json plan.phase-2-refine.compatibility` | == `breaking` |
| S5 | request concreteness | regex over the **whole** `request.md` body (heading-blind: the entire file minus its own `# Request` title line — no section is selected) | body names NO file path **AND** NO concrete fix signal (fenced code block / `python3 .plan/execute-script.py` CLI / `manage-*` notation) |
| S6 | explicit override | `status.metadata.planning_lane_override` (or `--lane-override deep`) | == `deep` forces deep (one-way) |
| S7 | author risk prose | regex over the **whole** `request.md` body | the body carries an explicit scale warning (`multi-PR`, `codebase-wide`, `largest`, `riskiest`, `expect a split`, `foundation`, `epic`, `campaign` — case-insensitive, word-boundary anchored). Deliberately OUTSIDE the carve-out below: the author stating the scale outranks a cheap band. `epic` additionally excludes the metadata-key form (`epic:`), so an ingested orchestrator spec's preamble is not mistaken for a hand-written warning. |

**narrow-and-concrete carve-out** — when `scope_estimate` is `surgical` **AND** the request is concrete (S5 passes), S3 and S4 (and only those two) are suppressed so a bounded, well-specified change cannot be forced `deep` by its `change_type` or `compatibility` alone. The carve-out requires **actual** narrowness: `single_module` is the catch-all middle band, so it does not qualify. The same predicate governs the execution-profile projection below, so a non-narrow request can neither hide its S3/S4 escalation nor collapse its posture to `minimal`.

**deep-lane short-circuit** — `plan.phase-1-init.deep_lane` is read BEFORE the signal set: `always` → force `deep`; `never` → force `light` (the DQ3 hard-escalation ratchet still fires unless `plan.phase-1-init.escalation: never` is also set); `auto` (default) → the signal set decides.

**Execution-profile projection** — `route` also projects a recommended execution-profile posture (`minimal` / `standard` / `full`) over the SAME signals, surfaced under `execution_profile` (and the structured `profile` block). The projection is a pure derivation — `minimal` for a `surgical`, concretely specified change (the narrow-and-concrete case dominates, so it holds even when the change reads generative or breaking), `full` for a generative change that is also broad or clean-slate breaking, `standard` otherwise. It is **independent of the deep-lane gate**: `deep_lane: always` forces `planning_lane=deep` but does NOT coerce the profile to `full` (planning depth and the finalize-step profile are separate axes). The lane contract is owned by [`extension-api/standards/ext-point-lane-element.md`](../extension-api/standards/ext-point-lane-element.md). With `--persist`, the projected posture is written to `status.metadata.execution_profile` as the init-time default; the phase-1-init posture dialogue may override it via `metadata --set --field execution_profile`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status planning-lane route \
  --plan-id {plan_id} [--lane-override deep|light] [--persist]
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
planning_lane: deep
ceremony_deep_lane: auto
decision_predicate: signal_set
fired_signals[2]:
  - "S3:change_type"
  - "S4:compatibility"
execution_profile: full
profile:
  recommended_posture: full
  candidate_postures[3]: [ minimal, standard, full ]
scope_provenance:
  distinct_path_count: 5
  fan_out_marker: false
  band_rule: path_count_middle_band
persisted: true
classification_validation:
  mismatch_count: 0
  mismatches[0]:
  findings_emitted: 0
```

`scope_provenance` explains **why** the band came out as it did: `distinct_path_count` and `fan_out_marker` are the two measurements the band table reads, and `band_rule` names the row that fired (one of `unscoreable_body`, `scan_incomplete`, `fan_out_marker`, `path_count_at_or_above_multi_module_floor`, `path_count_middle_band`, `path_count_at_or_below_surgical_max`, `pathless_non_empty_body`, in evaluation order — see the `scope-estimate-heuristic` row of the Scripts table). It is observability, not a gate; `--lane-override` / S6 remains the way to disagree with a verdict.

`route` runs the deterministic **classification-validation gate** (see `classification-validate` below) as a pre-route pass and surfaces its result under `classification_validation`. The gate is **flag-not-block** — it never changes the resolved lane; a flagged mismatch only records a Q-Gate finding.

**escalate** — the one-way light→deep ratchet evaluated inside the light-lane envelope. Sets `planning_lane=deep`, `lane_escalated=true`, and records the `escalation_trigger` (`explosion` / `premise` / `cross_cutting`). The `lane_escalated` flag is sticky — a deep lane never reverts, so there is no downgrade verb.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status planning-lane escalate \
  --plan-id {plan_id} --trigger explosion|premise|cross_cutting [--persist]
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
planning_lane: deep
lane_escalated: true
escalation_trigger: explosion
persisted: true
```

### classification-validate

Deterministic **classification-validation gate** — cross-checks the plan's `change_type` and `scope_estimate` against cheap request signals and emits a phase-1-init Q-Gate finding on a mismatch. **Zero codebase discovery, zero LLM cognition; flag-not-block** — it NEVER gates routing. The gate runs automatically as a pre-route pass inside `planning-lane route`; this subcommand exposes it standalone (e.g., for a phase-1-init invocation that does not route immediately).

Three mismatch classes are flagged, each chosen to raise zero false positives:

- **`feature_as_bug_fix`** — `change_type == bug_fix` while the deterministic change-type heuristic (the same scoring engine `change-type-heuristic` uses) resolves a **non-ambiguous** `feature` winner from the request narrative. A borderline / tied narrative never trips it.
- **`non_empty_affected_files_with_null_scope`** — `references.affected_files` is non-empty while `references.scope_estimate` is null / empty / `none`. Deterministic data-gap check, no heuristic.
- **`scale_mismatch_light_routing`** — `references.scope_estimate` is persisted as `surgical` while the request body names at least 8 distinct file paths (the `multi_module` floor). The safety net for the one residual the pre-route sensor cannot close alone: the sensor is not the only writer of `scope_estimate` (phase-2-refine's module-mapping derivation and phase-3-outline's refinement both write it), so a narrow band can outlive a body that is plainly not narrow — and a narrow band suppresses S3/S4 and projects the `minimal` posture. Exact, not heuristic: it re-derives the count from the same whole-body read the sensor uses, and imports both the threshold and the path counter from the sensor rather than restating them.

Each flagged mismatch records a `warning`-severity `anti-pattern` Q-Gate finding against the `2-refine` phase (the Q-Gate store opens at `2-refine`; `1-init` is not a Q-Gate phase, and `2-refine` is exactly where classification is revisited) and emits one `decision.log` line. Findings dedup by title, so re-running the gate does not duplicate them.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status classification-validate \
  --plan-id {plan_id}
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
change_type: bug_fix
scope_estimate: null
mismatch_count: 1
mismatches[1]{mismatch,title,finding_status,hash_id}:
  feature_as_bug_fix,Classification mismatch: change_type=bug_fix over a feature-shaped request,success,a1b2c3d4
findings_emitted: 1
blocked: false
```

`blocked` is always `false` — the gate is advisory. When no mismatch fires, `mismatch_count: 0` and `findings_emitted: 0`.

### sibling-collision-check

Init-time **semantic sibling-dedup collision gate** — scans every active (non-archived) sibling plan and flags two collision classes against the plan under init. **Deterministic, read-only; zero LLM, zero writes.** Surfaced through the phase-1-init step (after `planning-lane route`); the step consumes the result and raises the user gate (proceed / rename / abort) before phase-2.

Two collision classes are flagged, in priority order:

- **source-origin match** (primary) — the same audit / lesson / issue `source_id` backs more than one active plan (a same-source fan-out). This plan's `(source, source_id)` is read from its `request.md` header and compared against every active sibling's header; a sibling whose non-empty `source_id` equals this plan's `source_id` is flagged. A description-sourced plan (no `source_id`) can never trip this check.
- **file-path overlap** (secondary) — concrete repo-relative file paths named in this plan's `request.md` body intersect a sibling's `references.json` `affected_files`. Path extraction is deterministic (a repo-relative path regex requiring a `/` segment and a trailing extension) and the match is exact normalized-string equality, so the check raises zero false positives.

Active-plan enumeration mirrors `list` — main-checkout plans merged with worktree-resident plans (a phase-5+ plan moved into its worktree), deduped by id.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status sibling-collision-check \
  --plan-id {plan_id}
```

**Output** (TOON):
```toon
status: success
plan_id: my-plan
source: lesson
source_id: EXAMPLE-SOURCE-ID
active_sibling_count: 3
source_origin_matches[1]{plan_id,source,source_id}:
  sibling-plan,lesson,EXAMPLE-SOURCE-ID
source_origin_match_count: 1
file_overlap_matches[1]{plan_id,overlap_count,overlapping_files}:
  other-plan,2,marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py;test/plan-marshall/manage-status/test_sibling_collision.py
file_overlap_match_count: 1
collision_detected: true
```

`overlapping_files` joins the per-row file list with `;` (paths never contain `;`) so each row stays a single TOON column. When no collision fires, both match lists are empty and `collision_detected: false`.

### self-test

Verify manage-status health (checks imports, phase routing table, directory access).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status self-test
```

**Output** (TOON):
```toon
status: success
passed: 4
failed: 0
```

---

## Valid Phases & Routing

Phase set, transition rules, and phase-to-skill routing are defined in [standards/status-lifecycle.md](standards/status-lifecycle.md). The standard 6-phase model (`1-init` through `6-finalize`) is sequential — the `transition` command enforces ordering.

---

## Scripts

**Script**: `plan-marshall:manage-status:manage-status`

| Command | Parameters | Description |
|---------|------------|-------------|
| `create` | `--plan-id --title --phases [--force] [--use-worktree]` | Create status.json (records `use_worktree` intent when `--use-worktree` is present; the branch and `worktree_path` are derived at phase-5-execute Step 2.5) |
| `read` | `--plan-id` | Read full status |
| `set-phase` | `--plan-id --phase` | Set current phase (marks as in_progress) |
| `update-phase` | `--plan-id --phase --status` | Update specific phase status |
| `progress` | `--plan-id` | Calculate progress percentage |
| `metadata` | `--plan-id --get/--set --field [--value]` | Get/set metadata fields |
| `title-token set` | `--plan-id --state {lock-waiting\|lock-owned\|build-busy} [--owner {build-hook\|merge-lock\|cli}]` | Write the `{owner, state, set_at}` record into `status.title_token`, replacing any existing record (last writer wins). `--owner` defaults to `cli`. No rendering — `manage-terminal-title` owns title composition + glyph/icon vocabulary. `build-busy` is the orchestration-busy state (🔨 icon-slot override). |
| `title-token clear` | `--plan-id [--owner {build-hook\|merge-lock\|cli}]` | Remove the `status.title_token` record when `--owner` matches the recorded owner or the record is stale (>3600 s). A foreign-owned live record is left intact and reported as `cleared: false, reason: foreign_owner`. Idempotent — a no-op when already absent. |
| `mark-step-done` | `--plan-id --phase --step --outcome [--display-detail] [--head-at-completion] [--loop-back-target] [--fact KEY=VALUE]... [--force]` | Record phase step outcome (+ optional display detail / HEAD SHA / loop-back target / repeatable structured `facts`) in `metadata.phase_steps` |
| `assert-step-recorded` | `--plan-id --phase --step [--require-terminal]` | Read-only verdict: reports `recorded: true` iff a terminal `metadata.phase_steps[phase][step]` outcome exists. The phase-6-finalize post-dispatch guard. With `--require-terminal`, a near-miss orphan record under a different key returns `error: step_record_mismatched_key` (carrying `orphan_key`); a truly-absent record returns `error: step_record_missing`. Zero writes. |
| `merge-authorization grant` | `--plan-id --kind --head --gap-class --granted-over --reason` | Persist a HEAD-bound merge authorization as `metadata.merge_authorizations[{kind}] = {head, gap_class, granted_over, reason, granted_at}`. A re-grant at a new HEAD overwrites the record — that overwrite IS the sanctioned re-seek, so there is no revoke verb. `--kind` and `--gap-class` accept any non-empty token; the population and each row's `authorizes:` class are declared by the Merge-Authorization Roster in `phase-6-finalize/standards/branch-cleanup.md`, not by the parser. |
| `merge-authorization check` | `--plan-id --head --gap-class` | Return every authorization record with a HEAD verdict (`valid` when `record.head` equals `--head`, `lapsed` otherwise) AND an admissibility verdict (`valid` AND `record.gap_class` equals `--gap-class`), plus `authorized_kinds`, `lapsed_kinds`, `admissible_kinds`, `inadmissible_kinds`, `any_authorized` and `any_admissible`. Deliberately takes **no** `--kind` — a per-kind filter would let one valid authorization mask a lapsed sibling. `--gap-class` is required so no caller can route on HEAD-validity alone: several kinds are granted at earlier sites at the same HEAD over a different gap. Fail-closed: a malformed or superseded record is `lapsed`, a record with no `gap_class` matches no class, and an empty store returns both aggregates false with empty lists (`absent` is never collapsed into `valid`). |
| `get-context` | `--plan-id` | Get combined status context |
| `get-worktree-path` | `--plan-id` | Resolve persisted worktree path (returns empty string when `use_worktree==false`) |
| `list` | `[--filter PHASE]` | Discover all plans across the main checkout and its worktrees (each entry tagged `location: current`/`worktree`), optionally filtered by phase |
| `transition` | `--plan-id --completed` | Mark phase done, advance to next |
| `archive` | `--plan-id [--dry-run] [--reason REASON]` | Archive completed plan; `--reason` persists to `status.metadata.archived_reason` (used by `plan-doctor stuck-low-confidence-archive` rule) |
| `delete-plan` | `--plan-id [--no-restore-lessons]` | Delete entire plan directory. Runs the lesson carry-back FIRST, resolving the corpus through the **main-anchored** store handle (never the cwd-keyed `base_path()`), and reports `lesson_carry_back_action` over the closed vocabulary enumerated in full under [Lesson carry-back (and the veto)](#lesson-carry-back-and-the-veto) — that table is the single home for the value set — plus `lesson_store_resolution`, `lessons_dir`, `restored_lesson_ids`, and `skipped_lessons`. **Vetoes the deletion** with `error: lesson_carry_back_incomplete` when any carried lesson did not land — the directory holds the only copy, so it is left intact. `--no-restore-lessons` skips the carry-back and therefore the veto. |
| `route` | `--phase` | Get skill name for phase |
| `get-routing-context` | `--plan-id` | Get combined routing context |
| `change-type-heuristic` | `--plan-id [--persist]` | Deterministic change-type classifier for phase-3-outline Step 4. Reads the clarified-request narrative (falling back to original_input) and scores it against a fixed keyword table — returns one of `feature`, `bug_fix`, `tech_debt`, `enhancement`, `verification`, `analysis`, or `ambiguous=true` when no keyword fires / two change types tie / confidence < 0.7. With `--persist`, writes the resolved change_type to `status.metadata.change_type` (skipped in the ambiguous branch so the LLM `detect-change-type` workflow is the single writer there). |
| `scope-estimate-heuristic` | `--plan-id [--persist]` | Deterministic pre-route `scope_estimate` classifier for phase-1-init, run BEFORE `planning-lane route` so the router's S2 signal reads a real value instead of `None`. Scores the **whole** `request.md` body (heading-blind — the entire file minus its own `# Request` title line; no section is selected, so an ingested spec's own `##` headings cannot truncate it) from two measurements taken with zero architecture queries: the count of distinct `dir/name.ext` path references, and the presence of a glob / pattern fan-out marker (`/**`, `**/`, `/*`, `*/`, `*.ext`). The band table, in evaluation order, with the `band_rule` each row reports: body absent / unreadable / empty → `none` (`unscoreable_body`); body not safely scannable in full → `multi_module` (`scan_incomplete`); fan-out marker present → `multi_module` (`fan_out_marker`); ≥ 8 distinct paths → `multi_module` (`path_count_at_or_above_multi_module_floor`); 4–7 distinct paths → `single_module` (`path_count_middle_band`); 1–3 distinct paths and no fan-out marker → `surgical` (`path_count_at_or_below_surgical_max`); no path at all in a non-empty body → `single_module` (`pathless_non_empty_body`). The band line is **scale-truthful in both directions**: a fan-out marker is a declared inability to enumerate the file set, so it **widens** to `multi_module` rather than narrowing, and the `**` alternatives of the marker are path-adjacent (`/**` / `**/`) so markdown bold does not register as fan-out. `scan_incomplete` is the ReDoS-defense counterpart of the same discipline: the path scan is bounded per line and by a total character budget (CWE-1333), so a body too large or adversarially-repetitive to scan in full yields a path total that is a **lower bound, not a count** — that row therefore wins BEFORE the path-count rows are consulted, so a partial total can never be read as an accurate narrow band. `none` is the **declared unknown**, never a band guessed from zero bytes; the companion `scope_resolved` boolean distinguishes a classified band (`true`) from it (`false`), and `none` is a deep-biasing S2 value, so an unscoreable request widens the lane rather than narrowing it. The path counter counts distinct path-shaped **strings**, not work targets: it cannot separate a target from a citation and deliberately requires a directory separator (a bare filename is intentionally excluded) — both residuals push the band up the `surgical` → `single_module` → `multi_module` line, never down. With `--persist`, writes the result to `references.json`'s `scope_estimate` and emits one decision-log line. The deep-lane refine Step 9 module-mapping derivation may later overwrite the coarse guess. |
| `aggregate-confidence` | `--plan-id [--scores-file PATH] [--correctness N] [--completeness N] [--consistency N] [--non-duplication N] [--ambiguity N] [--module-mapping N] [--persist]` | Weighted-math confidence aggregator for phase-2-refine Step 10. Computes the overall confidence from per-dimension scores (0..100) using the fixed weights `correctness 20% / completeness 20% / consistency 20% / non-duplication 10% / ambiguity 20% / module-mapping 10%`. Missing dimensions default to 0 and are recorded in `missing_dimensions`. Scores can be supplied via `--scores-file` (JSON object keyed by dimension) and / or individual CLI flags; flags take precedence on conflict. With `--persist`, the overall confidence is written to `status.metadata.confidence`. |
| `planning-lane route` | `--plan-id [--lane-override deep\|light] [--persist]` | Deterministic planning-lane router. Resolves `planning_lane ∈ {light, deep}` from the DQ1 signal set (S1–S7) plus a `request.md` regex with zero discovery; `plan.phase-1-init.deep_lane` (`always`/`never`/`auto`) short-circuits the signals. Default is light; any deep signal forces deep. Also projects the recommended `execution_profile` posture (`minimal`/`standard`/`full`) over the same signals, independent of the deep-lane gate. With `--persist`, writes `status.metadata.planning_lane` + `status.metadata.execution_profile`. Emits one decision-log line naming every signal value, the winning predicate, the projected posture, and the `scope_provenance` block that explains which band rule fired. |
| `planning-lane escalate` | `--plan-id --trigger explosion\|premise\|cross_cutting [--persist]` | One-way light→deep ratchet. Sets `planning_lane=deep` + `lane_escalated=true` + `escalation_trigger`; the flag is sticky and there is no downgrade path. With `--persist`, writes the mutation to `status.metadata`. |
| `classification-validate` | `--plan-id` | Deterministic classification-validation gate (flag-not-block). Cross-checks `change_type` / `scope_estimate` against cheap request signals; flags `feature_as_bug_fix` (bug_fix stamp over a non-ambiguous feature narrative), `non_empty_affected_files_with_null_scope`, and `scale_mismatch_light_routing` (a persisted `surgical` band over a body the scope sensor reads as `multi_module` — naming >= 8 distinct paths, or not safely scannable in full, which the sensor bands `multi_module` because a truncated path total is a lower bound rather than a count), recording a `warning` `anti-pattern` Q-Gate finding against `2-refine` per mismatch. NEVER blocks routing; runs automatically as a pre-route pass inside `planning-lane route`. |
| `sibling-collision-check` | `--plan-id` | Init-time semantic sibling-dedup collision gate (deterministic, read-only). Scans active (non-archived) sibling plans and flags `source_origin_matches` (same audit / lesson / issue `source_id` backing more than one active plan) and `file_overlap_matches` (concrete request-body paths intersecting a sibling's `references.json` `affected_files`); returns a `collision_detected` boolean. phase-1-init raises the user gate (proceed / rename / abort) before phase-2. |
| `self-test` | _(none)_ | Verify manage-status health |

---

## Canonical invocations

The canonical argparse surface for `manage-status.py`. The D4 plugin-doctor analyzer
(`_analyze_manage_invocation.py`) reads this section as source-of-truth for markdown
notation occurrences across the marketplace. Consuming skills xref this section by
name (e.g., "see `manage-status` Canonical invocations → `transition`") instead of
restating the command inline.

### create

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status create \
  --plan-id PLAN_ID --title TEXT --phases CSV \
  [--force] \
  [--use-worktree] \
  [--store {plans|orchestrator}]
```

`--phases` is required for the default `plans` store and ignored for `--store orchestrator` (the `kind=orchestrator` schema carries a single three-value `phase` field instead of a phase list).

### read

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id PLAN_ID [--store {plans|orchestrator}]
```

### set-phase

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status set-phase \
  --plan-id PLAN_ID --phase PHASE
```

### update-phase

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-phase \
  --plan-id PLAN_ID --phase PHASE --status {pending|in_progress|done}
```

### progress

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status progress \
  --plan-id PLAN_ID
```

### metadata

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id PLAN_ID --field FIELD \
  (--get | --set --value VALUE) \
  [--store {plans|orchestrator}]
```

### update-field

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-field \
  --plan-id PLAN_ID --field FIELD --value VALUE \
  [--store orchestrator]
```

Orchestrator store only (`--store` defaults to `orchestrator`). Sets one top-level field of a `kind=orchestrator` status.json: `phase` (`init|orchestrating|closed`), `resume_anchor` (verbatim string), or the list fields `workstreams` / `plans` (JSON-array `--value`). The plans store has no generic field setter — plan status mutations go through the dedicated verbs.

### get-context

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-context \
  --plan-id PLAN_ID
```

### get-worktree-path

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-worktree-path \
  --plan-id PLAN_ID
```

### list

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status list \
  [--filter PHASES_CSV]
```

### transition

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status transition \
  --plan-id PLAN_ID --completed PHASE
```

### archive

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status archive \
  --plan-id PLAN_ID [--dry-run] [--reason REASON]
```

### route

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status route \
  --phase PHASE
```

### get-routing-context

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-routing-context \
  --plan-id PLAN_ID
```

### delete-plan

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status delete-plan \
  --plan-id PLAN_ID [--no-restore-lessons]
```

The lesson carry-back runs by default and can VETO the deletion: when any carried `lesson-*.md` did not land in the main-anchored corpus, the verb returns `error: lesson_carry_back_incomplete` and leaves the plan directory intact (it holds the only copy). `--no-restore-lessons` skips the carry-back, and therefore the veto, deleting any carried lesson with the directory.

### mark-step-done

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id PLAN_ID --phase PHASE --step STEP_ID \
  --outcome {done|skipped|loop_back|failed} \
  [--force] [--display-detail TEXT] [--head-at-completion SHA] \
  [--loop-back-target {5-execute|6-finalize}] \
  [--fact KEY=VALUE]...
```

### assert-step-recorded

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status assert-step-recorded \
  --plan-id PLAN_ID --phase PHASE --step STEP_ID \
  [--require-terminal]
```

### merge-authorization — grant

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status merge-authorization grant \
  --plan-id PLAN_ID --kind KIND --head SHA --gap-class GAP_CLASS \
  --granted-over TEXT --reason TEXT
```

Writes `metadata.merge_authorizations[KIND] = {head, gap_class, granted_over, reason, granted_at}` and returns that record. A re-grant at a new HEAD overwrites the previous one and additionally reports `previous_head`.

### merge-authorization — check

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status merge-authorization check \
  --plan-id PLAN_ID --head SHA --gap-class GAP_CLASS
```

Returns `any_authorized`, `any_admissible`, `authorized_kinds[]`, `lapsed_kinds[]`, `admissible_kinds[]`, `inadmissible_kinds[]`, and a `records[]` table carrying one `verdict` plus one `admissible` flag per record (`valid` when `record.head` equals `--head`; `admissible` when additionally `record.gap_class` equals `--gap-class`). There is no `--kind` flag. Fail-closed: an empty store returns both aggregates false with empty lists.

### change-type-heuristic

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status change-type-heuristic \
  --plan-id PLAN_ID [--persist]
```

### scope-estimate-heuristic

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status scope-estimate-heuristic \
  --plan-id PLAN_ID [--persist]
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
scope_estimate: surgical
scope_resolved: true
distinct_path_count: 2
distinct_paths[2]:
  - marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md
  - test/plan-marshall/manage-status/test_planning_lane.py
persisted: true
```

`scope_resolved: false` is the **declared unknown** — the request body was unscoreable, so
`scope_estimate` is `none` (a "cannot tell" verdict that biases S2 deep), not a measured
narrow band. Reading `scope_estimate` alone cannot make that distinction.

### aggregate-confidence

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status aggregate-confidence \
  --plan-id PLAN_ID \
  [--scores-file PATH] \
  [--correctness N] [--completeness N] [--consistency N] \
  [--non-duplication N] [--ambiguity N] [--module-mapping N] \
  [--persist]
```

### planning-lane

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status planning-lane route \
  --plan-id PLAN_ID
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status planning-lane escalate \
  --plan-id PLAN_ID --trigger explosion
```

### classification-validate

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status classification-validate \
  --plan-id PLAN_ID
```

### sibling-collision-check

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status sibling-collision-check \
  --plan-id PLAN_ID
```

### self-test

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status self-test
```

---

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error Code | Exit Code | Cause |
|------------|-----------|-------|
| `invalid_plan_id` | 1 | Plan ID not in kebab-case format |
| `file_not_found` | 1 | status.json doesn't exist |
| `file_exists` | 1 | status.json already exists (use `--force`) |
| `invalid_phase` | 1 | Phase name not in the phases list (set-phase, update-phase, transition) |
| `invalid_title_token_state` | 1 | `title-token set`: `--state` value not in `lock-waiting`/`lock-owned`/`build-busy`. (Argparse `choices` normally catches this at parse time; this error fires only when the validation is bypassed at the API layer.) |
| `invalid_title_token_owner` | 1 | `title-token set`/`clear`: `--owner` value not in `build-hook`/`merge-lock`/`cli`. (Argparse `choices` normally catches this at parse time; this error fires only when the validation is bypassed at the API layer.) |
| `phase_not_found` | 1 | Phase doesn't exist in this plan's status.json phases array |
| `unknown_phase` | 1 | Phase name not in the static valid phases set (`1-init` through `6-finalize`); only used by `route` command |
| `plan_not_found` | 1 | Plan directory does not exist (delete-plan command) |
| `lesson_carry_back_incomplete` | 1 | `delete-plan`: at least one `lesson-*.md` the plan carries did NOT land in the main-anchored corpus (a destination collision, a traversal-shaped lesson id, or a store that would not resolve), so the plan directory holds the only copy of it. **The directory is NOT deleted.** `skipped_lessons[]` names each un-landed id with its `reason`, and `lesson_store_resolution` reports which substrate was reached. Resolve the collision, or pass `--no-restore-lessons` to delete and discard the lesson deliberately. |
| `not_found` | 1 | Plan directory not found (archive command) |
| `not_found` | 0 | Metadata field doesn't exist — valid query result (returns `value: null`), not an error |
| `conflict` | 1 | `mark-step-done`: step already has a different outcome and `--force` was not supplied |
| `legacy_string_entry` | 1 | `mark-step-done`: existing entry uses the pre-migration bare-string shape; caller must migrate to dict shape before retrying |
| `invalid_outcome` | 1 | `mark-step-done`: outcome not in `done`/`skipped`/`loop_back`/`failed` |
| `invalid_argument` | 1 | `mark-step-done`: empty `--phase` or `--step` |
| `missing_loop_back_target` | 1 | `mark-step-done`: `--outcome=loop_back` supplied without `--loop-back-target`. The flag is REQUIRED on every loop_back outcome (no backwards-compat fallback). |
| `invalid_loop_back_target` | 1 | `mark-step-done`: `--loop-back-target` value not in `5-execute`/`6-finalize`. (Argparse `choices` normally catches this at parse time; this error fires only when the validation is bypassed at the API layer.) |
| `unexpected_loop_back_target` | 1 | `mark-step-done`: `--loop-back-target` supplied alongside an outcome other than `loop_back`. The flag is FORBIDDEN on `done`/`skipped`/`failed` outcomes. |
| `invalid_fact` | 1 | `mark-step-done`: a `--fact` token has no `=` separator, or an empty key. The offending token is echoed as `offending_token`; the call is rejected before any write. |
| `step_record_missing` | 0 | `assert-step-recorded --require-terminal`: no terminal record exists under any key for the named phase (the dispatched step returned without recording a `mark-step-done` outcome). Exit code is 0 — the post-dispatch guard branches on the TOON `error` field, not the process exit code. |
| `step_record_mismatched_key` | 0 | `assert-step-recorded --require-terminal`: the queried step has no terminal record, but a near-miss orphan terminal record exists under a different key in the same phase (the dispatched step recorded under the wrong key — e.g. a bare skill name instead of its fully-qualified manifest `step_id`). Carries `orphan_key` and `orphan_outcome`. Exit code is 0 — the guard branches on the TOON `error` field. |
| `worktree_unresolved` | 1 | `phase_handshake verify`: `metadata.use_worktree==true` and `metadata.worktree_path` is non-empty but does not resolve on the filesystem. `get-worktree-path` does not emit this error — it returns `worktree_state: pending` for the pre-materialization state. |

---

## Integration

**Called by**: `plan-marshall:plan-marshall` orchestrator for phase transitions, `phase-1-init` for initial status creation, and `phase-6-finalize` for archiving.

### With phase skills

Phase skills read/update status through manage-status:
- phase-1-init: Creates status with `create`
- phase-2-refine onwards: Uses `set-phase`, `metadata`, `get-context`, `transition`
- phase-6-finalize: Uses `archive` for completed plans

### With agents

Agents use `metadata` to store change_type and other classification data.

## Related

- `plan-marshall` — Orchestrator that drives phase transitions
- `phase-1-init` through `phase-6-finalize` — Phase-specific skills routed to by manage-status
- `manage-metrics` — Augments phase tracking with timing and token data
- `manage-config` — System configuration consumed by status operations

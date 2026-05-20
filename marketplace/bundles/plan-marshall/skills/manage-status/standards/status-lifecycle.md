# Status Lifecycle

Phase and plan lifecycle model for manage-status.

## Phase State Machine

```
pending ──→ in_progress ──→ done
```

| State | Meaning |
|-------|---------|
| `pending` | Phase not yet started |
| `in_progress` | Phase is actively being worked on |
| `done` | Phase completed |

### Transition Rules

- Only forward transitions are supported (pending → in_progress → done)
- `set-phase` marks the target phase as `in_progress`
- `transition --completed X` marks phase X as `done` and advances to the next phase
- The first phase is automatically marked `in_progress` on plan creation

## Plan Lifecycle

```
create ──→ [phases 1-6] ──→ archive
                              │
                              └──→ delete-plan (alternative)
```

### Archive

- Moves plan directory to `.plan/archived-plans/YYYY-MM-DD-{plan_id}/`
- Supports `--dry-run` preview
- Archived plans subject to retention cleanup (default: 5 days)

### Delete

- Permanently removes the plan directory
- Used by plan-init when user selects 'Replace' for existing plan
- Logs file count before deletion for audit trail

## Phase Names

> Phase names follow the standard 6-phase model. See [manage-contract.md](../../ref-workflow-architecture/standards/manage-contract.md) § Phase Names for the canonical definition.

## Routing

The `route` command maps phases to workflow skills. This is a fallback mapping — the authoritative source is `manage-config`'s `skill_domains.system.workflow_skills` in `marshal.json`.

| Phase | Skill |
|-------|-------|
| `1-init` | `plan-marshall:phase-1-init` |
| `2-refine` | `plan-marshall:phase-2-refine` |
| `3-outline` | `plan-marshall:phase-3-outline` |
| `4-plan` | `plan-marshall:phase-4-plan` |
| `5-execute` | `plan-marshall:phase-5-execute` |
| `6-finalize` | `plan-marshall:phase-6-finalize` |

## Title-Body Artifact

Every mutation that touches phase, short_description, or archive lifecycle publishes a plaintext artifact alongside `status.json` so per-target session renderers can compose terminal titles without re-deriving plan state from the filesystem.

| Property | Value |
|----------|-------|
| Location | `{plan_dir}/title-body.txt` (sibling of `status.json`) |
| Content shape | `pm:{current_phase}` — or `pm:{current_phase}:{short_description}` when `short_description` is present |
| Encoding | UTF-8, exactly one terminating `\n`, no leading or trailing whitespace beyond that |
| Writer | `manage-status` mutation paths (`create`, `set-phase`, `transition`, `archive`) plus the `read` cold-bootstrap branch |
| Reader | Per-target `session render-title` operation (specified in the cluster-01 platform-api design doc) |

### Lifecycle

| Event | Effect on `title-body.txt` |
|-------|----------------------------|
| `create` | File created after `status.json` write. |
| `set-phase` | File rewritten atomically with the new phase. |
| `transition` (next phase) | File rewritten atomically with the new phase. |
| `transition` (last phase → `current_phase = complete`) | File deleted. |
| `archive` | File deleted from the live plan-dir before the directory is moved into `.plan/archived-plans/`. |
| `read` on a non-terminal plan when the file is absent | File republished via the cold-bootstrap branch — covers fresh tabs that opened after the writer's last fire. |
| `delete-plan` | File removed transitively with the plan directory. |

### Terminal Phases

When `status.current_phase` ∈ `{complete, archived}`, the helper deletes the file rather than writing it. "File absent → no plan-title to render" is the only conditional the reader carries — there is no resolver chain, no fallback to `status.json`, no walk-up plan discovery.

### Atomic-Write Contract

The publication helper writes via `atomic_write_file` (temp-file + `os.replace`), so a process interrupt mid-write cannot leave the file in a partially-written state. A failed publish is silently swallowed — the next successful mutation self-heals, consistent with the existing terminal-title hook semantics.

## Metadata

Arbitrary key-value pairs stored in `status.json` under the `metadata` object. Common fields:

| Field | Set By | Purpose |
|-------|--------|---------|
| `change_type` | phase-3-outline Step 4 (`manage-status:change-type-heuristic` script; LLM fallback via `effort` when the heuristic is ambiguous) | feature, bug_fix, tech_debt, etc. |
| `confidence` | phase-2-refine | Request clarity confidence (0-100) |

Metadata fields are promoted to top-level in `get-context` output for convenience.

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

Standard 6-phase model (must match `constants.PHASES`):

| Phase | Purpose |
|-------|---------|
| `1-init` | Initialize plan structure |
| `2-refine` | Clarify request until confident |
| `3-outline` | Create solution outline with deliverables |
| `4-plan` | Create tasks from deliverables |
| `5-execute` | Execute implementation tasks |
| `6-finalize` | Finalize with commit/PR |

## Routing

The `route` command maps phases to workflow skills. This is a fallback mapping — the authoritative source is `manage-config`'s `skill_domains.system.workflow_skills` in `marshal.json`.

## Metadata

Arbitrary key-value pairs stored in `status.json` under the `metadata` object. Common fields:

| Field | Set By | Purpose |
|-------|--------|---------|
| `change_type` | detect-change-type-agent | feature, bug_fix, tech_debt, etc. |
| `confidence` | phase-2-refine | Request clarity confidence (0-100) |

Metadata fields are promoted to top-level in `get-context` output for convenience.

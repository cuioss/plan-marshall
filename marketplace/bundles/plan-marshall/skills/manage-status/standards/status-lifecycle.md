# Status Lifecycle

Phase and plan lifecycle model for manage-status.

## Phase State Machine

```text
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

```text
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

## Title Token

`manage-status` performs **no terminal-title rendering**. It stores a bare state marker — `status.title_token` — alongside `current_phase` and `short_description` in `status.json`, which is the single source of persisted title state. The `manage-terminal-title` composer renders the title from those fields, and `platform-runtime` reads `status.json` and emits the result per platform. manage-status writes only the state string; the glyph/icon vocabulary and the `{icon} {glyph} {body}` assembly live entirely in `manage-terminal-title`.

| Property | Value |
|----------|-------|
| Location | `status.title_token` field in `status.json` |
| Content shape | One of `lock-waiting`, `lock-owned`, `build-busy` |
| Writer | `manage-status title-token set/clear` (the ONLY writer; no mutation path auto-writes it) |
| Consumer | `manage-terminal-title` composer (owns the state → glyph/icon rendering), invoked by `platform-runtime` after it reads `status.json` |

The `title-token set --state {state}` verb writes the field; `title-token clear` removes it (idempotent). Both validate against the closed state set (`TITLE_TOKEN_STATES`) and emit a `[MANAGE-STATUS]` work-log line. No phase-mutation path (`create`, `set-phase`, `transition`, `archive`) touches `title_token` — it is set and cleared explicitly by the callers that own its lifecycle.

The three states split into two rendering classes, both owned by the composer:

| State | Set/cleared by | Composer rendering |
|-------|----------------|--------------------|
| `lock-waiting` | the merge-lock coordination machinery | ⏳ glyph, prepended to the body |
| `lock-owned` | the merge-lock coordination machinery | 🔒 glyph, prepended to the body |
| `build-busy` | the orchestration layer (bracketing a long-running call) | 🔨 **icon-slot override** — forced into the icon slot, NOT a prepended glyph |

`build-busy` is the orchestration-busy state: it is set before, and cleared after, a long-running orchestration Bash call (a resolved build / verify / coverage command, a `git push`, a CI-wait) so the title surfaces the 🔨 build symbol for the whole blocking window. `manage-status` only persists the bare `build-busy` string; the icon-slot-override rendering and the precedence against the lock glyphs and process icons live entirely in `manage-terminal-title`. For the normative orchestration requirement — when the state is set/cleared and the live-push mechanics — see [`persona-plan-marshall-agent`](../../persona-plan-marshall-agent/SKILL.md).

For the full three-way split (state / composer / resolve+emit), the glyph and icon vocabulary, and the read-from-`status.json` (live + archived fallback) emit path, see `manage-terminal-title/standards/terminal-title-architecture.md`.

## Metadata

Arbitrary key-value pairs stored in `status.json` under the `metadata` object. Common fields:

| Field | Set By | Purpose |
|-------|--------|---------|
| `change_type` | phase-3-outline Step 4 (`manage-status:change-type-heuristic` script; LLM fallback via `effort` when the heuristic is ambiguous) | feature, bug_fix, tech_debt, etc. |
| `confidence` | phase-2-refine | Request clarity confidence (0-100) |

Metadata fields are promoted to top-level in `get-context` output for convenience.

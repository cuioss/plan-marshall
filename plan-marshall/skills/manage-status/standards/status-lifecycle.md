# Status Lifecycle

Phase and plan lifecycle model for manage-status. Two status kinds exist side by side: the plan status.json (the default `plans` store, everything below up to and including Metadata) and the lean `kind=orchestrator` status.json (the `orchestrator` store — see the Orchestrator Status section at the end).

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
| Writer | `manage-status title-token set/clear` (the only explicit writer); additionally `archive` pops the token unconditionally, and `transition`/`set-phase` pop a stale `build-busy` token only (a phase-boundary safety-net that leaves lock tokens untouched) |
| Consumer | `manage-terminal-title` composer (owns the state → glyph/icon rendering), invoked by `platform-runtime` after it reads `status.json` |

The `title-token set --state {state}` verb writes the field; `title-token clear` removes it (idempotent). Both validate against the closed state set (`TITLE_TOKEN_STATES`) and emit a `[MANAGE-STATUS]` work-log line. `title-token set/clear` is the only explicit writer of `title_token`. In addition, three phase-mutation paths clear it defensively: `archive` pops the token unconditionally — an archived plan has no live session to render it, so any leftover token would freeze a stale glyph in the archived snapshot — while `transition` and `set-phase` pop a stale `build-busy` token only, the phase-boundary safety-net that keeps a missed clear from leaking the 🔨 build icon across a phase change. The live lock-coordination tokens (`lock-waiting`, `lock-owned`) survive `transition`/`set-phase` untouched, and `create` never touches `title_token`.

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

## Orchestrator Status (`kind=orchestrator`)

Orchestrator epics persist a second, deliberately lean status kind under the main-anchored orchestrator store — `.plan/local/orchestrator/{slug}/status.json`, resolved via `get_store_dir('orchestrator', slug)`. It is the machine authority for an epic's plan queue and resume state (see `persona-marshall-orchestrator/standards/orchestration-model.md` for the consuming contract).

### Schema

```json
{
  "kind": "orchestrator",
  "title": "Epic title",
  "phase": "init | orchestrating | closed",
  "workstreams": [],
  "plans": [
    {
      "id": "PLAN-01",
      "slug": "short-slug",
      "workstream": "WS-01",
      "status": "staged",
      "plan_marshall_plan_id": "",
      "pr": "",
      "landing": ""
    }
  ],
  "resume_anchor": "the exact next action a resuming session takes",
  "metadata": {},
  "created": "...",
  "updated": "..."
}
```

### Metadata

Arbitrary key-value pairs stored under the epic's `metadata` object. Common fields:

| Field | Set By | Purpose |
|-------|--------|---------|
| `parallelization_scope` | `marshall-orchestrator` `init.md` (operator `AskUserQuestion`, asked once per epic) | Maximum number of concurrently-launched plans the orchestrator may emit; positive integer, default `1` (strictly sequential) when unset |

The field is written through the existing `metadata --store orchestrator` verb, which accepts any `snake_case` key without a whitelist — so the knob requires no script or JSON-schema change. For the selection and disjointness rules that consume it, see `persona-marshall-orchestrator/standards/orchestration-model.md` § Parallelization by Surface Disjointness.

### Three-Phase Lifecycle

```text
init ──→ orchestrating ──→ closed
```

| Phase | Meaning |
|-------|---------|
| `init` | Epic scaffolded; decomposition not yet complete |
| `orchestrating` | Active: plans staged, launched, analyzed, reconciled |
| `closed` | Epic frozen into `history.md`; tree retained as audit record |

There is NO phase-transition machinery for the orchestrator kind — no `phases[]` list, no `set-phase`/`update-phase`/`transition`. The `phase` field is a plain three-value field set via `update-field --field phase --value {init|orchestrating|closed}`.

### Verb Surface

The orchestrator store is served by exactly four verbs (see Canonical invocations in `SKILL.md`):

| Verb | Operation |
|------|-----------|
| `create --store orchestrator` | Create the `kind=orchestrator` status.json (`--phases` ignored) |
| `read --store orchestrator` | Read the epic status document |
| `update-field` | Set a top-level field: `phase`, `resume_anchor`, or the JSON-array list fields `workstreams` / `plans` |
| `metadata --store orchestrator` | Get/set entries of the `metadata` object |

Plan discovery (`list`), archiving, routing, title-token, and every other plan-store verb do NOT apply to the orchestrator store — orchestrator epics are structurally invisible to plan discovery because it globs only `.plan/local/plans/`.

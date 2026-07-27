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

`manage-status` performs **no terminal-title rendering**. It stores a structured state record — `status.title_token` — alongside `current_phase` and `short_description` in `status.json`, which is the single source of persisted title state. The `manage-terminal-title` composer renders the title from those fields, and `platform-runtime` reads `status.json` and emits the result per platform. manage-status writes only the state record; the glyph/icon vocabulary and the `{icon} {glyph} {body}` assembly live entirely in `manage-terminal-title`.

| Property | Value |
|----------|-------|
| Location | `status.title_token` field in `status.json` |
| Content shape | `{"owner": …, "state": …, "set_at": …}` — `state` is one of `lock-waiting`, `lock-owned`, `build-busy`; `owner` is one of `build-hook`, `merge-lock`, `cli`; `set_at` is a UTC ISO-8601 instant |
| Writer | `manage-status title-token set/clear` (the CLI writer, `owner: cli` by default), the `build-hook` render assist, and `merge-lock`; additionally `archive` pops the record unconditionally |
| Consumer | `manage-terminal-title` composer (owns the state → glyph/icon rendering), invoked by `platform-runtime` after it reads `status.json` |

The `title-token set --state {state} [--owner {owner}]` verb writes the record with a fresh `set_at`; `title-token clear [--owner {owner}]` removes it. `set` validates `{state}` against the closed state set (`TITLE_TOKEN_STATES`) and `{owner}` against the owner vocabulary (`TITLE_TOKEN_OWNERS`), and both verbs emit a `[MANAGE-STATUS]` work-log line.

**Arbitration.** A `set` from any owner replaces the record wholesale — last writer wins, and the record always names its current owner. A `clear` is **owner-scoped**: only the recorded `owner` may clear its own token, and a foreign clear is a reported no-op (`cleared: false`, `reason: foreign_owner`). That asymmetry — open SET, scoped CLEAR — is what makes ownership meaningful: a lock glyph owned by `merge-lock` cannot be clobbered by an unrelated build bracket.

**Staleness is a read-side property.** A record whose `set_at` is older than `TITLE_TOKEN_STALE_AFTER_SECONDS` (3600 s) is stale and may be cleared or replaced by **any** writer. There is no phase-boundary sweep: `transition` and `set-phase` clear nothing, because a sweep only fires when a phase happens to change and would leave a stranded token alive indefinitely otherwise. Every reader resolves staleness through `_status_core.title_token_is_stale` / `read_title_token`, so a stranded token self-heals on the next read. `archive` remains the one owner-agnostic pop — an archived plan holds no live coordination state worth arbitrating over — and `create` never touches `title_token`.

**Concurrency.** Four independent writers (the `build-hook` `PreToolUse:Bash`/`PostToolUse:Bash` assist, `merge-lock`'s two lock surfaces, and `merge-lock`'s clear) mutate this one field from separate executor subprocesses. Both verbs therefore run their read-modify-write inside a single `rmw_json` critical section, and the clear takes its arbitration decision against the record read *inside* the guard — closing the check-then-act window a plain read-then-write would leave open.

Those four are the writers that *target* the field; they are not the only processes that can destroy a record. Every full-document `status.json` writer — `set-phase`, `transition`, `create`, and every other caller that commits a whole document assembled from a snapshot read taken before the commit — would restore that snapshot's stale `title_token` if it committed after a `set`. That second window is closed at the shared write seam rather than per verb: `_status_core.write_status` commits inside the **same** `rmw_json` guard (it resolves the same path, so it takes the same guard file) and carries over the `title_token` read *inside* the guard instead of the caller's snapshot value. `archive` is the sole opt-out (`preserve_title_token=False`), because its owner-agnostic pop is a deliberate discard rather than an instance of this race.

The three states split into two rendering classes, both owned by the composer:

| State | Set/cleared by | Composer rendering |
|-------|----------------|--------------------|
| `lock-waiting` | the merge-lock coordination machinery (`owner: merge-lock`) | ⏳ glyph, prepended to the body |
| `lock-owned` | the merge-lock coordination machinery (`owner: merge-lock`) | 🔒 glyph, prepended to the body |
| `build-busy` | the `build-hook` render assist bracketing a Bash build window (`owner: build-hook`) | 🔨 **icon-slot override** — forced into the icon slot, NOT a prepended glyph |

`build-busy` is the orchestration-busy state: the `PreToolUse:Bash` render assist sets it when a build-wrapper invocation enters, and the paired `PostToolUse:Bash` assist clears it when that Bash call exits, so the title surfaces the 🔨 build symbol for the whole blocking window. Both halves are machine-driven — no LLM turn owns the clear. `manage-status` only persists the record; the icon-slot-override rendering and the precedence against the lock glyphs and process icons live entirely in `manage-terminal-title`.

The record shape, the owner vocabulary, the arbitration rule, and the staleness threshold are specified once in `manage-terminal-title/standards/terminal-title-architecture.md` § Channel Delivery Contract ruling (c) and are not restated in normative form here.

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

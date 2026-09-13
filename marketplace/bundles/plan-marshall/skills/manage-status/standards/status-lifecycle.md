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

### Loop-back re-entry marker: two consumption points

A backward `set-phase` — one whose target phase precedes the current phase in the plan's phase list — is a sanctioned **loop-back re-entry**. It re-opens the target phase as `in_progress` (the one sanctioned backward status move, which is why the forward-only rule above describes the ordinary path rather than an invariant) and persists `metadata.loop_back_reentry` as `{from_phase, to_phase, at}`. The marker is a *scheduling* record: a re-entered phase re-captures its invariants against a tree that has legitimately moved on, so handshake drift at the next guarded boundary is guaranteed by construction, and the marker is what authorises auto-resolving exactly that drift.

A backward `set-phase` never clears a **later** phase, so the phase it re-opens is additive: a plan looping back from `6-finalize` to `5-execute` then holds **two** phases `in_progress` at once. That is the ordinary way a plan arrives in the multi-open-phase state the archive post-condition below has to close.

**There is exactly one marker, and it has two consumption points.** A reader who sees only the first would wrongly conclude the transition path is the only one:

| Consumption point | Reached when | What is recorded |
|---|---|---|
| `transition` at a guarded boundary | The re-entered phases reach the next guarded boundary (today `6-finalize`) | The marker is cleared. On drift it authorises one auto-override re-capture; on a **clean** verify it is cleared anyway, so a later genuinely-unscheduled drift cannot find a stale marker and have it auto-overridden |
| `archive` | The plan is archived while a re-entry is still open, so it never reaches that boundary at all | The marker is cleared and `metadata.loop_back_reentry_outcome` records `outcome: ended_without_completing` alongside the marker's `from_phase` / `to_phase`, its `scheduled_at`, and `consumed_at` / `consumed_by: archive` |

Both points consume the **same** marker; neither introduces a second one. At `archive` the pop and the outcome write land in the **same write that closes the phases** — deliberately not a follow-up write, because `shutil.move` has by then invalidated the live plan path. Without this second point the marker would ride into the permanent record still asserting that a loop-back was in flight for a plan that had already finished.

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

#### Phase-closure post-condition

The archived `status.json` is the plan's **permanent record**, so `archive` closes the plan's open phases before moving the directory. The write happens while the live plan path still resolves — a follow-up `transition` call cannot do it, because the move has already invalidated that path. Three parts, and all three are load-bearing:

1. **Every** phase recorded as `in_progress` is closed to `done` — not just the first one found. A plan holding more than one open phase (a loop-back re-entry is the ordinary way to get there) would otherwise keep the second one recorded as running in the permanent record, so the archive would assert that a phase is still in flight for a plan that has finished.
2. Every phase whose status is in `UNTOUCHED_PHASE_STATUSES` — derived as `VALID_PHASE_STATUSES - {in_progress, done}`, today exactly `{pending}` — is **left alone**. `in_progress` is the only *closable* status: it names a phase that really did start, so recording it `done` closes a genuine record. Writing `done` onto a `pending` phase would instead fabricate a fresh false record of work that never happened, which is the opposite of the defect in (1) and equally a falsification. A never-started phase therefore stays `pending` in the archive.
3. `current_phase` becomes `complete` once **no phase remains `in_progress`**. This is deliberately *not* "every phase is `done`": that predicate can never hold for a plan abandoned mid-lifecycle, whose untouched `pending` phases are not `done` and must stay that way, so such a plan was archived frozen at its last phase and never reached the post-finalize sentinel its dormant consumers match on (the phase-6-finalize `current_phase: complete` check, and `cleanup --filter complete`).

A plan abandoned mid-lifecycle consequently archives as `current_phase: complete` with its started phases `done` and its unstarted phases still `pending` — a record that says what happened rather than one that claims the whole plan ran.

The predicate behind (1) and (3) is `_status_core.in_progress_phases`, and the `census` verb's open-phase reporting consumes that same function. The set of phases archive closes and the set census reports as open are therefore one answer to one question, rather than two local re-spellings of `status == in_progress` free to drift apart.

#### Deferred requirement: the phase record and the metrics ledger are not cross-checked

Two independent accounts of the same phase lifecycle exist side by side, and **nothing currently reconciles them**:

| Account | Owner | What it records |
|---------|-------|-----------------|
| The phase record — `status.json`'s `phases[]` plus `current_phase` | `manage-status` (this skill) | Which phase a plan is in, and each phase's `pending` / `in_progress` / `done` status |
| The metrics ledger — the per-phase rows `manage-metrics` writes | `manage-metrics` | Per-phase `start_time` / `end_time` and token/duration figures for the same phases |

Because the two are written by different verbs at different moments and are never compared, **a plan can complete with the two disagreeing** and no gate notices. The disagreement a future implementor must detect is a phase the two accounts describe incompatibly — a phase the status record reports `done` that the ledger never closed (no `end_time`), a phase the ledger closed that the status record still reports `in_progress`, and a phase present in one account and absent from the other altogether. The `archive` post-condition above narrows one source of this drift but does not close it: it corrects the *status* side only, and the ledger is not consulted.

This reconciliation is **deliberately deferred**, and the reason is that the surface it must seam into does not exist yet. It needs two things:

- a **verdict vocabulary** — the agreed value set a reconciliation result would be reported over, so a disagreement is reportable as a typed outcome rather than as prose;
- a **statistics host** under `manage-metrics` — an existing aggregate-reporting surface for such a verdict to join.

Neither is available today: `manage-metrics` owns exactly two scripts, `manage-metrics.py` and `_ledger_reconciliation.py`, and neither mentions statistics in any case, so there is no statistics host under that skill to seam into.

⛔ **Do not build a private host here.** Standing up a reconciliation surface inside `manage-status` would put the cross-check on the side that owns only one of the two accounts, and would commit the project to a second, parallel statistics home that the eventual `manage-metrics` host would then have to absorb or contradict. The requirement is recorded so it is not lost, and it waits on the host rather than routing around it.

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

The `title-token set --state {state} [--owner {owner}]` verb writes the record with a fresh `set_at`; `title-token clear [--owner {owner}]` removes it. `set` validates `{state}` against the closed state set (`TITLE_TOKEN_STATES`) and `{owner}` against the owner vocabulary (`TITLE_TOKEN_OWNERS`), and both verbs emit a `[MANAGE-STATUS]` work-log line **only when they change the stored value** — `set` when the incoming `(owner, state)` differs from the live record (a record already aged past the staleness threshold reads as absent, so re-asserting it counts as a change), `clear` when it actually removed one. A re-assertion of the pair already stored still refreshes `set_at`; it just does not log. See [`../SKILL.md`](../SKILL.md) § "Title-token log emission is change-gated".

**Arbitration.** A `set` from any owner replaces the record wholesale — last writer wins, and the record always names its current owner. A `clear` is **owner-scoped**: only the recorded `owner` may clear its own token, and a foreign clear is a reported no-op (`cleared: false`, `reason: foreign_owner`). That asymmetry — open SET, scoped CLEAR — is what makes ownership meaningful: a lock glyph owned by `merge-lock` cannot be clobbered by an unrelated build bracket.

**Staleness is a read-side property.** A record whose `set_at` is older than `TITLE_TOKEN_STALE_AFTER_SECONDS` (3600 s) is stale and may be cleared or replaced by **any** writer. There is no phase-boundary sweep: `transition` and `set-phase` clear nothing, because a sweep only fires when a phase happens to change and would leave a stranded token alive indefinitely otherwise. Every reader resolves staleness through `_status_core.title_token_is_stale` / `read_title_token`, so a stranded token self-heals on the next read. `archive` remains the one owner-agnostic pop — an archived plan holds no live coordination state worth arbitrating over — and `create` never touches `title_token`.

**Concurrency.** Four independent writers (the `build-hook` `PreToolUse:Bash`/`PostToolUse:Bash` assist — a Claude-target render-hook bracket, see `platform-runtime/standards/terminal-title-architecture.md` § Channel Delivery Contract ruling (c) — `merge-lock`'s two lock surfaces, and `merge-lock`'s clear) mutate this one field from separate executor subprocesses. Both verbs therefore run their read-modify-write inside a single `rmw_json` critical section, and the clear takes its arbitration decision against the record read *inside* the guard — closing the check-then-act window a plain read-then-write would leave open.

Those four are the writers that *target* the field; they are not the only processes that can destroy a record. Every full-document `status.json` writer — `set-phase`, `transition`, `create`, and every other caller that commits a whole document assembled from a snapshot read taken before the commit — would restore that snapshot's stale `title_token` if it committed after a `set`. That second window is closed at the shared write seam rather than per verb: `_status_core.write_status` commits inside the **same** `rmw_json` guard (it resolves the same path, so it takes the same guard file) and carries over the `title_token` read *inside* the guard instead of the caller's snapshot value. `archive` is the sole opt-out (`preserve_title_token=False`), because its owner-agnostic pop is a deliberate discard rather than an instance of this race.

The three states split into two rendering classes, both owned by the composer:

| State | Set/cleared by | Composer rendering |
|-------|----------------|--------------------|
| `lock-waiting` | the merge-lock coordination machinery (`owner: merge-lock`) | ⏳ glyph, prepended to the body |
| `lock-owned` | the merge-lock coordination machinery (`owner: merge-lock`) | 🔒 glyph, prepended to the body |
| `build-busy` | the `build-hook` render assist bracketing a Bash build window (`owner: build-hook`) | 🔨 **icon-slot override** — forced into the icon slot, NOT a prepended glyph |

`build-busy` is the orchestration-busy state: the `PreToolUse:Bash` render assist (Claude target) sets it when a build-wrapper invocation enters, and the paired `PostToolUse:Bash` assist clears it when that Bash call exits, so the title surfaces the 🔨 build symbol for the whole blocking window. Both halves are machine-driven — no LLM turn owns the clear. `manage-status` only persists the record; the icon-slot-override rendering and the precedence against the lock glyphs and process icons live entirely in `manage-terminal-title`.

The record shape, the owner vocabulary, the arbitration rule, and the staleness threshold are specified once in `platform-runtime/standards/terminal-title-architecture.md` § Channel Delivery Contract ruling (c) and are not restated in normative form here.

For the full three-way split (state / composer / resolve+emit), the glyph and icon vocabulary, and the read-from-`status.json` (live + archived fallback) emit path, see `platform-runtime/standards/terminal-title-architecture.md`.

## Metadata

Arbitrary key-value pairs stored in `status.json` under the `metadata` object. Common fields:

| Field | Set By | Purpose |
|-------|--------|---------|
| `change_type` | phase-3-outline Step 4 (`manage-status:change-type-heuristic` script; LLM fallback via `effort` when the heuristic is ambiguous) | The PLAN-scoped classification — feature, bug_fix, tech_debt, etc. |
| `confidence` | phase-2-refine | Request clarity confidence (0-100) |

Metadata fields are promoted to top-level in `get-context` output for convenience.

`metadata.change_type` is the **PLAN-scoped** field — the plan's single settled classification, authoritative wherever the two scopes are compared. It is not the identically-named DELIVERABLE-scoped field a `solution_outline.md` deliverable carries in its own `**Metadata:**` block, of which there is one per deliverable. See [`manage-execution-manifest/standards/decision-rules.md` § change_type scope reconciliation](../../manage-execution-manifest/standards/decision-rules.md#change_type-scope-reconciliation) for how the composer reconciles the two scopes.

## Orchestrator Status (`kind=orchestrator`)

Orchestrator epics persist a second, deliberately lean status kind under the main-anchored orchestrator store — `.plan/local/orchestrator/{slug}/status.json`, resolved via `get_store_dir('orchestrator', slug)`. It is the machine authority for an epic's plan queue and resume state (see `persona-plan-orchestrator/standards/orchestration-model.md` for the consuming contract).

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
| `parallelization_scope` | `plan-orchestrator` `init.md` (operator `AskUserQuestion`, asked once per epic) | Maximum number of concurrently-launched plans the orchestrator may emit; positive integer, default `1` (strictly sequential) when unset |

The field is written through the existing `metadata --store orchestrator` verb, which accepts any `snake_case` key without a whitelist — so the knob requires no script or JSON-schema change. For the selection and disjointness rules that consume it, see `persona-plan-orchestrator/standards/orchestration-model.md` § Parallelization by Surface Disjointness.

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

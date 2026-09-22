# PLAN-47: Orchestrator Has No First-Class Config Block (dispatch effort + parallelization scope)

epic: truthful-signals
workstream: WS-01

> Staged plan spec. Operator-requested 2026-07-22: give the orchestrator a first-class
> `orchestrator` element in marshal.json (parallel to the `plan` block) holding its own knobs,
> instead of borrowing `plan.effort` plus unbounded prose discretion. **Widened 2026-07-22** to
> cover all **three** dispatch effort surfaces (analyze / decompose / reader) **plus the
> parallelization scope** — the cohesive home for orchestrator configuration. Grounded @ `dfc4ac15c`.
> (Emit autonomy is deliberately NOT here — it is a behavioral knob staged separately as PLAN-48.)

## Objective

The running orchestrator's dispatch tier ("Tier resolves to execution-context-level-3") and its
concurrency come from sources **no user can set as an orchestrator concern**:
1. **baseline effort** — `effort resolve-target --default` → `plan.effort`; the orchestrator
   silently reuses the *plan's* config, no orchestrator scope;
2. **the read-only-analysis uplift** ("MAY resolve a higher-effort level") — **prose discretion** in
   `orchestration-model.md:123`, bounded by nothing;
3. **the parallelization scope (N)** — PLAN-40 D3 makes the orchestrator *ask* for it every session
   via `AskUserQuestion`; it is not persisted, so the same answer is re-entered each session.

Give the orchestrator a first-class `orchestrator` block so a user can pin the effort of all three
dispatch surfaces (bounding the uplift deterministically) and set a standing parallelization scope.

## ⚠ Grounding — verified at `dfc4ac15c`

- **THREE dispatch effort surfaces, all read-only:**
  - `analyze.md:35` Step 2 ground-truth corroboration — `execution-context-{level}` (the verb's ONE
    context-dispatch sub-step);
  - `decompose.md:32-34` Step 2 on-disk corpus + candidate mapping + prior-art/collision search —
    `execution-context-{level}`;
  - `analyze.md:38` untrusted third-party text ingestion — **`execution-context-reader-{level}`** (a
    *different* vehicle, no Bash), gated through `validate_struct`. This is the third effort surface
    PLAN-47's first cut omitted.
  - `init.md:25` Step 2 is the deterministic `scaffold` script — NOT a dispatch; setup has no knob.
- **Baseline resolution today:** `_cmd_effort.py` resolves per-phase role-group `default` slot →
  `plan.effort`. Orchestrator dispatch enters via `effort resolve-target --default` = straight to
  `plan.effort`. No `orchestrator.*` scope exists.
- **Uplift is prose:** `orchestration-model.md:123` — no config ceiling, no per-verb control.
- **Parallelization scope:** PLAN-40 D3 (#981) added the `parallelization_scope` `AskUserQuestion`
  (init/orchestrate flow) — asked interactively, **not persisted**. D1 confirms the exact ask site.
- marshal.json holds a `plan` block; the new element is a **sibling `orchestrator` block**.

## Deliverables

### D1 — GATE: fix the schema shape and resolution precedence (mutates nothing)

Map the marshal.json schema + `_cmd_effort.py` resolution order + the `parallelization_scope` ask
site. Decide the `orchestrator` block shape. Proposed (D1 confirms):
- `orchestrator.effort` — a baseline level, per-surface overrides `orchestrator.effort.analyze`,
  `orchestrator.effort.decompose`, `orchestrator.effort.reader`, and an **uplift bound** (an explicit
  level or a `max` ceiling the discretion may not exceed);
- `orchestrator.parallelization_scope` — an integer default the ask falls back to (and may still be
  overridden interactively per session).
Fallback rule: **unset `orchestrator.*` MUST resolve exactly as today** (`plan.effort`; interactive
scope ask), so existing epics are unchanged. Name every artifact each choice edits.

### D2 — add the `orchestrator` block to schema + `manage-config`

Extend the marshal.json schema with the sibling `orchestrator` element and teach `manage-config` to
resolve and write it:
- effort: `effort resolve-target --role orchestrator.{analyze|decompose|reader}` returns the
  configured variant (`execution-context-{level}` / `execution-context-reader-{level}`);
  `effort set --scope orchestrator.analyze --level level-N` writes it (per-scope writer, preserves
  siblings). Precedence: `orchestrator.effort.{surface}` → `orchestrator.effort` (baseline) →
  `plan.effort`.
- scope: a reader for `orchestrator.parallelization_scope` the orchestrate/init flow consults, and a
  writer to set it.

### D3 — the dispatch sites + uplift + scope ask resolve from config

Rewrite `orchestration-model.md:123`'s effort-dimension prose so the uplift is **config-resolved,
not free discretion** (ceiling honored). `analyze.md` (both the context corroboration and the
reader ingestion) and `decompose.md` name their resolved roles. The `parallelization_scope`
`AskUserQuestion` **pre-fills from `orchestrator.parallelization_scope`** when set (still overridable).
Unset everywhere ⇒ today's behavior exactly.

### D4 — steward seeding + tests + doc

`/marshall-steward` seeds/validates the `orchestrator` block on init/upgrade (empty is legal). Tests:
effort precedence (`orchestrator.{surface}` → `orchestrator` → `plan`) for all three surfaces;
ceiling caps the uplift; unset = unchanged; `parallelization_scope` default pre-fills the ask and an
interactive answer still overrides. Document the block where `plan.effort` is documented.

## Expected surface

- marshal.json schema (`orchestrator` sibling block) + its schema doc
- `manage-config/scripts/_cmd_effort.py` (+ a scope reader/writer for `parallelization_scope`)
- `persona-marshall-orchestrator/standards/orchestration-model.md` (§ Dispatch Decision Rule effort
  dimension → config-resolved)
- `marshall-orchestrator/workflow/analyze.md` (context + reader roles), `decompose.md` (role),
  `init.md` / `orchestrate.md` (scope pre-fill)
- steward provisioning (seed/validate) + tests under `test/plan-marshall/manage-config/**`

**Disjointness:** manage-config + orchestration-model + orchestrator-workflow docs + marshal.json
schema. Distinct from PLAN-46 (manage-status title seam), PLAN-48 (emit-autonomy — behavioral, shares
the `orchestrator` block but a different key + a different verb surface; coordinate the block schema
at outline so both extend it cleanly), PLAN-42/45/41/43/44/27. Emittable now.

## Notes

- Theme fit: machinery-integrity half — turns implicit, prose-only orchestrator behavior into an
  explicit, user-set, deterministic config surface.
- Only three surfaces get effort knobs because only three dispatch (analyze context, decompose
  context, reader). Do NOT invent an `init` effort scope — scaffold is deterministic.
- **Coordinate the `orchestrator` block schema with PLAN-48 at outline** — both introduce keys under
  the same new block; D1 of whichever lands first defines the block, the other extends it.
- Builds on PLAN-31 (#968) Dispatch Rule + PLAN-40 (#981) D3 (parallelization scope) + D5 (effort
  dimension); makes both configurable rather than discretionary/ephemeral.

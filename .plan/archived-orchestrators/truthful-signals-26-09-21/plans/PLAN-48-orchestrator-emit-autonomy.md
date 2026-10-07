# PLAN-48: Orchestrator Emit Autonomy Is Absent (no auto-queue-fill knob)

epic: truthful-signals
workstream: WS-01

> Staged plan spec. Operator-requested 2026-07-22 as a **separate, guarded** plan (not folded into
> PLAN-47) because it is a *behavioral* knob that touches the emit≠running discipline — it needs its
> own design gate, not a quiet config fold-in. Grounded @ `dfc4ac15c`.

## Objective

Every orchestrator emit today is manual: on a landing that frees a slot, the orchestrator re-grounds
and emits the next `/plan-marshall` command, then **waits for the operator to say "started"** before
the next. Plans already have autonomy knobs — `finalize_without_asking`, `loop_back_without_asking`,
`auto_merge_after_ci` — but the orchestrator has **no analog**. Add an `orchestrator.auto_emit`
knob (default **off**) that lets the orchestrator auto-fill the queue toward the parallelization
scope on each landing, mirroring the plan-tier autonomy knobs — **without ever corrupting the
launched/running distinction**.

## ⚠ The invariant this must not break

`emit ≠ running` has been operator-corrected **4×** this session: a plan is `launched` on emit and
`running` only on operator-confirmed start. `auto_emit` automates the *emit*, never the *start*. The
danger is that auto-emitting reads as "now running" and the orchestrator over-counts live plans,
corrupting the very disjointness/scope math the scope is for. The whole plan is designed around
keeping that line intact.

## ⚠ Grounding — verified at `dfc4ac15c`

- Plan-tier autonomy knobs exist and are honored (`finalize_without_asking` /
  `loop_back_without_asking` / `auto_merge_after_ci`) — the precedent this mirrors at the
  orchestrator tier. D1 re-confirms their config home + semantics.
- `orchestrate.md` / `analyze.md` landing flow currently ends with a *proactive emit* (PLAN-40 D3)
  gated by surface-disjointness + prep-readiness, but the operator drives the cadence; nothing
  auto-fires.
- No `orchestrator.*` config scope exists yet — this knob lives in the **same `orchestrator` block
  PLAN-47 introduces** (coordinate schema at outline).

## Deliverables

### D1 — GATE: define exactly what auto_emit does and does NOT automate (mutates nothing)

Pin the contract against the plan-tier autonomy precedent:
- **Automates:** on a landing that frees a slot, re-ground the next disjoint staged plan(s) and emit
  toward `parallelization_scope`, marking each **`launched`**.
- **Never automates:** (a) the `launched → running` transition — that stays operator-confirmed, the
  emit≠running invariant is absolute; (b) emitting a plan that collides, is blocked, or is
  unprepared — the "only if sensible" guard is unchanged, a shortfall is logged not filled with a
  bad emit; (c) a genuine-fork plan whose emit needs an operator decision. Confirm the landing flow's
  exact emit seam in `orchestrate.md`/`analyze.md`.

### D2 — add `orchestrator.auto_emit` and wire the landing flow

Add `orchestrator.auto_emit` (default `false`) to the `orchestrator` block (coordinate with PLAN-47's
D1 — whichever lands first defines the block, this extends it). When `true`, the
`orchestrate.md`/`analyze.md` post-landing emit fires automatically under the existing disjointness +
prep-readiness + "only if sensible" guards, marking `launched`. When `false` (default), behavior is
exactly today's stage-and-wait.

### D3 — the invariant guard is enforced and tested

`auto_emit` MUST NOT set `running`. A regression test: with `auto_emit=true`, a landing fills toward
scope with **`launched`** status only (never `running`); a landing whose only candidates collide or
are blocked emits **nothing** and logs the shortfall (never a bad emit); `auto_emit=false` reproduces
today's manual cadence. Pins the emit≠running invariant against the new autonomy.

### D4 — steward seeding + doc

`/marshall-steward` seeds `orchestrator.auto_emit=false` (safe default). Document it beside the
plan-tier autonomy knobs so the orchestrator-tier analog is discoverable, and cross-reference the
emit≠running rule as the constraint the knob operates within.

## Expected surface

- marshal.json schema (`orchestrator.auto_emit` — shares the block PLAN-47 defines)
- `marshall-orchestrator/workflow/orchestrate.md` + `analyze.md` (post-landing emit reads the knob)
- `persona-marshall-orchestrator/standards/orchestration-model.md` (record the knob + the invariant
  it must not break)
- config read + steward seeding + tests under `test/plan-marshall/**`

**Disjointness:** orchestrator landing-flow docs + the shared `orchestrator` config block. Overlaps
PLAN-47 **only** on the block schema — coordinate at outline (whichever lands first defines the
block). Distinct verb surface (autonomy/cadence vs effort/scope). Disjoint from PLAN-46/42/45/41/43/
44/27. Emittable now, but **sequence after or with PLAN-47** so the block schema is defined once.

## Notes

- Theme fit: machinery-integrity — makes an operator-manual cadence an explicit, opt-in config,
  mirroring the plan-tier autonomy knobs, while structurally protecting the emit≠running invariant.
- Default MUST be off: the safe posture is manual emit; autonomy is opt-in.
- Builds on PLAN-40 (#981) D3 (the proactive queue-fill emit this would automate) + the
  `feedback_emit_not_running_count` discipline (the invariant it must preserve).

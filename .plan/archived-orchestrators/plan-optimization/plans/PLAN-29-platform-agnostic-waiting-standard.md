# PLAN-29: platform-agnostic-waiting-standard

epic: plan-optimization
workstream: WS-10

> Staged plan spec — **DESIGN-FIRST** (same posture as PLAN-25). Surfaced 2026-07-21 from an operator
> research thread on standardizing waiting/polling cycles (CI, build-server) on a background-watch
> primitive. **Hard constraint from the operator: the standard must NOT be Claude-specific** — it must be
> expressed through the existing `marketplace/targets/` + `platform-runtime` multi-target machinery, since
> `Monitor` (the Claude realization) has no guaranteed analog on other targets. Machinery inventory below
> is orchestrator-researched against source (2026-07-21); re-ground file:line at outline.

## Objective

Turn "wait for an external event" (CI run, merge-queue merge, build-server long-poll overflow) into a
**platform-agnostic standard** with a single semantic contract and per-target realizations — Claude Code
via the `Monitor` background-watch tool, other targets via their own primitive or a documented fallback.
Decide, first, WHERE the abstraction lives (a runtime op vs a target-scoped skill), then express the
standard so no general skill body names `Monitor` or any Claude-only construct.

## Design inputs (orchestrator-researched, reuse — do NOT reinvent)

- **Build-time seam:** `marketplace/targets/` — `TargetBase` ABC (`base.py`), `TARGET_REGISTRY`
  (`__init__.py`), per-target `mapping.json` (`opencode/mapping.json` `tool_permissions`), the shared
  `body_transform_engine.py`, and the **variant-emitter precedent** (`claude/variant_emitter.py`) for
  "one source construct → capability-gated per-target output".
- **Runtime seam:** `platform-runtime` skill — the `Runtime` ABC (`runtime_base.py`, ~22 goal-based ops),
  registry dispatch keyed on `marshal.json runtime.target`, and the **no-op contract**
  (`standards/no-op-policy.md`): a target lacking a mechanism returns `status: no-op` + `reason` +
  `alternative`, and the caller MUST continue. `_UNMAPPED_TOOLS` (`claude_runtime.py`) is the existing
  "capability unavailable on a target" representation.
- **The unbuilt 4th home:** the `targets:` frontmatter filter — specified in
  `doc/refactor/07-target-extensibility.md:116-125` + `principles.md:129-139`, **zero implementation
  today**. `targets: [claude]` ⇒ component emitted only for listed targets, simply absent elsewhere.
- **Governing principles:** `doc/refactor/principles.md` §1 (semantic-in / normalized-out — the boundary
  must NOT surface `Monitor`'s event-stream shape), §5 (No Universal Syntax — platform behavior goes in a
  script/runtime-op/no-op, never in body text), §6 (the *differs-per-target* vs *exists-only-on-some* fork
  + the admission test at `07:124-125`).
- **Carried-forward analysis (this session, keep):** waiting is owned by the **main loop**, never a
  dispatched leaf (a leaf can't be resumed after a reap; exact subagent-lifetime cap is unverified and the
  design must not depend on it); the **checkpoint-and-re-dispatch** fallback is the pattern that is correct
  even under worst-case reaping; and **"silence ≠ success"** — a waiter's terminal-state coverage must
  include failure signatures, not just the happy path (mirrors PLAN-24's truthful-status theme).

## Deliverables

### D1 — ADR: resolve the §6 fork for the waiting capability (load-bearing design)

Decide and record, as an ADR, whether "wait for external event" is a **differs-per-target** capability
(→ a new goal-based `Runtime` op, e.g. `wait-for`/`watch`, with a `no-op`+`alternative` on targets lacking
a background-watch analog) or an **exists-only-on-some-targets** capability (→ a `targets:`-scoped
skill/knowledge body, which requires building the unbuilt `targets:` filter), or a **hybrid** (the waiting
*policy* is a skill that renders on all targets; the waiting *primitive* is a `Runtime` op that no-ops
where absent). Apply the admission test (`07:124-125`) — the 4th home is only for a whole workflow
genuinely N/A elsewhere, never to dodge normalizing a shared capability. **Acceptance:** an ADR naming the
chosen route with rationale grounded in `principles.md` §1/§5/§6, and an explicit statement of what each
target (claude, opencode) does for the capability. This deliverable gates D3/D4.

### D2 — classify `Monitor` in the existing capability tables (concrete, separable, correct regardless of D1)

`Monitor` is currently unclassified: absent from `opencode/mapping.json::tool_permissions` (an agent
declaring it would fail the OpenCode build, fail-closed) and from runtime `_UNMAPPED_TOOLS`, and it is
named in `persona-plan-marshall-agent` body prose (`08` §C1) untransformed. Place it in the sanctioned
homes: a `tool_permissions` disposition (map or declare target-absent) and/or `_UNMAPPED_TOOLS`-style
membership, and route the body-prose reference through the build-target tool-name rewrite data rather than
leaving it as a hardcoded Claude token. **This is the one immediately-buildable piece** — it is correct
whatever D1 decides and it removes a latent OpenCode-build hazard. **Acceptance:** the OpenCode build has a
defined, non-crashing disposition for `Monitor`; no general skill body carries an untransformed `Monitor`
literal that the target machinery cannot rewrite; regression covering the build disposition.

### D3 — author the waiting standard, platform-agnostically (semantic-in / normalized-out)

Author the standard as a skill-shaped knowledge body stating: WHEN to wait; **the main loop owns waiting,
leaves never do** (carry the reaping analysis); the **failure-signature coverage rule** (silence ≠
success); the tiered realization — background-watch primitive where present (Claude → `Monitor`; single
completion → `run_in_background`+`until`), else the **checkpoint-and-re-dispatch** fallback; and the
bounded-poll relationship to the build-server client. Express it in intent terms ("wait until condition C
holds, or its terminal-failure states"), **never** in `Monitor`'s event-stream vocabulary (principles §1).
Home is chosen by D1 (a general skill, or a `targets:`-scoped one). **Fold the `CI-wait-budget-600s`
watch** — the finalize CI-wait is the standard's first concrete consumer. **Acceptance:** a target-neutral
standard doc a reader on ANY target can follow; the Claude realization maps cleanly to `Monitor`; a
target without the primitive has a stated, non-blocking path (no-op+alternative or checkpoint-re-dispatch).

### D4 — specify the delivery mechanism + decide the build split (design + epic-decision)

Specify the mechanism D1 selected — the `Runtime` `wait-for` op (ABC + claude impl over `Monitor` +
opencode `no-op`) **or** the `targets:` frontmatter filter (generator handling + emission gating, per
`07:116-125`) — and **decide whether that mechanism is built within this plan or split to a follow-up.**
The `targets:` filter is a GENERAL mechanism whose first consumer happens to be this standard; if D1 picks
it, building it is presumptively its own plan (record the split as an epic decision), and PLAN-29 ships
D1–D3 + the spec. The `Runtime` op is narrower and MAY ship here. **Acceptance:** a written mechanism
spec precise enough to implement, plus a recorded build-here-vs-split decision with rationale.

## Out of scope / do NOT expand
- Do NOT build a general `targets:` frontmatter filter inline without D4's split decision — it is likely
  its own plan (general mechanism, multiple future consumers).
- Do NOT convert existing waiting call sites (finalize CI-wait, build-server client) in this plan — this
  establishes the standard + mechanism; migration of consumers is follow-up work.
- Do NOT surface `Monitor`'s event-stream shape across the platform boundary (principles §1 violation).
- The build-server daemon / long-poll internals — that is the plan-server epic; this plan only references
  the bounded-poll-overflow case as a consumer of the waiting standard.

## Absorbs
- Operator research thread "standardize waiting cycles on a background-watch primitive, platform-agnostically"
  (2026-07-21) → D1–D4.
- The `CI-wait-budget-600s` epic watch (fixed-budget finalize CI-wait) → D3 (first consumer).

## Expected Surface
- new ADR under `doc/adr/` (D1)
- `marketplace/targets/opencode/mapping.json` (`tool_permissions`) + `claude_runtime.py` `_UNMAPPED_TOOLS`
  + `persona-plan-marshall-agent` body-prose `Monitor` coupling (`08` §C1) (D2)
- the waiting-standard doc — home TBD by D1 (a `standards/*.md`, possibly a new skill) (D3)
- `platform-runtime` `Runtime` ABC + claude/opencode impls (if Runtime-op route) OR
  `marketplace/targets/` generator `targets:`-filter handling spec (if 4th-home route) (D4)
- `doc/refactor/07-target-extensibility.md` / `principles.md` reconciliation of the chosen route
- tests: opencode-build-has-Monitor-disposition (D2); target-neutral-standard-followable; chosen-mechanism spec

## Dependencies and Sequencing
- Depends on: none. Design-first — D1 must land before D3/D4 are actionable (intra-plan ordering).
- **Potential adjacency with PLAN-26** on `platform-runtime` IF D1 picks the `Runtime`-op route (PLAN-26
  touches the terminal-title/platform surface). Different region expected; confirm at outline and sequence
  if the Runtime route is chosen. Surface-disjoint from the launched trio (20/21/22) and from PLAN-23/24/27
  (maven) and PLAN-28 (housekeeping/lint).
- Meta-project (marketplace targets + platform-runtime + refactor docs).

## Size / split guard
4 deliverables, design-heavy with ONE concrete build (D2). Under the ~6 presumption. The elastic risk is
D4's mechanism build — explicitly guarded: if D1 selects the `targets:` filter, D4 splits the generator
build to a follow-up plan (recorded as an epic decision) and PLAN-29 ships D1–D3 + the spec, keeping this
plan design-first as intended.

## Hand-Off Command
```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-29-platform-agnostic-waiting-standard.md"
```

## Status Trail
- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-29.md is recorded}

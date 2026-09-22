# PLAN-LR-07: The `lessons` verb always resolves to `lessons-routing`, never a fresh dated epic

epic: lessons-routing
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Objective

**Operator ruling 2026-09-22** (recorded in this epic's own `epic.md`, Standing Rule section and
resume-anchor R15): `lessons-routing` is ALWAYS the orchestrator used for a lessons-corpus sweep. No
new `lessons-handling-{YY-MM-DD}-{NN}` epic is ever opened again. That ruling is currently enforced by
nothing but a ledger note a session might not read — the `lessons` verb's own workflow doc still
literally instructs deriving a fresh dated slug and opening a new epic every time it runs. This plan
makes the ruling structural: it edits the skill source so the verb itself resolves to `lessons-routing`,
and — while touching that code path — fixes a second, independently-discovered defect in the same
doc: the current text tells a sweep to `status.json`-stage its clusters as if they were the sweep
epic's own plans, contradicting the "must not provide plans, act as a distribution point" discipline
the mode exists to implement. The 2026-09-22 sweep worked around this by hand (routing via `inbox
write` instead of staging); this plan makes that the DOCUMENTED behavior instead of an improvisation.

⛔ **This is a shared marketplace skill.** Every project running plan-marshall's `plan-orchestrator`
skill gets this change, not just this repository. The fixed target epic name is `lessons-routing` —
verified as this project's own convention (see Claim Labels); a project with a different epic name for
this purpose would need its own equivalent, which is out of this plan's scope to generalize.

## Deliverables

Five deliverables.

**D1 — rewrite the mode contract's "Dated-slug epic" rule.** In
`persona-plan-orchestrator/standards/orchestration-model.md` § "Lessons-Handling Mode Contract",
replace the bullet describing dated-slug derivation with a "Fixed-epic sweep" rule: every `lessons`
invocation operates on the epic named `lessons-routing` (scaffolded if absent, idempotent otherwise) —
never derives or opens a `lessons-handling-{YY-MM-DD}-{NN}` epic. State the three prior dated epics
(`lessons-handling-26-08-08-01`, `26-08-26-01`, and the short-lived `26-09-22-01`) as closed history
under the retired model, explicitly not a template to reuse.

**D2 — rewrite `workflow/lessons-handling.md` Step 1.** Drop the dated-slug derivation entirely. The
target slug is the fixed constant `lessons-routing`. Scaffold / create `status.json` / push the
terminal title only when absent — each call is already naturally idempotent
(`scaffold`'s `already_existed` field, `manage-status create`'s presumed idempotence on an existing
document — confirm at outline) so this is a straightforward substitution, not a new idempotence
mechanism to design.

**D3 — rewrite Steps 3–4 to route instead of stage.** ⛔ **This is the load-bearing fix.** Current
Step 4 instructs writing the clustered queue into `status.json`'s `plans` list as `status: staged`
rows — i.e., the sweep epic accumulating its OWN plans from swept content, which directly contradicts
the mode's own "must not provide plans, act as a distribution point of the sibling orchestrators" rule
and the epic's Inbound Routing / Standing Rule sections. Replace it with: for each disposed cluster,
resolve the owning sibling epic (by subject match against that epic's own stated scope — no new
resolver invented here; this is the same judgment call the 2026-09-22 sweep made by hand) and route it
via `orchestrator inbox write --sender-type orchestrator --sender-id lessons-routing --kind
candidate-lesson`. Preserve the ONE narrow exception already established by precedent
(`PLAN-LH2-18` → `PLAN-LR-06`): a cluster that is a tooling defect in the routing/versioning mechanism
itself, not lesson content, MAY be staged as a new `PLAN-LR-NN` in `lessons-routing` — but only after
checking (a) it isn't already shipped elsewhere and (b) it isn't actually `truthful-signals`' subject
per the Inbound Routing rule's "confident signal hides a caveat" carve-out. `PLAN-LR-06` itself was
retired the day after being staged for failing exactly that second check — cite it as the worked
counter-example, not a footnote.

**D4 — update Step 6/7 and the Output contract.** A sweep's disposition record is logged as a dated
subsection in `lessons-routing`'s own `## Lesson Sweeps` section (the pattern the 2026-09-22 sweep
established by hand in this epic's `epic.md`), never a separate epic's ledger. The `slug` field in the
verb's TOON output always reads `lessons-routing`.

**D5 — sweep for stale cross-references, derived not eyeballed.** Grep the `plan-orchestrator` and
`persona-plan-orchestrator` skill trees for `dated-slug`, `dated epic`, and `lessons-handling-{` and
fix every hit the population enumerates (confirmed at staging: exactly three — `plan-orchestrator/
SKILL.md:28` and `:74`, and the `orchestration-model.md:372` bullet D1 already rewrites) — publish the
population the sweep actually found, per this epic's own `2026-09-21-10-002`-class lesson
("hand-maintained doc enumeration of a code-declared set drifts") that was JUST routed to
`truthful-signals` from this very corpus: point at the grep, don't restate a count that can go stale.

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md`
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/lessons-handling.md`
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md`

## Dependencies and Sequencing

- Depends on: none. Disjoint surface from PLAN-LR-01/02/03/04/05 (those touch `manage-lessons/**` and
  `tools-integration-ci/**` only) — may run in any order relative to them, though `N=1` still applies.
- Overlaps with (per `corpus cross-check`, 2026-09-22, re-derive at emit time): live plans in
  `orchestrator-refactor` (PLAN-01, PLAN-02 `ledger-decomposition-and-row-vocabulary`, PLAN-05
  `identifier-rename-execution`, PLAN-07 `orchestrator-script-decomposition`) and `truthful-signals`
  (PLAN-TRUTH-146, -151, -155) also declare `plan-orchestrator/SKILL.md` and/or
  `orchestration-model.md` in their own Expected Surface — same shared skill files, different edits.
  ⚠ **`orchestrator-refactor`'s own aspect 4 ("survey every sibling epic for orchestrator-tooling work
  scattered elsewhere and fold it in") could plausibly claim this plan** — it was kept here because the
  content is `lessons-routing`'s own operating-model decision (which epic the `lessons` verb targets),
  not generic orchestrator substrate work; flag for `orchestrator-refactor` if it disagrees.
  **Serialize with whichever of the above lands first**; do not attempt a merged/redesigned edit.
- Adjacent to: the `plan-orchestrator` skill's other verb workflows (`decompose`, `analyze`, etc.) —
  untouched; this plan's surface is narrowly the `lessons` verb's own three files.

## Claim Labels

- OBSERVED: `orchestration-model.md:372` states "Each run opens its own epic with slug
  `lessons-handling-{YY-MM-DD}-{NN}}`... Every invocation is a fresh, distinct epic" — read at
  `persona-plan-orchestrator/standards/orchestration-model.md` § "Lessons-Handling Mode Contract".
- OBSERVED: `workflow/lessons-handling.md` Step 1 derives `{slug}` as
  `lessons-handling-{YY-MM-DD}-{NN}` and scaffolds a fresh epic tree from it — read at
  `plan-orchestrator/workflow/lessons-handling.md` § "Step 1: Derive the dated slug and scaffold the
  epic".
- OBSERVED: `workflow/lessons-handling.md` Step 4 instructs writing the clustered queue into the SWEEP
  EPIC's own `status.json` `plans` list at `status: staged`, with no routing-to-sibling step anywhere
  in the document — read at `plan-orchestrator/workflow/lessons-handling.md` § "Step 4: Persist the
  queue and regenerate the derivable blocks". This contradicts the mode's own quoted rule ("the
  orchestrator itself must not provide plans but act as a distribution point of the sibling
  orchestrators") recorded in `lessons-routing/epic.md` § "Standing Rule: Content Sweeps vs Router
  Infra".
- OBSERVED: exactly three files reference the dated-slug pattern in prose — `plan-orchestrator/
  SKILL.md:28`, `plan-orchestrator/SKILL.md:74`, and `orchestration-model.md:372` — read via
  `grep -rn "dated-slug\|dated epic\|lessons-handling-{"` over
  `marketplace/bundles/plan-marshall/skills/plan-orchestrator/` and
  `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/` (2026-09-22, this plan's own
  staging). D5's sweep is this same grep re-run at outline, not a fresh population.
- OBSERVED: three lessons-handling epics exist under `.plan/archived-orchestrators/` /
  `.plan/orchestrator/` history — `lessons-handling-26-08-08-01`, `lessons-handling-26-08-26-01` (both
  archived), and `lessons-handling-26-09-22-01` (opened and closed same-day, its record inlined into
  `lessons-routing/epic.md` § "Lesson Sweeps" and its tree removed) — read via `corpus epics`
  (2026-09-22).
- HYPOTHESIS: `manage-status create` and `orchestrator scaffold` are each idempotent against an
  already-existing target (return success / `already_existed: true` rather than erroring) — confirm
  at outline against `orchestrator.py`'s `cmd_scaffold` and `manage-status`'s `cmd_create` (this
  plan's D2 assumes idempotence rather than building new guard logic; if either is NOT idempotent,
  D2's "scaffold if absent" framing needs an explicit existence check instead).
- Verify-first clause: D3's routing-vs-staging rewrite must be checked against this epic's own
  `## Lesson Sweeps § 2026-09-22` entry (already inlined in `epic.md`) as the worked example — the
  rewritten Step 3/4 text should describe exactly what that entry records having done, not a new or
  different procedure invented at outline.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/lessons-routing/plans/PLAN-LR-07-the-lessons-verb-always-resolves-to-lessons-routing.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message.

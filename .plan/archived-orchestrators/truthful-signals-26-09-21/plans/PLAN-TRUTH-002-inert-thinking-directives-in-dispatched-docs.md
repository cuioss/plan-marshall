# PLAN-TRUTH-002: Inert in-prose thinking directives in dispatched workflow docs

> Renamed from **PLAN-97** on 2026-07-30 (see `plan-id-rename-map.md`).

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-NN-{plan_slug}.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Dispatched workflow docs contain prose asking the model to adopt a thinking level ("use ultrathink",
"use careful step-by-step reasoning"). Model and effort are **pinned by the dispatched variant
filename**, so this prose is inert or in tension with the pin, and it diverges from a contract stated
two files away. Remove the confirmed instances, sweep the corpus population-derived, and add an
edit-time guard against reintroduction.

Source: inbox message `operator-adhoc-001.md` (out-of-plan finding, main checkout).

## Mechanism — OBSERVED, orchestrator-verified first-party at HEAD

- `agents/execution-context.md:30` states outright: **"Model and effort are NOT prompt-body fields.
  They are pinned by the variant filename (`execution-context-{level}.md`) that the caller dispatched
  against"**, per `extension-api/standards/ext-point-dynamic-level-executor` (ADR-003). ✅ Verified
  verbatim at that line.
- Therefore any prose INSIDE a dispatched workflow doc asking the model to adopt a reasoning level is
  inert or in tension with the pin.

**Archetype: vacuous guard** (a predicate that can never fire) — **this is n=5**. Secondary archetype:
doc-contract-divergence. Both are tracked epic counters; update them at landing.

## Confirmed instances — OBSERVED, orchestrator-verified

1. `plan-marshall/skills/plan-marshall/workflow/research-best-practices.md` — ✅ **all three verified
   at the exact stated lines:**
   - `:9` — "Use **ultrathink mode** for deep analysis and synthesis"
   - `:46` — "consider using ultrathink to formulate the most effective search query strategy"
   - `:112` — "use ultrathink at the start of this step"

   Reachable ONLY via dispatch to `execution-context-reader-{level}`, whose effort is already pinned
   by the variant.
2. `pm-documents/skills/ref-documentation/workflow/content-review.md` — message-reported at `:7`
   (descriptive restatement) and `:177` ("**CRITICAL:** Use careful step-by-step reasoning for
   comprehensive tone assessment"). **HYPOTHESIS — not independently verified by the orchestrator;
   confirm at outline.**

   The message argues `:177` is *worse than inert*: a chain-of-thought scaffold on a
   checklist-following review task, the case where CoT prompting pulls attention off the stated
   constraints. That reasoning is plausible but is the message's own; treat the *harm* claim as a
   HYPOTHESIS even once the string is confirmed present.

## Deliverables

1. **D1 — fix the confirmed instances.** **MUST NOT be gated on D3.** Remove the reasoning-level and
   process-narration prose only; **preserve surrounding criteria prose verbatim**. Modules:
   `plan-marshall`, `pm-documents`.
2. **D2 — corpus-wide sweep for the same defect class, then fix what it finds.** **This is a
   DISCOVERY deliverable — its output size is unknown at spec time.**

   ⛔ **The originating grep was a SAMPLE, not an enumeration.** It covered `ultrathink`,
   "think step by step", careful/deeply + reason|think|consider|analyze, "take your time",
   "before answering". **Do not treat that list as the population.**

   The candidate file set MUST be **population-derived from the dispatch roster** — every markdown
   reachable as an `execution-context*` `workflow:` target; see `test/_shared/_dispatch_roster.py`.
   Enumerate the roster, then scan it. **Report roster size and hit count separately: a count of
   files examined is a VOLUME, not a coverage number.**
3. **D3 — a plugin-doctor rule preventing reintroduction.** Population-derived detector over the same
   roster, **not a hard-coded path list**.

   ⛔ **THE FALSE-POSITIVE BOUNDARY IS THE HARD PART.** 24 of 25 corpus hits for "step-by-step" are
   legitimate procedural prose ("Step-by-step workflow for creating a solution outline"). **Descriptive
   prose about workflow SEQUENCING is not a violation.** Only directives asking the model to adopt a
   reasoning level or narrate a reasoning process are. **Needs test cases in both directions — a
   detector that fires on procedural prose is a regression, not a win.**

Three deliverables, well under the split guard.

## Out of scope — deliberate, do not expand into it

Any sweep of CRITICAL / NEVER / MUST NOT / MANDATORY emphasis markers. Corpus counts: `MUST NOT` 220,
`CRITICAL` 170, `NEVER` 164, `MANDATORY` 47, `ALWAYS` 43, `FORBIDDEN` 20. The distribution is flat
(max 18 in one file, and that file is `plugin-architecture/references/execution-directive.md` — a
document *about* directives). These guard true invariants: `.plan/` script-only access,
one-command-per-Bash, executor notation, TOON schema shape. **Leave them alone.**

## Why not `recipe-surgical-fix`

Checked against its Step 1 fit gate: it aborts. `research-best-practices.md` → `plan-marshall`,
`content-review.md` → `pm-documents`, plugin-doctor rule + tests → `pm-plugin-development`. Three
modules fails `cross_module`; D2's unbounded discovery pass fails `too_broad`; findings-only also
fails, since the two files are already in different modules. **Do not re-litigate this at outline.**

## Claim Labels

- OBSERVED (orchestrator-verified first-party 2026-07-28): the pin contract at
  `agents/execution-context.md:30`, verbatim.
- OBSERVED (orchestrator-verified): all three `ultrathink` instances in `research-best-practices.md`
  at `:9`, `:46`, `:112`.
- HYPOTHESIS: the two `content-review.md` instances at `:7` and `:177` — confirm/refute at that file
  § those lines, **by symbol/string not line number** (verify-at-outline).
- HYPOTHESIS (message-supplied reasoning, not verified): that a CoT scaffold on a checklist task
  actively degrades constraint-following. Plausible and worth acting on, but it is the message's
  argument — do not serialize it downstream as established.
- HYPOTHESIS (message-supplied derived counts, NOT re-derived): "24 of 25 corpus hits for
  step-by-step are legitimate", and the six emphasis-marker corpus counts. **Derived counts from a
  message are leads** — re-derive any figure D3's detector is tuned against (verify-at-outline).
- Verify-first clause: D2 must confirm `test/_shared/_dispatch_roster.py` still exposes the roster in
  the shape D2 needs before building on it. If the roster has moved or changed shape, re-scope D2's
  enumeration rather than hand-rolling a second roster.

## Expected Surface

- OBSERVED: `plan-marshall/skills/plan-marshall/workflow/research-best-practices.md` — `:9`, `:46`, `:112`.
- HYPOTHESIS: `pm-documents/skills/ref-documentation/workflow/content-review.md` — `:7`, `:177`
  (verify-at-outline).
- HYPOTHESIS: additional roster files found by D2 — enumerated at outline, **not guessed here**.
- HYPOTHESIS: `pm-plugin-development` plugin-doctor rule home + tests (D3).
- OBSERVED: `test/_shared/_dispatch_roster.py` — the population source (read-only unless D2 extends it).

**Disjointness:** `plan-marshall` (one workflow doc) + `pm-documents` + `pm-plugin-development`, plus
whatever D2's sweep surfaces — **the sweep makes the surface open-ended, so treat this plan as
exclusive against anything touching dispatched workflow docs.**
⚠ Plausibly overlaps **PLAN-TRUTH-004** and **PLAN-81** (plugin-doctor / population-derived detector work) —
check before pairing.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-TRUTH-004, PLAN-81 (detector surface — verify before pairing). D2's open-ended sweep
  may collide with any in-flight plan editing a dispatched workflow doc.
- Adjacent to: **PLAN-TRUTH-003** (the sibling message from the same drain) — both want a population-derived
  plugin-doctor detector over a roster. **Co-design the detector pattern; do not build two.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-002-inert-thinking-directives-in-dispatched-docs.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

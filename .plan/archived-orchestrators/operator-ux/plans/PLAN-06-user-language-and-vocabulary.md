# PLAN-06: Honour the user's language, and speak the user's vocabulary

epic: operator-ux
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-06-user-language-and-vocabulary.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Two rules, one surface. **Language**: plan-marshall must answer in the language the user is
writing in and keep doing so across phase boundaries, sub-agent returns and prompts — a German
user currently gets German inconsistently, because nothing in the marketplace states the
obligation at all. **Vocabulary**: user-facing text must use the user's nouns, not the
system's — "ledger", "epic", "workstream", "q-gate", "disjointness", "multiSelect", "lane",
"footprint" are internal concepts, and a user who never learned them cannot act on a sentence
built from them. Both rules land in a NEW dedicated standards file,
`persona-plan-marshall-agent/standards/user-communication.md`, loaded UNCONDITIONALLY beside
`agent-behavior-rules.md` — isolated as one cohesive document, but binding everywhere because
the persona is loaded by every persona and every dispatched agent.

## Deliverables

1. A NEW `standards/user-communication.md` in `persona-plan-marshall-agent`, and a new
   unconditional load step for it in that skill's `SKILL.md` Workflow — placed with Step 1
   (`agent-behavior-rules.md`), NOT among the "As Needed" steps. A rule that loads only when
   remembered cannot deliver "throughout", which is the whole complaint.
2. The user-language rule in that file: the obligation, its scope (all user-facing output —
   prompts, summaries, reports, error text), and its explicit non-scope (code, identifiers,
   file content, commit messages, and the marketplace's own developer documentation, which
   stay in their existing language).
3. A `marshal.json` user-language setting with an `auto` default meaning "follow the language
   the user writes in", plus its `manage-config` read/write surface — so a user can pin a
   language rather than relying on inference alone.
4. The user-vocabulary rule in the same file, with the displacement glossary: each
   internal term paired with what to say instead at a user-facing surface. The glossary is the
   deliverable that makes the rule applicable rather than aspirational.
5. A stated boundary between *renaming a concept for the user* and *renaming it in the code*.
   This plan changes what the user is TOLD, never the config keys, status vocabulary, or
   directory names — those are contracts with their own consumers.
6. A pointer from `agent-behavior-rules.md` to the new file, so a reader of the general rules
   finds the communication rules rather than concluding none exist. The rules themselves are
   NOT duplicated there — one home, one authority.

## Claim Labels

- OBSERVED: No user-language, locale, or output-language concept exists anywhere in the
  marketplace. Asserted as an ABSENCE and verified as one — a marketplace-wide search over
  `*.md` and `*.py` for `user_language`, `output_language`, `locale`, `experience_level`,
  `verbosity` and equivalent phrasings returns only unrelated `java.util.Locale` examples in
  `pm-dev-java` standards. This plan defines the concept; it does not extend one.
- OBSERVED: `persona-plan-marshall-agent` is the unconditional foundational base every persona
  inherits and is deliberately not listed in any `composes:` field — read at
  `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/SKILL.md` § Composition.
  This is why the two rules bind everywhere when placed there.
- OBSERVED: The internal vocabulary reaches users today. The operator's pasted prompt says
  *"Per Step 7 this requires an operator multiSelect"*; the orchestrator's own verbs speak of
  ledgers, epics and disjointness to the same audience. Source: operator paste plus this
  epic's own surface.
- OBSERVED: `standards/user-communication.md` does not exist at HEAD — the standards
  directory holds exactly `agent-behavior-rules.md`, `argument-naming.md`,
  `coverage-gathering-contract.md`, `thoroughness.md` and `tool-usage-patterns.md`. This plan
  CREATES it. Asserted as an absence and verified by listing the directory.
- OBSERVED: `persona-plan-marshall-agent/SKILL.md` already uses progressive disclosure — Step 1
  loads `agent-behavior-rules.md` unconditionally, Steps 2-5 load their standards "As Needed"
  — read at
  `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/SKILL.md` § Workflow.
  The new file must join the UNCONDITIONAL tier; placing it in the "As Needed" tier would
  reproduce the opt-in failure a separate skill was rejected for.
- HYPOTHESIS: A `marshal.json` top-level scalar is the right home for the language setting,
  rather than a `plan.*` phase knob — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md` § the
  top-level block inventory (verify-at-outline). The knob governs every phase, so a
  phase-local home would be wrong by construction.
- Verify-first clause: settle at outline whether sub-agent returns are user-facing for the
  purpose of the language rule. A `display_detail` the orchestrator surfaces verbatim IS user
  facing; a TOON field it consumes and re-renders is not. Getting this wrong either leaves
  English fragments in a German session or forces translation of machine fields.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/user-communication.md`
  — CREATED by this plan; verified absent at HEAD (the standards directory holds five other files)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/SKILL.md`
  — the new unconditional load step
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md`
  — pointer to the new file only; no rule text lands here
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md`
- OBSERVED: `test/plan-marshall/manage-config/`

## Dependencies and Sequencing

- Depends on: none. Independent by design — this is the intended second-slot partner for
  WS-01's plans.
- Overlaps with: PLAN-07 (`standards/user-communication.md` — hard sequence, PLAN-06 first:
  PLAN-06 CREATES the file PLAN-07 extends, so the order is structural, not stylistic);
  PLAN-01/02/03/04 (`manage-config/SKILL.md`, `_config_defaults.py`).
- Adjacent to: the prompt-structure standard (PLAN-05), which CITES these rules from a
  different bundle and does not edit this surface.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/operator-ux/plans/PLAN-06-user-language-and-vocabulary.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

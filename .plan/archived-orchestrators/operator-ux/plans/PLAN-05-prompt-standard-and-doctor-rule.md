# PLAN-05: Make the AskUserQuestion standard testable, and enforce it

epic: operator-ux
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-05-prompt-standard-and-doctor-rule.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

An authoring reference for `AskUserQuestion` already exists and is not being met, so this is a
conformance problem rather than a greenfield one. Sharpen `askuserquestion-patterns.md` from
guidance into rules a reader can fail against, then add a `plugin-doctor` rule that flags a
violating prompt at authoring time. The governing test comes from the operator's own pasted
example: a prompt whose option reads *"pick this only if you want the plan to avoid loading
the Java/CUI standard sets"* asks the user to reason about skill-loading mechanics in order to
answer a question about their own code. That option must fail the rule.

## Deliverables

1. `askuserquestion-patterns.md` restructured around testable obligations. At minimum: every
   option states its consequence; no option is describable only in system-internal mechanics;
   the recommended option is marked and ordered first; the question names what the system
   already knows and why it still needs the user; and the preamble carries no workflow step
   number, tool-API type, or internal noun.
2. A `plugin-doctor` rule implementing the mechanically checkable subset — the preamble/option
   vocabulary check and the missing-consequence check are tractable; the "answerable without
   reading the codebase" judgement is not, and the rule must not pretend otherwise.
3. The rule registered in `plugin-doctor/references/rule-catalog.md` with its severity and its
   safe/prompted-fix classification.
4. A stated, deliberate scope for what the rule CANNOT catch, so a clean doctor run is not
   mistaken for a conformant prompt — an audit separates what it could not evaluate from what
   it evaluated and found wanting.
5. Tests: the pasted api-sheriff prompt (preamble and option 4) is used verbatim as a
   negative fixture and must fail the rule; a conformant rewrite must pass.

## Claim Labels

- OBSERVED: `askuserquestion-patterns.md` exists as the authoring reference — read at
  `marketplace/bundles/pm-plugin-development/skills/plugin-architecture/references/askuserquestion-patterns.md`.
- OBSERVED: 126 marketplace files reference `AskUserQuestion`; the prompt-dense docs are
  `menu-configuration.md` (29), `branch-cleanup.md` (24), `phase-1-init/SKILL.md` (20) and
  `planning.md` (18). These are DERIVED counts from a grep at HEAD and are labelled as such;
  they bound the remediation sweep PLAN-08 performs, not this plan's own scope.
- OBSERVED: The operator's pasted prompt leaks internal vocabulary in its preamble — *"Domain
  detection returned ambiguous (no narrative match). Per Step 7 this requires an operator
  multiSelect"* — naming a workflow step number and a tool-API type. Source: operator paste,
  first-party plan-marshall output.
- HYPOTHESIS: `plugin-doctor`'s rule surface supports a prose/markdown-content rule of this
  shape, rather than only structural/frontmatter rules — confirm/refute at
  `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md`
  § the existing rule inventory and the rule-implementation seam (verify-at-outline). ⛔ If the
  rule engine cannot express a content check, re-scope deliverable 2 to a review-checklist
  entry plus a `ext-self-review-plan-marshall` candidate surface, which is the shipped pattern
  for exactly this class.
- Verify-first clause: settle at outline whether an existing `ext-self-review-plan-marshall`
  candidate already covers user-facing-string checks. If so, extend it rather than adding a
  second detector — a second detector for one property is the defect this marketplace names
  repeatedly.

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-architecture/references/askuserquestion-patterns.md`
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md`
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/`
- OBSERVED: `test/marketplace/`
- HYPOTHESIS: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/`
  — touched only if the verify-first clause resolves toward extending it (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none. Deliberately independent so it can run in the second concurrency slot.
- Overlaps with: PLAN-08, which CONSUMES this standard but does not edit it.
- Adjacent to: `persona-plan-marshall-agent/standards/user-communication.md` — PLAN-06's
  surface, and the settled single home of the language/vocabulary/volume rules. This standard
  CITES it by anchor and does not restate it; if PLAN-06 has not landed, the anchor is a
  forward reference verified at outline.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/operator-ux/plans/PLAN-05-prompt-standard-and-doctor-rule.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

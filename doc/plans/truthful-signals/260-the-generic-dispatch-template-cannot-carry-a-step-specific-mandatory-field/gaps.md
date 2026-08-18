# Gaps — the-generic-dispatch-template-cannot-carry-a-step-specific-mandatory-field

**Source:** verification.md (same directory)   **Open items:** 5

## G1 — Link the input-table `Required: Yes` row to `requires_prompt_fields`, or the class stays open

- **Kind:** incomplete-sweep
- **Severity:** high
- **Where:** `test/plan-marshall/phase-6-finalize/test_step_prompt_fields_contract.py:211` — `_step_specific_fields`; `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md:132`
- **What is wrong:** the guard reads the *carriage* half only from `prompt: |` blocks inside a step's own
  doc. Running the module's own `_prompt_blocks` over all 26 `ext-point-finalize-step` implementors
  returns a block for exactly 2 of them (`pre-submission-self-review`, `finalize-step-simplify`); for the
  other 24 the carried set is always empty and `test_no_undeclared_prompt_field` is vacuous. Nothing
  anywhere links a step's input-table `Required: Yes` row — the surface on which `candidates` was
  declared, and the surface the plan's Problem section quotes — to the new frontmatter key. Demonstrated:
  adding a `| ghost_input | Yes | … |` row to a `Prompt-body field | Required` table in
  `phase-6-finalize/workflow/create-pr.md`, with no `requires_prompt_fields`, leaves the suite at
  **14 passed**.
- **Why it matters:** the plan's original defect — a step declares a mandatory prompt-body field, the
  generic dispatcher cannot carry it, and nothing fails — is still reproducible today for any of the 24
  generically-dispatched steps. The suite reports green over a class it does not cover, which is worse
  than no guard because it reads as closure.
- **Fix:** add a third assertion to the module that derives, per implementor, the set of input-table rows
  under a `Required` column whose key is outside `_CONTRACT_FIELDS`, and asserts that set equals the
  step's `requires_prompt_fields` declaration. Parse the table header to locate the `Required` column
  rather than assuming a position (a header-aware scan over the 26 docs returns exactly one hit today,
  `default:pre-submission-self-review` / `candidates`, so the new assertion starts green). State the
  input table as the third checked surface in `ext-point-finalize-step.md` § "Step-specific prompt-body
  fields", replacing the current "these two quantified directions are the ONLY … detector scope".
- **Done when:** injecting a `Required: Yes` non-contract prompt-body row into any finalize-step doc
  without adding the matching `requires_prompt_fields` entry turns a test in
  `test_step_prompt_fields_contract.py` red.
- **Module/topic:** `plan-marshall` bundle — `phase-6-finalize` / `extension-api` prompt-body contract.

## G2 — D1's extension slot and D2's guard contradict each other

- **Kind:** bug
- **Severity:** high
- **Where:** `test/plan-marshall/phase-6-finalize/test_step_prompt_fields_contract.py:304` — `test_no_orphan_prompt_field_declaration`; `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:645`; `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md:134`
- **What is wrong:** D1 gave both generic templates an extension slot so a generically-dispatched step
  *can* have step-specific fields forwarded ("the five fields are a floor, not a ceiling … the dispatcher
  MUST forward every declared field", `SKILL.md:645`). D2's ∃-direction then requires every declared field
  to appear in the step's **own** `prompt:` block, so a step that uses the new slot is rejected.
  Demonstrated: adding `requires_prompt_fields: [pr_template]` to `create-pr.md` (a step with no own
  snippet) turns `test_no_orphan_prompt_field_declaration` **and**
  `test_every_declaring_doc_has_a_parseable_dispatch_block` red. The assertion message and
  `ext-point-finalize-step.md:134` both justify the rejection with "the generic template carries only the
  five generic fields and cannot send a step-specific one" — a statement the same run's D1 edit made
  false.
- **Why it matters:** the mechanism the plan built is unusable in the exact configuration it was built
  for. The first author to follow `SKILL.md:645` and declare a field for the generic slot gets a red build
  and a failure message telling them something untrue about the template they just read.
- **Fix:** decide which carriage sites are admissible and make the ∃-direction reflect it. Either accept
  the generic template as a carriage site (a declaring step with no own `prompt:` block is compliant, and
  `test_every_declaring_doc_has_a_parseable_dispatch_block` becomes conditional on the step having its
  own snippet), or drop the extension slot and require an own snippet, in which case `SKILL.md:641`,
  `SKILL.md:645` and `SKILL.md:1040–1052` must say so. Then reword the assertion message and
  `ext-point-finalize-step.md:134` so neither restates the falsified "cannot send a step-specific one".
- **Done when:** a generically-dispatched step declaring `requires_prompt_fields` either passes the suite
  (option 1) or is rejected by a message that matches what `phase-6-finalize/SKILL.md` tells an author to
  do (option 2), and no document or assertion string claims the generic template cannot carry a
  step-specific field.
- **Module/topic:** `plan-marshall` bundle — `phase-6-finalize` / `extension-api` prompt-body contract.

## G3 — The "mandatory" declaration rule is already violated by the dispatcher's own runtime inputs

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md:48` — the `requires_prompt_fields` row; against `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:196-203` and `SKILL.md:1041-1044`
- **What is wrong:** the ext-point row says declaring the field is "**mandatory** for a step whose
  dispatch body carries any field beyond the generic contract", and defines the generic contract as six
  names. But `SKILL.md:196–203` states DISPATCHED external steps receive "`--iteration`, `producer`,
  whitelisted `--session-id`" *in addition to* declared fields, and `SKILL.md:1041–1044` instructs the
  dispatcher to forward `--iteration` and `producer` "as workflow-specific prompt-body inputs".
  `dispatch-inline-split.md:29` names `producer=plugin-doctor` for `project:finalize-step-plugin-doctor`,
  whose SKILL.md declares no `requires_prompt_fields`; `dispatch-inline-split.md:32` names the
  `--session-id` forward to `plan-marshall:plan-retrospective`, likewise undeclared; and the wait-region
  dispatch at `SKILL.md:1506–1521` carries `producer`, `caller_phase`, `pr_number`. Two documents
  therefore license an undeclared extra-field class that a third calls a mandatory-declaration violation,
  and nothing detects the disagreement.
- **Why it matters:** an author classifying a new step reads "mandatory for any field beyond the generic
  contract", sees `iteration` and `producer` in the dispatch body, and either declares them (turning the
  ∃-direction red per G2) or concludes the rule does not mean what it says. Both outcomes erode the
  declaration surface the plan created.
- **Fix:** name the runtime-input class explicitly in the `requires_prompt_fields` row — either fold
  `iteration`, `producer`, `session_id`, `caller_phase` and `pr_number` into a named
  dispatcher-supplied-inputs set that is exempt from declaration (and add them to `_CONTRACT_FIELDS`, or
  to a second exempt frozenset, in the test), or make them declarable and declare them on the steps that
  receive them. Keep `SKILL.md:196–203`, `SKILL.md:1041–1044` and `ext-point-finalize-step.md:48` saying
  the same thing.
- **Done when:** `ext-point-finalize-step.md` § "Step-specific prompt-body fields" and
  `phase-6-finalize/SKILL.md` § "Interface Contract for External Steps" agree on whether
  `iteration`/`producer`/`session_id`/`caller_phase`/`pr_number` must be declared, and the test's exempt
  set matches that decision.
- **Module/topic:** `plan-marshall` bundle — `phase-6-finalize` / `extension-api` prompt-body contract.

## G4 — report-01.md's D0 direction-2 answer "none" is contradicted by the tree

- **Kind:** doc-drift
- **Severity:** medium
- **Where:** `doc/plans/truthful-signals/260-…/report-01.md` § D0, "Direction 2 — fields a dispatch body carries that no step declares: **none**"
- **What is wrong:** the answer holds only under the narrowed scope "fields inside a *step doc's own*
  `prompt:` block". Under the question as the plan states it, the finalize dispatch bodies carry
  `iteration`, `producer`, whitelisted `session_id` (`SKILL.md:196-203`, `SKILL.md:1041-1044`) and
  `producer`/`caller_phase`/`pr_number` (`SKILL.md:1506-1521`), none of which any step declares in
  `requires_prompt_fields`. The report's accompanying claim "The generic templates carry only the generic
  contract fields" is true of the fenced block and false of the forwarding instruction printed directly
  beneath it.
- **Why it matters:** direction 2 is the half the plan singles out as "the half nobody looks for". A
  reader taking the report's "none" at face value concludes the sweep was complete and will not re-run it.
- **Fix:** correct the D0 section of `report-01.md` to state the narrowed scope it actually swept, and
  record the runtime-input class as the direction-2 population (with its declaration surface being the
  workflow input tables, e.g. `verification-feedback.md:26-31` marking `producer` **Required: Yes**).
- **Done when:** the report's D0 direction-2 paragraph names both the scope it swept and the
  runtime-input fields it did not cover.
- **Module/topic:** plan documentation — `doc/plans/truthful-signals/260-…`.

## G5 — Two small factual slips left by the run

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/260-…/report-01.md` § D3 ("13 tests"); `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md:126` (link display text)
- **What is wrong:** (a) the report states "13 tests, all green post-fix"; the landed file contains 14
  `def test_` functions (`git show 95116c07:test/plan-marshall/phase-6-finalize/test_step_prompt_fields_contract.py | grep -c '^def test_'` → 14) and 14 pass at HEAD — the review-fix regression test is
  mentioned later but never folded into the count. (b) the new section's link renders as
  `../../agents/execution-context.md`, which resolves to
  `marketplace/bundles/plan-marshall/skills/agents/execution-context.md` — a path that does not exist;
  only the href (`../../../agents/execution-context.md`) is correct, so a reader copying the visible path
  lands nowhere.
- **Why it matters:** (a) a stated count that does not re-derive is the exact defect class this epic
  tracks; (b) the display text is the half a reader copies.
- **Fix:** change "13 tests" to 14 in `report-01.md` § D3; change the link display text at
  `ext-point-finalize-step.md:126` to `../../../agents/execution-context.md` so text and href agree.
- **Done when:** the report's test count equals `grep -c '^def test_'` on the file, and the displayed link
  path in `ext-point-finalize-step.md:126` resolves to an existing file.
- **Module/topic:** `plan-marshall` bundle — `extension-api` standards; plan documentation.

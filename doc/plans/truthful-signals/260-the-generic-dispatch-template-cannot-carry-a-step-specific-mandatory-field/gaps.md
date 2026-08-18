# Gaps — the-generic-dispatch-template-cannot-carry-a-step-specific-mandatory-field

**Source:** verification.md (same directory)   **Open items:** 7

## G1 — Link the input-table `Required: Yes` row to `requires_prompt_fields`, or the class stays open

- **Kind:** incomplete-sweep
- **Severity:** high
- **Where:** `test/plan-marshall/phase-6-finalize/test_step_prompt_fields_contract.py:211` — `_step_specific_fields`; `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md:130` (names the input table as the declaration surface), `:132` ("the ONLY … detector scope"), `:137` ("asserts both directions and no third scope")
- **What is wrong:** the guard reads the *carriage* half only from `prompt: |` blocks inside a step's own
  doc. Running the module's own `_prompt_blocks` over all 26 `ext-point-finalize-step` implementors
  returns a block for exactly 2 of them (`pre-submission-self-review`, `finalize-step-simplify`); for the
  other 24 the carried set is always empty and `test_no_undeclared_prompt_field` is vacuous. Nothing
  anywhere links a step's input-table `Required: Yes` row — the surface on which `candidates` was
  declared, the surface the plan's Problem section quotes, and the surface
  `ext-point-finalize-step.md:130` itself names ("the declaration (a field the step's **input table**
  marks Required)") — to the new frontmatter key. Demonstrated: adding a `| ghost_input | Yes | … |` row
  to a `Prompt-body field | Required` table in `phase-6-finalize/workflow/create-pr.md`, with no
  `requires_prompt_fields`, leaves the module at **14 passed** and the wider
  `test/plan-marshall/phase-6-finalize/` + `test/plan-marshall/extension-api/` sweep unchanged.
- **Why it matters:** the plan's original defect — a step declares a mandatory prompt-body field, the
  generic dispatcher cannot carry it, and nothing fails — is still reproducible today for any of the 24
  generically-dispatched steps. The suite reports green over a class it does not cover, which is worse
  than no guard because it reads as closure. The doc states the input table as the declaration surface
  one paragraph before declaring the gap closed by a guard that never reads it.
- **Fix:** add a third assertion to the module that derives, per implementor, the set of input-table rows
  under a `Required` column whose key is outside `_CONTRACT_FIELDS`, and asserts that set equals the
  step's `requires_prompt_fields` declaration. Parse the table header to locate the `Required` column
  rather than assuming a position (a header-aware scan over the 26 docs returns exactly one hit today,
  `default:pre-submission-self-review` / `candidates`, so the new assertion starts green). State the
  input table as the third checked surface in `ext-point-finalize-step.md` § "Step-specific prompt-body
  fields", replacing the current "these two quantified directions are the ONLY … detector scope" at
  line 132 and the "asserts both directions and no third scope" at line 137.
- **Done when:** injecting a `Required: Yes` non-contract prompt-body row into any finalize-step doc
  without adding the matching `requires_prompt_fields` entry turns a test in
  `test_step_prompt_fields_contract.py` red.
- **Module/topic:** `plan-marshall` bundle — `phase-6-finalize` / `extension-api` prompt-body contract.

## G2 — D1's extension slot and D2's guard contradict each other

- **Kind:** bug
- **Severity:** high
- **Where:** `test/plan-marshall/phase-6-finalize/test_step_prompt_fields_contract.py:304` — `test_no_orphan_prompt_field_declaration`; `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:641`, `:645`, `:1040`, `:1043-1045`. The falsified rationale is shipped verbatim at **four** sites, all of which the fix must reword: (i) `test_step_prompt_fields_contract.py:317` (the assertion message), (ii) the same file's module docstring, lines 19–21, (iii) `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md:134`, (iv) `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:53`.
- **What is wrong:** D1 gave both generic templates an extension slot so a generically-dispatched step
  *can* have step-specific fields forwarded (`SKILL.md:641`, `:1040`; "those five are a **floor, not a
  ceiling** … the dispatcher MUST forward every declared field", `SKILL.md:645`). D2's ∃-direction then
  requires every declared field to appear in the step's **own** `prompt:` block, so a step that uses the
  new slot is rejected. Demonstrated (re-run independently): adding `requires_prompt_fields:
  [pr_template]` to `create-pr.md` — a `default:` step dispatched through generic template 1, with no own
  snippet — turns `test_no_orphan_prompt_field_declaration` **and**
  `test_every_declaring_doc_has_a_parseable_dispatch_block` red, with the message
  `["default:create-pr: ['pr_template']"]`.
  `SKILL.md:645` is additionally self-contradictory inside one sentence: it says the dispatcher MUST
  forward every declared field via the `<…>` slot **and** that "a step's extras live in its own dispatch
  body". Those are two different carriage sites, and the guard admits only the second.
  All four sites listed above justify the rejection with "the generic template carries only the five
  generic fields and [structurally] cannot send a step-specific one" — a statement `SKILL.md:641`/`:645`,
  landed in the same commit `95116c07`, made false. Site (iv) is in a file this run edited, so the
  contradiction is intra-commit, not inherited.
- **Why it matters:** the mechanism the plan built is unusable in the exact configuration it was built
  for. The first author to follow `SKILL.md:645` and declare a field for the generic slot gets a red build
  and a failure message telling them something untrue about the template they just read.
- **Fix:** decide which carriage sites are admissible and make the ∃-direction reflect it. Either (1)
  accept the generic template as a carriage site — a declaring step with no own `prompt:` block is
  compliant, and `test_every_declaring_doc_has_a_parseable_dispatch_block` becomes conditional on the
  step having its own snippet — or (2) drop the extension slot and require an own snippet, in which case
  `SKILL.md:641`, `:645` and `:1040-1052` must say so and stop instructing the dispatcher to forward.
  Then reword all four sites named in **Where** so none restates "the generic template … cannot send a
  step-specific one", and remove the "a step's extras live in its own dispatch body" clause from
  `SKILL.md:645` if option (1) is taken.
- **Done when:** a generically-dispatched step declaring `requires_prompt_fields` either passes the suite
  (option 1) or is rejected by a message that matches what `phase-6-finalize/SKILL.md` tells an author to
  do (option 2); and `grep -rn "cannot send a step-specific one\|cannot carry a step-specific field"
  marketplace/ test/` returns zero hits.
- **Module/topic:** `plan-marshall` bundle — `phase-6-finalize` / `extension-api` prompt-body contract.

## G3 — The "mandatory" declaration rule is already violated by the dispatcher's own runtime inputs

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md:48` — the `requires_prompt_fields` row; against `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:196-203` and `SKILL.md:1041-1044`; `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md:27` and `:30`
- **What is wrong:** the ext-point row says declaring the field is "**mandatory** for a step whose
  dispatch body carries any field beyond the generic contract", and defines the generic contract as six
  names. But `SKILL.md:196–203` states DISPATCHED external steps receive "`--iteration`, `producer`,
  whitelisted `--session-id`" *in addition to* declared fields, and `SKILL.md:1041–1044` instructs the
  dispatcher to forward `--plan-id`, `--iteration` and any `producer` runtime input "as workflow-specific
  prompt-body inputs". `dispatch-inline-split.md:27` names `producer=plugin-doctor` for
  `project:finalize-step-plugin-doctor` (whose `.claude/skills/finalize-step-plugin-doctor/SKILL.md`
  declares no `requires_prompt_fields` and documents `--iteration` in its own Interface Contract);
  `dispatch-inline-split.md:30` names the `--session-id` forward to `plan-marshall:plan-retrospective`,
  likewise undeclared. `iteration` is the cleanest instance: it goes to **every** dispatched external
  step and no step declares it. Two documents therefore license an undeclared extra-field class that a
  third calls a mandatory-declaration violation, and nothing detects the disagreement.
- **Why it matters:** an author classifying a new step reads "mandatory for any field beyond the generic
  contract", sees `iteration` and `producer` in the dispatch body, and either declares them (turning the
  ∃-direction red per G2) or concludes the rule does not mean what it says. Both outcomes erode the
  declaration surface the plan created.
- **Fix:** name the runtime-input class explicitly in the `requires_prompt_fields` row — either fold
  `iteration`, `producer` and whitelisted `session_id` into a named dispatcher-supplied-inputs set that
  is exempt from declaration (and add them to `_CONTRACT_FIELDS`, or to a second exempt frozenset, at
  `test_step_prompt_fields_contract.py:78-80`), or make them declarable and declare them on the steps
  that receive them. Keep `SKILL.md:196–203`, `SKILL.md:1041–1044` and `ext-point-finalize-step.md:48`
  saying the same thing.
- **Done when:** `ext-point-finalize-step.md` § "Step-specific prompt-body fields" and
  `phase-6-finalize/SKILL.md` § "Interface Contract for External Steps" agree on whether
  `iteration`/`producer`/`session_id` must be declared, and the test's exempt set matches that decision.
- **Module/topic:** `plan-marshall` bundle — `phase-6-finalize` / `extension-api` prompt-body contract.
- **Scope correction (adversarial review):** the earlier draft of this gap also cited the wait-region
  dispatch at `SKILL.md:1506-1521` (`producer` / `caller_phase` / `pr_number`). That block dispatches
  `plan-marshall/workflow/verification-feedback.md`, which is **not** an `ext-point-finalize-step`
  implementor (`find_implementors` returns 26 records; it is not among them), so
  `ext-point-finalize-step.md:48` does not govern it and it is not evidence for this gap. Its extra
  fields are sanctioned by the `*` catch-all row at `agents/execution-context.md:28`. The
  `caller_phase` half of that observation is real but is a different defect — see G7.

## G4 — report-01.md's D0 direction-2 answer "none" is contradicted by the tree

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/260-…/report-01.md` § D0, "Direction 2 — fields a dispatch body carries that no step declares: **none**"
- **What is wrong:** the answer holds only under the narrowed scope "fields inside a *step doc's own*
  `prompt:` block". Under the question as the plan states it, the finalize dispatch bodies for DISPATCHED
  external steps carry `--iteration`, `producer` and whitelisted `session_id` as workflow-specific
  prompt-body inputs (`SKILL.md:196-203`, `SKILL.md:1041-1044`), none of which any step declares in
  `requires_prompt_fields`. The report's accompanying claim "The generic templates carry only the generic
  contract fields" is true of the fenced block and false of the forwarding instruction printed directly
  beneath it (`SKILL.md:1041-1044`).
- **Why it matters:** direction 2 is the half the plan singles out as "the half nobody looks for". A
  reader taking the report's "none" at face value concludes the sweep was complete and will not re-run it.
- **Severity note (adversarial review):** re-severitied `medium` → `low`. The substantive half of this
  observation — the live contradiction in the bundle source — is G3 and carries the medium. What remains
  here is a correction to a dated run record whose claim is already superseded by verification.md § D0
  and by G3; nobody acts on the report's paragraph once those exist.
- **Fix:** correct the D0 section of `report-01.md` to state the narrowed scope it actually swept
  ("fields carried inside a step doc's own `prompt:` block"), and record the dispatcher's runtime-input
  class (`iteration`, `producer`, whitelisted `session_id`) as the direction-2 population it did not
  cover, with its declaration surface being the workflow input tables (e.g.
  `plan-marshall/workflow/verification-feedback.md:26` marks `producer` **Required: Yes**).
- **Done when:** the report's D0 direction-2 paragraph names both the scope it swept and the
  runtime-input fields it did not cover.
- **Module/topic:** plan documentation — `doc/plans/truthful-signals/260-…`.

## G5 — report-01.md states a test count that does not re-derive

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/260-…/report-01.md` § D3 — "All in `test_step_prompt_fields_contract.py` (13 tests, all green post-fix)"
- **What is wrong:** the landed file contains 14 `def test_` functions
  (`git show 95116c07:test/plan-marshall/phase-6-finalize/test_step_prompt_fields_contract.py | grep -c '^def test_'` → **14**), and 14 pass at HEAD
  (`uv run python -m pytest … -q` → `14 passed`). The report's own § Findings paragraph names the 14th
  (`test_field_parser_strips_any_bracketed_skills_index`, added by the review fix) but never folds it
  into the count.
- **Why it matters:** a stated count that does not re-derive is the exact defect class this epic tracks.
- **Fix:** change "13 tests, all green post-fix" to "14 tests, all green post-fix" in `report-01.md` § D3.
- **Done when:** the report's stated test count equals
  `grep -c '^def test_' test/plan-marshall/phase-6-finalize/test_step_prompt_fields_contract.py`.
- **Module/topic:** plan documentation — `doc/plans/truthful-signals/260-…`.

## G6 — Broken link display text in the new ext-point section

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md:126`
- **What is wrong:** the new § "Step-specific prompt-body fields" opens with
  `[`../../agents/execution-context.md`](../../../agents/execution-context.md)`. The **href** is correct
  (`marketplace/bundles/plan-marshall/agents/execution-context.md` exists); the **display text** resolves
  to `marketplace/bundles/plan-marshall/skills/agents/execution-context.md`, which does not exist. A
  reader copying the visible path lands nowhere, and the link-checker only validates the href.
- **Why it matters:** the display text is the half a reader copies; a link whose two halves disagree is a
  false signal that the checker is structurally unable to catch.
- **Separation note (adversarial review):** split out of the former G5, which bundled this with the test
  count. Two files, two fixes, two done-whens — one row each.
- **Fix:** change the link display text at `ext-point-finalize-step.md:126` from
  `../../agents/execution-context.md` to `../../../agents/execution-context.md` so text and href agree.
- **Done when:** the displayed link path at `ext-point-finalize-step.md:126` resolves to an existing file
  when joined to that file's directory.
- **Module/topic:** `plan-marshall` bundle — `extension-api` standards.

## G7 — `caller_phase` is a documented contract field the guard would flag as step-specific

- **Kind:** bug
- **Severity:** low
- **Where:** `test/plan-marshall/phase-6-finalize/test_step_prompt_fields_contract.py:78-80` — `_CONTRACT_FIELDS`; against `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-execution-context-workflow.md:101` and `:103`; the competing six-name definition at `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md:139`
- **What is wrong:** `ext-point-execution-context-workflow.md:101` declares `caller_phase:` "the optional
  `caller_phase:` field (**6th-field extension** of the canonical 5-field contract)" and `:103` repeats
  "`caller_phase` is the optional 6th field the orchestrator passes when dispatching a phase-agnostic
  workflow". `ext-point-finalize-step.md:139` defines a *different* six — "the six generic-contract names
  (`name`, `plan_id`, `skills`, `workflow`, `instructions`, `WORKTREE`)" — and `_CONTRACT_FIELDS` in the
  new guard encodes that second six. Consequently a finalize step doc that carried `caller_phase` in its
  own `prompt: |` block (the sanctioned usage for a phase-agnostic workflow) would be flagged by
  `test_no_undeclared_prompt_field` as carrying an undeclared step-specific field, and adding it to
  `requires_prompt_fields` would then contradict `ext-point-execution-context-workflow.md`.
- **Why it matters:** this is precisely the over-broad-fix class D3(c) exists to forbid — a guard that
  mis-classifies a documented contract field as step-specific. The control only anchors on
  `instructions`, so it does not cover the second XOR-free contract extension. Latent today: no
  implementor doc carries `caller_phase` in a `prompt:` block (verified — only 2 of 26 docs have a
  parseable block, carrying `{name, plan_id, skills, workflow, WORKTREE, candidates}` and
  `{name, plan_id, skills, instructions, WORKTREE}` respectively), so nothing fails now.
- **Fix:** reconcile the two "six-field" definitions on one source. Either add `caller_phase` to
  `_CONTRACT_FIELDS` (`test_step_prompt_fields_contract.py:78-80`) and to the name list at
  `ext-point-finalize-step.md:139`, or amend `ext-point-execution-context-workflow.md:101,103` to stop
  calling it a contract field and require it to be declared like any other step-specific field. Extend
  `test_contract_only_dispatch_is_not_flagged` (or add a synthetic sibling next to
  `test_instructions_block_carries_no_step_specific_field`) so a block carrying `caller_phase` is
  asserted **not** step-specific under whichever decision is taken.
- **Done when:** a synthetic prompt block containing `caller_phase:` is exercised by a test in
  `test_step_prompt_fields_contract.py`, and `ext-point-finalize-step.md` and
  `ext-point-execution-context-workflow.md` state the same contract-field set.
- **Module/topic:** `plan-marshall` bundle — `phase-6-finalize` / `extension-api` prompt-body contract.

## Refuted during adversarial review

No gap was refuted. G1–G5 were each re-tested against the tree — including three independent
edit-run-restore mutations — and all five survived. G3 and G4 had their supporting evidence **narrowed**
(the wait-region `SKILL.md:1506-1521` citation does not support them; see G3 § Scope correction), G4 was
**re-severitied** medium → low, and G5 was **split** into G5 + G6. Line references corrected:
`dispatch-inline-split.md:29`/`:32` → `:27`/`:30`. The evidence removed from G3/G4 is retained above
rather than deleted, because a later reader re-deriving direction 2 will find the same block and needs to
know it was considered and why it does not count.

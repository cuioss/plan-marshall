# Verification — the-generic-dispatch-template-cannot-carry-a-step-specific-mandatory-field

**Verified against:** commit `0314cc4d`   **Landed as:** PR #1197, commit `95116c07`   **Verdict:** implemented-with-gaps

## Method

What was actually done, in order:

- Read `plan.md` and `report-01.md` in full.
- Located the landing: `git log --oneline --all --grep '#1197'` → `95116c07`
  (`fix(phase-6-finalize): enforce step-specific prompt-body field declarations (#1197)`).
  Read the full landed diff (`git show 95116c07`, `git show --summary`). Also found the follow-up
  `beb5976b` (PR #1203) which closes this run's deferred residue.
- Opened at HEAD: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md`,
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` (lines 180–215, 600–650, 1000–1070,
  1495–1525), `.../phase-6-finalize/workflow/pre-submission-self-review.md`,
  `.../phase-6-finalize/standards/dispatch-inline-split.md`,
  `marketplace/bundles/plan-marshall/agents/execution-context.md`,
  `.../extension-api/standards/ext-point-execution-context-workflow.md`,
  `.../extension-api/standards/ext-point-dynamic-level-executor.md`,
  `.claude/skills/finalize-step-plugin-doctor/SKILL.md`,
  `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md`,
  and the whole of `test/plan-marshall/phase-6-finalize/test_step_prompt_fields_contract.py`.
- **Ran the test:** `uv run python -m pytest test/plan-marshall/phase-6-finalize/test_step_prompt_fields_contract.py -o addopts="" -q`
  → **14 passed** (report says 13; see Report accuracy).
- **Executed the derivations rather than reading them.** Scratch scripts driving the real
  `find_implementors()` and the test module's own parser:
  - finalize-step implementor population at HEAD = **26**; exactly one declares
    `requires_prompt_fields` (`default:pre-submission-self-review` → `['candidates']`).
  - Header-aware scan of every implementor's input tables for a `Required: Yes` row whose key is
    outside the six generic-contract names → **exactly one hit**, `default:pre-submission-self-review`
    / `candidates`. D0 direction 1 re-derives at n=1.
  - Ran the test module's `_prompt_blocks` over all 26 implementor docs → only **2** docs have a
    parseable `prompt: |` block (`pre-submission-self-review`, `finalize-step-simplify`); the other
    **24** yield zero blocks.
- **Three mutations, each on a file first confirmed clean with `git diff --quiet`, each restored from a
  byte copy taken before the edit (no `git checkout`/`restore`/`stash`), tree re-verified green
  afterwards (14 passed):**
  1. `pre-submission-self-review.md` frontmatter `requires_prompt_fields: [candidates, ghost]` →
     `test_no_orphan_prompt_field_declaration` **RED** with
     `["default:pre-submission-self-review: ['ghost']"]`. The guard fires exactly as the report claims.
  2. `create-pr.md` — added a `| Prompt-body field | Required | …` table with `| ghost_input | Yes |`
     and **no** `requires_prompt_fields` → **14 passed, still green**. The original declaration surface
     (an input-table Required row) is unguarded.
  3. `create-pr.md` — added `requires_prompt_fields: [pr_template]` to frontmatter (a step that
     dispatches through the generic template, i.e. the case D1's new extension slot exists for) →
     `test_every_declaring_doc_has_a_parseable_dispatch_block` and
     `test_no_orphan_prompt_field_declaration` both **RED**.
- Grepped the whole tree for `requires_prompt_fields` (7 non-plan-doc sites, all accounted for) and for
  `records_facts` / `advances_main_via_rebase` to check whether any central schema or plugin-doctor
  allowlist enumerates finalize-step frontmatter fields and was left unswept — none exists, so there is
  no missed sweep site there.
- Verified every cross-reference the new prose asserts by opening the target: the `*` row at
  `agents/execution-context.md:28`; the quoted prose at
  `ext-point-execution-context-workflow.md:67`; the 5-field statement at that file's line 103;
  `agents/execution-context.md` exists (the link href resolves, the display text does not — see G5).

Not an empty check-list: three mutations were applied and reverted, five derivations were executed
against the real registry, and 14 tests were run.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence |
|---|---|---|---|---|---|---|---|
| D0 | Derive the population both directions; report size; STOP-condition check | Population derived from the step docs' own required-field tables, both directions, size reported | yes | partly | direction 1 yes, direction 2 no | no | Direction 1 re-derives at **n=1** (input-table scan over all 26 implementors → only `default:pre-submission-self-review`/`candidates`). STOP condition genuinely resolved: `SKILL.md:635` is the live "Dispatch:" block for agent-suitable built-ins and `SKILL.md:1034` the live DISPATCHED project/skill block. Direction 2's answer "none" is contradicted — see G3/G4. |
| D1 | Generic path carries step-specific fields; rejected option recorded | One option implemented, the other recorded rejected with reason | yes | yes | yes | yes | Extension slot present at `SKILL.md:641` and `SKILL.md:1040`; prose "floor, not a ceiling" at `SKILL.md:645`; option (b) rejected in `report-01.md` § D1 with the checked precondition (24 of 26 step docs have no own dispatch snippet — re-derived). Out-of-scope honoured: `candidates` is **not** hard-coded into either template (grep confirms). |
| D2 | Divergence must be a build/test-time error | An intentionally divergent step fails the gate | yes | partly | fires, but see G1/G2 | **no** | Mutation 1 turns `test_no_orphan_prompt_field_declaration` red — the guard is real, not inert. But mutation 2 shows the gate is silent for the population the plan is about, and mutation 3 shows it rejects the very usage D1 created. |
| D3 | Three tests, each seen red pre-fix | (a) orphan rejected, (b) population non-empty + known instance, (c) control unchanged — all pass | yes | yes | yes | yes (within D2's scope) | `test_no_orphan_prompt_field_declaration` (a), `test_declared_population_is_non_empty` + `test_population_contains_the_known_instance` (b), `test_contract_only_dispatch_is_not_flagged` (c) — all present and green; 14/14 pass. (c) anchors on the real `default:finalize-step-simplify`, and the two `*_fires_on_an_injected_divergence` tests are committed proof the detectors fire. Red-first observations themselves are process claims not reproducible from the tree — the report says so. |

**D0.** Direction 1 is sound and re-derives independently. Direction 2 — "fields a dispatch body
carries that no step declares: none" — does not survive contact with the tree. The finalize dispatcher's
own dispatch bodies carry fields beyond the six generic-contract names, for steps that declare no
`requires_prompt_fields`: `SKILL.md:196–203` states that DISPATCHED external steps receive
"`--iteration`, `producer`, whitelisted `--session-id`"; `SKILL.md:1041–1044` repeats the instruction to
"forward `--plan-id`, `--iteration`, and any `producer` runtime input **as workflow-specific prompt-body
inputs**"; `dispatch-inline-split.md:29` names `producer=plugin-doctor` as the runtime input for
`project:finalize-step-plugin-doctor` (whose `.claude/skills/finalize-step-plugin-doctor/SKILL.md`
declares no `requires_prompt_fields`); and the wait-region block at `SKILL.md:1506–1521` carries
`producer`, `caller_phase` and `pr_number`. The report's answer is only true if the scope is narrowed to
"fields carried inside a *step doc's own* `prompt:` block", which is not what direction 2 asks.

**D2.** The guard exists, is population-derived, and fires (mutation 1). Its defect is where it looks for
the *carriage* half: `_step_specific_fields()` (test file, lines 211–222) reads only `prompt: |` blocks
inside the step's **own doc**. 24 of 26 finalize-step implementors have no such block, so for them
`carried` is always the empty set and `test_no_undeclared_prompt_field` is vacuous; and no assertion
anywhere links the input-table `Required: Yes` row — the surface on which `candidates` was originally
declared, and the one the plan's Problem section quotes — to the new frontmatter key. Mutation 2
demonstrates this directly: a step doc declaring a new Required non-contract prompt-body field in its
input table, with no `requires_prompt_fields` and no own snippet, is the plan's original defect
reproduced verbatim, and the suite stays green. The producerless row was not closed; a third place was
added and two of the three linked.

**D2 vs D1.** Mutation 3 shows the two deliverables disagree. D1 gave the generic template an extension
slot precisely so a step can declare a field and have the dispatcher forward it. D2's ∃-direction rejects
exactly that: a generically-dispatched step that declares `requires_prompt_fields` is flagged as an
orphan, and the assertion message states "the generic template carries only the five generic fields and
cannot send a step-specific one" — a claim the same run's D1 edit falsified. The same falsified rationale
is restated at `ext-point-finalize-step.md:134`.

## Report accuracy

Contradictions found, having re-derived every figure and opened every cited file:

1. **"D0 Direction 2 … none."** Contradicted — see D0 above. `iteration`, `producer`, whitelisted
   `session_id`, `caller_phase` and `pr_number` are all carried in finalize dispatch bodies beyond the
   generic contract, and none is declared in any `requires_prompt_fields`. (They *are* declared in prose
   input tables — e.g. `verification-feedback.md:26–31` marks `producer` **Required: Yes** — so the
   accurate statement is "declared on a different, unguarded surface", not "none".)
2. **"13 tests, all green post-fix."** The landed file contains **14** `def test_` functions
   (`git show 95116c07:test/…` → 14), and 14 pass at HEAD. The report's own later paragraph mentions the
   14th (`test_field_parser_strips_any_bracketed_skills_index`, added by the review fix `ab1247d`), so
   the count is stale rather than wrong in kind.
3. **"The guard is proven to fire."** Confirmed, not contradicted — mutation 1 reproduces the reported
   failure text exactly.
4. **"`ext-point-finalize-step.md:3` Implementations: 25 — verified correct."** Correct as of the run;
   the value is **26** today, and 26 is what `find_implementors()` returns at HEAD. The change is a later
   plan's step addition, not drift introduced here.
5. Findings 1, 2, 3 are genuinely fixed in the tree: the `*` row is cited at
   `agents/execution-context.md:28` and the prose rule at `ext-point-execution-context-workflow.md:67`
   (both quotes verified verbatim); the control docstring says "in place of `workflow`"
   (test file line 346); the `requires_prompt_fields` cross-reference is present at `SKILL.md:199–202`.
6. Everything else checked — the STOP-condition resolution, the "every step has its own snippet"
   refutation, the `instructions`-is-a-contract-field classification, the option-(b) rejection reason,
   the "not hard-coded into the generic template" out-of-scope compliance — re-derives cleanly.

## Out-of-scope compliance

Clean. The landed diff is six paths: the plan-directory rename (`260-….md` → `260-…/plan.md`, 100%
similarity), the new `report-01.md`, and the four substantive files — all inside the plan's Expected
surface. `ref-workflow-architecture/**` was listed as expected surface but not touched; that is a
permitted non-use, not a violation. `candidates` was **not** added to the generic template (the explicit
out-of-scope prohibition) — verified by grep: the only occurrences of `candidates` in `SKILL.md` are
unrelated. No `.plan/` write, no collateral edit, no step-workflow content rewrite beyond the required
declaration.

## Residue carried forward

- **Deferred finding 5** — `ext-point-dynamic-level-executor.md:159` stating categorically that every
  dispatch uses "the 5-field prompt body". **CLOSED** by a later commit, `beb5976b` (PR #1203,
  `chore(extension-api): correct the dispatch prompt-body claim to match its example`). Line 159 now
  reads "the generic contract fields … plus any workflow-specific runtime inputs the workflow declares
  in its own input table". Not open.
- **Finding 6** (red-first evidence not reproducible from the diff) — rejected with reason; the two
  `*_fires_on_an_injected_divergence` tests are in the tree and pass. Settled.
- No other residue was declared.

## What could NOT be verified

- The report's build-gate figures (`./pw quality-gate` `total_issues: 0` whole-tree;
  `./pw module-tests plan-marshall` 16262 passed / 1 skipped) were **not** re-run — too expensive for this
  pass, and both are point-in-time measurements against a tree that has since moved. Only the plan's own
  test file was executed.
- The **red-first** claims in D3 are process observations about the run's session. They are inherently
  unverifiable from the tree; the committed injected-divergence tests are the substitute evidence and
  they do pass.
- CI state (`verify / conclusion` success on `091135e`, re-trigger on `ab1247d`) and the PR review /
  reviewer-participation table were not checked against GitHub.
- Whether the LLM dispatcher at runtime actually forwards a declared field: the guard proves only what
  the *documents* say, and no runtime validation exists — `agents/execution-context.md` Step 1
  ("Validate Prompt-Body Contract (MANDATORY)", lines 49–56) checks only `name`, `plan_id`, `WORKTREE`
  and the `workflow`/`instructions` XOR, and was not extended by this plan. This is a scope observation,
  not a gap against the done-when (which permits test-time enforcement).

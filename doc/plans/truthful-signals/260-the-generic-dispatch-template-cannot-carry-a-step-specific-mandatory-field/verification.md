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
- Grepped the whole tree for `requires_prompt_fields` (**4** non-plan-doc files — `ext-point-finalize-step.md`,
  `phase-6-finalize/SKILL.md`, `pre-submission-self-review.md`, the test module — **23** occurrences in
  all, every one accounted for) and for
  `records_facts` / `advances_main_via_rebase` to check whether any central schema or plugin-doctor
  allowlist enumerates finalize-step frontmatter fields and was left unswept — none exists, so there is
  no missed sweep site there.
- Verified every cross-reference the new prose asserts by opening the target: the `*` row at
  `agents/execution-context.md:28`; the quoted prose at
  `ext-point-execution-context-workflow.md:65`; the 5-field statement at that file's line 103;
  `agents/execution-context.md` exists (the link href resolves, the display text does not — see G6).

Not an empty check-list: three mutations were applied and reverted, five derivations were executed
against the real registry, and 14 tests were run.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence |
|---|---|---|---|---|---|---|---|
| D0 | Derive the population both directions; report size; STOP-condition check | Population derived from the step docs' own required-field tables, both directions, size reported | yes | partly | direction 1 yes, direction 2 no | no | Direction 1 re-derives at **n=1** (input-table scan over all 26 implementors → only `default:pre-submission-self-review`/`candidates`). STOP condition genuinely resolved: `SKILL.md:631` introduces the live "Dispatch:" block for agent-suitable built-ins (fenced template at 634–642, over the five steps tabled at `SKILL.md:606–612`) and `SKILL.md:1033–1042` is the live DISPATCHED project/skill block. Direction 2's answer "none" is contradicted — see G3/G4. |
| D1 | Generic path carries step-specific fields; rejected option recorded | One option implemented, the other recorded rejected with reason | yes | yes | yes, but see G2 | yes | Extension slot present at `SKILL.md:641` and `SKILL.md:1040`; prose "floor, not a ceiling" at `SKILL.md:645`; option (b) rejected in `report-01.md` § D1 with the checked precondition (24 of 26 step docs have no own dispatch snippet — re-derived). Out-of-scope honoured: `candidates` is **not** hard-coded into either template (grep confirms). |
| D2 | Divergence must be a build/test-time error | An intentionally divergent step fails the gate | yes | partly | fires, but see G1/G2 | **no** | Mutation 1 turns `test_no_orphan_prompt_field_declaration` red — the guard is real, not inert. But mutation 2 shows the gate is silent for the population the plan is about, and mutation 3 shows it rejects the very usage D1 created. |
| D3 | Three tests, each seen red pre-fix | (a) orphan rejected, (b) population non-empty + known instance, (c) control unchanged — all pass | yes | yes | yes | yes (within D2's scope) | `test_no_orphan_prompt_field_declaration` (a), `test_declared_population_is_non_empty` + `test_population_contains_the_known_instance` (b), `test_contract_only_dispatch_is_not_flagged` (c) — all present and green; 14/14 pass. (c) anchors on the real `default:finalize-step-simplify`, and the two `*_fires_on_an_injected_divergence` tests are committed proof the detectors fire. Red-first observations themselves are process claims not reproducible from the tree — the report says so. |

**D0.** Direction 1 is sound and re-derives independently. Direction 2 — "fields a dispatch body
carries that no step declares: none" — does not survive contact with the tree. The finalize dispatcher's
own dispatch bodies carry fields beyond the six generic-contract names, for steps that declare no
`requires_prompt_fields`: `SKILL.md:196–203` states that DISPATCHED external steps receive
"`--iteration`, `producer`, whitelisted `--session-id`"; `SKILL.md:1041–1044` repeats the instruction to
"forward `--plan-id`, `--iteration`, and any `producer` runtime input **as workflow-specific prompt-body
inputs**"; `dispatch-inline-split.md:27` names `producer=plugin-doctor` as the runtime input for
`project:finalize-step-plugin-doctor` (whose `.claude/skills/finalize-step-plugin-doctor/SKILL.md`
declares no `requires_prompt_fields`), and `:30` the `--session-id` forward to
`plan-marshall:plan-retrospective`. The report's answer is only true if the scope is narrowed to
"fields carried inside a *step doc's own* `prompt:` block", which is not what direction 2 asks.
*(Adversarial-review correction: the wait-region block at `SKILL.md:1506–1521` was originally cited
here too. It dispatches `plan-marshall/workflow/verification-feedback.md`, which is not an
`ext-point-finalize-step` implementor, so it is not evidence for direction 2 over the step
population. The `iteration`/`producer`/`session_id` forwards above stand unchanged.)*

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

1. **"D0 Direction 2 … none."** Contradicted — see D0 above. `iteration`, `producer` and whitelisted
   `session_id` are carried in the dispatch bodies of DISPATCHED finalize steps beyond the generic
   contract, and none is declared in any `requires_prompt_fields`. (They *are* declared in prose input
   tables — e.g. `plan-marshall/workflow/verification-feedback.md:26` marks `producer` **Required:
   Yes** — so the accurate statement is "declared on a different, unguarded surface", not "none".)
   *Adversarial-review correction:* `caller_phase` and `pr_number` were also named here. They belong to
   the wait-region `verification-feedback` dispatch, which is not a finalize-step implementor, so they
   do not evidence direction 2 over the step population. `caller_phase` carries a separate defect of
   its own — see G7.
2. **"13 tests, all green post-fix."** The landed file contains **14** `def test_` functions
   (`git show 95116c07:test/…` → 14), and 14 pass at HEAD. The report's own later paragraph mentions the
   14th (`test_field_parser_strips_any_bracketed_skills_index`, added by the review fix the report calls
   `ab1247d` — a PR-branch SHA that does not resolve in this clone, the branch having been squash-merged;
   the test's presence in `95116c07` is the checkable fact and it holds), so
   the count is stale rather than wrong in kind.
3. **"The guard is proven to fire."** Confirmed, not contradicted — mutation 1 reproduces the reported
   failure text exactly.
4. **"`ext-point-finalize-step.md:3` Implementations: 25 — verified correct."** Correct as of the run;
   the value is **26** today, and 26 is what `find_implementors()` returns at HEAD. The change is a later
   plan's step addition, not drift introduced here.
5. Findings 1, 2, 3 are genuinely fixed in the tree: the `*` row is cited at
   `agents/execution-context.md:28` and the prose rule at `ext-point-execution-context-workflow.md:65`
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
out-of-scope prohibition) — verified by grep: `candidates` occurs **zero** times in `SKILL.md`. No `.plan/` write, no collateral edit, no step-workflow content rewrite beyond the required
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

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked.** Everything below was re-derived or re-executed from the tree at HEAD (`826791bd`), not read
off this document:

- **Commits.** `95116c07` and `beb5976b` resolve and carry the stated subjects. `0314cc4d` resolves.
  `ab1247d`, `929ffa4`, `cec4ccd`, `091135e` do **not** resolve (`git cat-file -t` → *not a valid object
  name*) — PR-branch SHAs lost to the squash-merge. Every claim resting on them is unverifiable in this
  clone and is now marked as such.
- **Test run.** `uv run python -m pytest test/plan-marshall/phase-6-finalize/test_step_prompt_fields_contract.py -q`
  → **14 passed**, both with and without the project's default `addopts` (so the module is genuinely
  collected by the build gate, not only by an overridden invocation). `grep -c '^def test_'` on the
  landed blob at `95116c07` → **14**.
- **Population, re-derived independently.** Drove `find_implementors('plan-marshall:extension-api/standards/ext-point-finalize-step')`
  → **26** records; exactly **one** declares `requires_prompt_fields`
  (`default:pre-submission-self-review` → `['candidates']`); the module's own `_prompt_blocks` yields a
  block for exactly **2** docs (`pre-submission-self-review`, `finalize-step-simplify`), so **24** carry
  none. Wrote an *independent* header-aware input-table scanner (locating the `Required` column by header
  position, over every table in all 26 docs, not only `Prompt-body field` tables) → **exactly one**
  `Required: Yes` row outside `_CONTRACT_FIELDS`: `default:pre-submission-self-review` / `candidates`.
  Parsed both real blocks: control `finalize-step-simplify` carries
  `{name, plan_id, skills, instructions, WORKTREE}` and resolves to zero step-specific fields, so D3(c)
  is **non-vacuous**.
- **Four mutations**, each on a file first confirmed clean with `git diff --quiet`, each restored from a
  byte copy taken before the edit (no `git checkout`/`restore`/`stash`), each restore re-verified with
  `git diff --quiet`:
  1. `create-pr.md` frontmatter `requires_prompt_fields: [pr_template]` → `test_no_orphan_prompt_field_declaration`
     and `test_every_declaring_doc_has_a_parseable_dispatch_block` **RED**, message
     `["default:create-pr: ['pr_template']"]`. G2 reproduced.
  2. `create-pr.md` body — a `| Prompt-body field | Required | Description |` table with
     `| ghost_input | Yes | … |` and no `requires_prompt_fields` → **14 passed**, and **1077 passed**
     across `test/plan-marshall/phase-6-finalize/` + `test/plan-marshall/extension-api/` (the two
     pre-existing `test_ci_verify.py` failures are present with and without the mutation and are
     unrelated). G1 reproduced against a **broader** suite than the original sweep.
  3. `pre-submission-self-review.md` — removed the `requires_prompt_fields` declaration →
     `test_declared_population_is_non_empty`, `test_population_contains_the_known_instance` **and**
     `test_no_undeclared_prompt_field` **RED**. D3(b) and the ∀-direction both bite.
  4. Tree re-verified after every restore; `git status --porcelain` shows no residue from this review in
     `marketplace/`, `test/` or `.claude/`.
- **Every clean-pass row re-opened.** D1 (extension slot at `SKILL.md:641`/`:1040`, prose at `:645`,
  option-(b) rejection precondition re-derived at 24-of-26, `candidates` absent from `SKILL.md`), D3
  (all five named tests present, control non-vacuous, mutation 3 proves (b) red-capable).
- **Every "swept, clean" claim re-swept with a broader pattern.** `requires_prompt_fields` across the
  whole tree (4 non-plan-doc files / 23 occurrences — the document's "7 sites" does not re-derive as
  either and is corrected). `head_dependent` across `*.py`/`*.json`/`*.toml` to look for a central
  frontmatter-key allowlist the run might have left unswept — only per-field consumers exist, no
  enumeration, so that claim holds. `grep -rn "cannot send a step-specific one\|cannot carry a
  step-specific field"` over `marketplace/`, `test/`, `.claude/` → **4** sites, two more than G2 named.
- **Every cited line number re-opened.** Corrected: `dispatch-inline-split.md:29`→`:27`, `:32`→`:30`,
  `ext-point-execution-context-workflow.md:67`→`:65`, `SKILL.md:635`→`:631`/`634–642`. Confirmed exact:
  `ext-point-finalize-step.md:48`, `:126`, `:130`, `:132`, `:134`, `:137`, `:139`; header count
  "Implementations: **26**" at that file's line 3 matches `find_implementors` today;
  `agents/execution-context.md:28` (`*` row) and `:49–56` (Step 1 validates only four things);
  `ext-point-execution-context-workflow.md:101`/`:103`; `SKILL.md:196–203`, `:606–612`, `:641`, `:645`,
  `:1033–1044`, `:1506–1521`; test file `:78–80`, `:211`, `:304`, `:317`, `:346`;
  `verification-feedback.md:26`; `ext-point-dynamic-level-executor.md:159` (residue **confirmed closed**
  — reads "the generic contract fields … plus any workflow-specific runtime inputs the workflow declares
  in its own input table"). Landed diff re-derived at **six** paths.
- **STOP condition re-checked from the dispatcher, not from the report.** `SKILL.md:606–612` tables the
  five agent-suitable built-ins (`create-pr`, `lessons-capture`, `adr-propose`, `automatic-review`,
  `sonar-roundtrip`) that template 1 dispatches, and `SKILL.md:1001–1044` is the DISPATCHED
  project/skill branch. Both templates are live. The plan is **not** mis-aimed.

**NOT re-checked.** The build-gate figures (`./pw quality-gate` whole-tree, `./pw module-tests
plan-marshall` 16262/1) — still unrun, for the same cost reason. GitHub state: PR #1197's CI conclusion,
review threads and the reviewer-participation table. The report's red-first process claims (inherently
unverifiable from the tree). The runtime behaviour of the LLM dispatcher. Two pre-existing
`test_ci_verify.py` failures at HEAD were observed but not investigated — they are outside this plan's
footprint.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| G1 | Guard vacuous for 24 of 26; input-table row unlinked | **upheld**, severity `high` confirmed | Mutation 2 re-run: 14 passed and 1077 passed across two test dirs. `_CONTRACT_FIELDS`/`_step_specific_fields` read no table anywhere (`grep` for `Required`/`table` in the module returns only prose). Strengthened: `ext-point-finalize-step.md:130` itself names the input table as the declaration surface two paragraphs before declaring the gap closed. |
| G2 | Extension slot and ∃-direction contradict | **upheld**, severity `high` confirmed, **rewritten** | Mutation 1 re-run, both tests red with the exact message. Two further instances of the falsified rationale found that G2 did not name — the module docstring (test file lines 19–21) and `pre-submission-self-review.md:53`, a file this run itself edited — so the contradiction is intra-commit. Also recorded: `SKILL.md:645` contradicts itself in one sentence (dispatcher MUST forward via the slot / "a step's extras live in its own dispatch body"), which is what makes the fix a decision rather than a wording pass. |
| G3 | Mandatory-declaration rule violated by dispatcher runtime inputs | **upheld** at `medium`, **evidence narrowed** | `SKILL.md:196–203` and `:1041–1044` confirmed verbatim; `dispatch-inline-split.md:27`/`:30` confirmed (line numbers were wrong, corrected). `iteration` is the cleanest instance — it reaches every dispatched external step and `finalize-step-plugin-doctor`'s own Interface Contract documents accepting it while declaring no `requires_prompt_fields`. The `SKILL.md:1506–1521` citation was **removed**: that dispatch targets `verification-feedback.md`, which `find_implementors` does not return, so `ext-point-finalize-step.md:48` does not govern it. |
| G4 | report-01.md's "Direction 2 … none" is wrong | **upheld**, **re-severitied** `medium` → `low` | The claim is wrong for the reason G3 gives. But its substantive half *is* G3, and what is left is a correction to a dated run record already superseded by this document. A stale sentence nobody acts on is not `medium`. |
| G5 | "13 tests" + broken link display text | **upheld but split** | Two defects, two files, two fixes were bundled in one row. Kept as G5 (the count: `git show 95116c07:… \| grep -c '^def test_'` → 14, `pytest` → 14 passed) and new **G6** (the link: href resolves to `marketplace/bundles/plan-marshall/agents/execution-context.md`, display text to a path `ls` reports absent). |
| G7 | *(new)* `caller_phase` classified as step-specific by the guard | **added**, `low` | `ext-point-execution-context-workflow.md:101,103` calls `caller_phase` "the optional 6th field" of the contract; `ext-point-finalize-step.md:139` defines a different six and `_CONTRACT_FIELDS` (test `:78–80`) encodes that one. A step doc carrying `caller_phase` in its own block would be flagged undeclared — the exact over-broad-fix class D3(c) exists to forbid, which the control does not cover. Latent: no implementor doc carries it today. |
| Verdict | `implemented-with-gaps` | **upheld** | Every deliverable is implemented; none is missing. D0's direction 2 and D2's coverage are wrong/incomplete rather than absent, which is `implemented-with-gaps`, not `partially-implemented`. |
| Figures | counts, line numbers, test totals | **4 corrected** | "7 non-plan-doc sites" → 4 files / 23 occurrences; "the only occurrences of `candidates` in `SKILL.md` are unrelated" → **zero** occurrences; four line references; `ab1247d` marked unresolvable. Every other figure re-derived exactly. |

**Documents corrected.** In `gaps.md`: G1 gained two further citations and a broader reproduction; G2 was
rewritten to name all four instances of the falsified rationale and the intra-sentence contradiction at
`SKILL.md:645`, with a grep-checkable Done-when; G3's line references were fixed and its wait-region
evidence withdrawn into an explicit scope-correction note; G4 was re-severitied to `low` with the reason
stated; G5 was split into G5 (test count) and G6 (link display text); G7 was added; the open-item count
moved 5 → **7**; a `## Refuted during adversarial review` section records that nothing was refuted and
what was withdrawn instead. In `verification.md`: the four figure corrections above, the narrowed D0
direction-2 and Report-accuracy-1 evidence, a `see G2` qualifier on the D1 correctness cell, the `G5` →
`G6` link-text cross-reference, and this section.

**Residual doubt — what a third reviewer should look at first.**

1. **Is `pre-submission-self-review`'s `prompt: |` block the same dispatch the ext-point row describes?**
   That block is the step **re-dispatching itself** (Step 1 runs inline and produces `candidates`; Step 2
   dispatches `workflow: …/pre-submission-self-review.md` with the envelope). The finalize dispatcher
   never forwards `candidates` — the step manufactures it. If that is right, then
   `ext-point-finalize-step.md:48`'s "…that the step's own dispatch `prompt:` block carries **and the
   dispatcher MUST forward**" is false of the single instance the whole mechanism is anchored on, and G2
   is a symptom of a deeper mis-modelling: `requires_prompt_fields` conflates *fields the finalize
   dispatcher must send* with *fields a step sends to its own sub-agent*. This was not pursued here and
   is the highest-value next question.
2. **Which dispatch branch actually runs `default:pre-submission-self-review`?** It is a `default:` step
   classified DISPATCHED at `dispatch-inline-split.md:19`, yet it is absent from the agent-suitable
   built-in table at `SKILL.md:606–612` and from the inline branch's source of truth. Either the table is
   incomplete or the branch selection is under-specified. Out of this plan's scope, but it bears on
   whether the generic template is the carriage site for this step at all.
3. The build-gate figures and the GitHub state, both still unverified.

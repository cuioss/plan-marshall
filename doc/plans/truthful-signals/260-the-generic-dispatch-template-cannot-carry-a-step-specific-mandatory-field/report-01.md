# Run report — the-generic-dispatch-template-cannot-carry-a-step-specific-mandatory-field (run 01)

**Date (UTC):** 2026-08-12 → 2026-08-13    **Branch:** `claude/generic-dispatch-template-field-615qbt` (harness-assigned)    **PR:** [#1197](https://github.com/cuioss/plan-marshall/pull/1197)    **Outcome:** completed (landing delegated — see Contract check)

## Skills loaded

Loaded by path from the bundle source (the `plan-marshall` plugin is not installed in this cloud session; `Read` of the bundle path is the route that always works):

- `plan-marshall:ref-code-quality` — `marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md` (always)
- `pm-plugin-development:plugin-script-architecture` — `.../pm-plugin-development/skills/plugin-script-architecture/SKILL.md` (always)
- `plan-marshall:ref-workflow-architecture` — dispatch topology / workflow docs surface
- `pm-plugin-development:plugin-architecture` — SKILL.md / bundle structure surface

The cloud-plan-lane contract itself was loaded first, before reading the plan.

## Deliverables

The plan is about a **producerless contract row**: a finalize step declares a required prompt-body field, the dispatcher that runs it has no enforced way to carry it, and nothing fails when the two disagree. The authoritative prompt-body contract (`marketplace/bundles/plan-marshall/agents/execution-context.md` § "Input — Prompt-Body Contract") is `name`, `plan_id`, `skills[]`, **exactly one of** `workflow`/`instructions`, `WORKTREE`, plus workflow-specific runtime inputs (the `*` row) the step declares in its own input table.

### D0 — GATE: derive population (both directions), report size, confirm template is followed

**STOP CONDITION resolved — the plan is NOT mis-aimed.** Both generic dispatch templates in `phase-6-finalize/SKILL.md` are followed by real dispatch paths, not illustrative:

- Template 1 (the "Dispatch:" block, and its restatement in the Execute-Step-Pipeline "BUILT-IN (agent-suitable)" branch) is the body the finalize dispatcher sends for the built-in agent-suitable steps: `create-pr`, `automatic-review`, `sonar-roundtrip`, `lessons-capture`, `adr-propose`.
- Template 2 (the "DISPATCHED project/skill step" branch) is the body sent for dispatched `project:`/`bundle:skill` steps (e.g. `finalize-step-plugin-doctor`).

**Population, both directions, n=1:**

- **Direction 1 — steps declaring a step-specific required field:** only `default:pre-submission-self-review` declares one — `candidates`, marked **Required: Yes** in its "Inputs (dispatched envelope — Steps 2–3)" table. It is a workflow-specific runtime input.
- **Direction 2 — fields a dispatch body carries that no step declares:** none. The only two finalize **step docs** with their own `prompt: |` dispatch block are `pre-submission-self-review.md` (carries `candidates`, now declared) and `finalize-step-simplify.md` (carries `instructions`). `instructions` is a **generic-contract field** — the XOR-alternative to `workflow` per the execution-context contract — **not** a step-specific field, so it needs no declaration. No bundle/project step doc carries a `prompt: |` block. The generic templates carry only the generic contract fields.

**Finding-as-filed partially refuted (as the plan's claim-labels anticipated):** the known field `candidates` **is** carried today — by `pre-submission-self-review`'s own Step 2 dispatch snippet, not by the generic template. Nothing is broken at runtime today. The defect is the latent producerless-contract row: the declaration and its carriage are two unlinked edits, and the generic path structurally cannot carry a step-specific field, so a future step declaring one while relying on the generic path would break silently.

**"Every step has its own dispatch snippet" hypothesis — REFUTED.** The five built-in agent-suitable steps and the dispatched project steps have no own dispatch snippet; they rely on the generic template. This is why D1 option (b) (below) is unsafe.

*Verification state:* verified by reading the dispatcher (`phase-6-finalize/SKILL.md` Execute-Step-Pipeline), the authoritative contract (`agents/execution-context.md`), and every finalize-step doc's `prompt: |` block. Mutates nothing (gate only).

### D1 — Decide how the generic path carries step-specific fields (+ record rejected option)

**Implemented: option (a) — the generic template gains an explicit extension slot.** Both generic templates in `phase-6-finalize/SKILL.md` now carry a `<plus every step-specific field the step declares in requires_prompt_fields>` slot and prose stating the five fields are a floor, not a ceiling, and that the dispatcher MUST forward every field a step declares in `requires_prompt_fields`. The plan's out-of-scope item (do **not** hard-code the one known field into the generic template) is honoured and is now stated explicitly in the template prose.

**Rejected option (b) — demote the generic template to illustrative and require every step to use its own snippet.** The plan flags this as cheaper (it removes the duplication) *but only if no step lacks its own snippet*. That precondition is **false**: the five built-in agent-suitable steps and every dispatched project step have no own dispatch snippet — they are dispatched via the generic template. Demoting it would strand them. Rejected for that reason.

*Verification state:* both templates edited; the quality-gate `broken-relative-link` and `literal-count-drift` rules pass over the edited files.

### D2 — Make the divergence fail (LOAD-BEARING)

**Implemented via the reference architecture** — the `records_facts` both-direction conformance pattern. Two artifacts:

1. A new **Conditional** frontmatter field `requires_prompt_fields: list[str]` on the finalize-step ext-point (`extension-api/standards/ext-point-finalize-step.md`), with its governing discriminator and a dedicated "Step-specific prompt-body fields" section documenting the both-direction contract.
2. A both-direction conformance test `test/plan-marshall/phase-6-finalize/test_step_prompt_fields_contract.py`, mirroring `test_step_records_facts_contract.py`:
   - **∃-direction (no orphan declaration):** every `requires_prompt_fields` key must appear in the step's own `prompt:` dispatch body. A field declared Required but left to the generic template (which cannot carry it) is a test error.
   - **∀-direction (no undeclared field):** every field a step's dispatch body carries beyond the generic contract must be declared.

**Injected-divergence demonstration (required by the plan's Verification):** with `requires_prompt_fields: [candidates, ghost]` on `pre-submission-self-review` (ghost not carried), `test_no_orphan_prompt_field_declaration` FAILS with `["default:pre-submission-self-review: ['ghost']"]`. Reverted after confirming. The guard is proven to fire.

*Verification state:* implemented and demonstrated red-on-divergence, green-when-consistent.

### D3 — Tests, each verified to FAIL pre-fix

All in `test_step_prompt_fields_contract.py` (13 tests, all green post-fix). Red-first evidence:

- **(a) a step declaring a required field absent from its dispatch body is rejected** — `test_no_orphan_prompt_field_declaration`. Seen red via the injected `ghost` divergence (above).
- **(b) population non-empty + contains the known instance** — `test_declared_population_is_non_empty` + `test_population_contains_the_known_instance`. Both seen red when the `requires_prompt_fields` declaration was temporarily removed (empty population). In that same pre-fix state `test_no_undeclared_prompt_field` also went red (`candidates` carried but undeclared), exercising the ∀-direction.
- **(c) control — a step with no step-specific field dispatches unchanged** — `test_contract_only_dispatch_is_not_flagged` (real `finalize-step-simplify`, which carries the contract field `instructions`) plus synthetic-block mutation guards. Seen red by temporarily treating `instructions` as non-contract: the control and the instructions mutation-guard both failed, proving the control catches the over-broad fix. Restored after.

Each red-first observation was produced by an actual edit-run-revert cycle in this session.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → one file (`test/plan-marshall/phase-6-finalize/test_step_prompt_fields_contract.py`) — **Python changed, build runs.**

- Quality gate (`./pw quality-gate`, whole tree): `total_issues: 0`; all 36 plugin-doctor rules 0 findings; coverage COMPLETE over mypy(production, 395 files), ruff, SPDX headers, plugin-doctor marketplace-wide.
- Tests (`./pw module-tests plan-marshall`): **16262 passed, 1 skipped, 0 failed** (6m54s). The single skip is a pre-existing environment guard unrelated to this change.

**Scope note:** the footprint is entirely within the `plan-marshall` bundle and `test/plan-marshall/`; every test that reads the edited docs lives under `test/plan-marshall/`, and plugin-doctor ran marketplace-wide in the quality gate. The merge queue's `merge_group` run performs the full-tree verify.

## Findings

**Verification sub-agent (Task, general-purpose), pre-PR — verdict: D0–D3 all PASS, no blocking gaps.** It independently re-derived the population two ways (via `find_implementors` + the module's own parser, and via an input-table scan of all 25 implementors), confirmed the STOP condition (both generic templates are live dispatch sites; the third `prompt: |` block is the fixed `wait-region-unified-triage` dispatch, correctly unmodified), confirmed `instructions` is a generic-contract field, and ran the 13 tests green. Findings and dispositions (recorded per instance):

| # | Source | Finding | Disposition |
|---|--------|---------|-------------|
| 1 | sub-agent | `ext-point-finalize-step.md` new section wrongly attributed a "`*` row" to `ext-point-execution-context-workflow.md` (that section states the rule in prose, line 66; the actual `*` table row is in `agents/execution-context.md` line 28) | **fixed** (commit 929ffa4) — cite the dispatcher agent's `*` row and the ext-point's prose rule accurately |
| 2 | sub-agent | Control test docstring called `instructions` a "sixth field" that `finalize-step-simplify` "carries" — it replaces `workflow`, so the block has five field lines | **fixed** (commit 929ffa4) — reworded to "in place of `workflow`" |
| 3 | sub-agent | `phase-6-finalize/SKILL.md:196-198` (external-step interface contract) describes the input contract without mentioning `requires_prompt_fields` — an internal-consistency gap in the edited file | **fixed** (commit 929ffa4) — added the `requires_prompt_fields` cross-reference |
| 4 | sub-agent | `ext-point-finalize-step.md:3` "Implementations: 25" — is it stale? | **rejected (no change)** — verified correct: the new row is a frontmatter field, not an implementor; count unaffected |
| 5 | sub-agent | `ext-point-dynamic-level-executor.md:159` states categorically "Every dispatch site … dispatches … with the 5-field prompt body" — reads as over-broad given the extension slot | **deferred** — a pre-existing simplification in a doc outside this plan's deliverables (it governs the dynamic-level executor agent, not the finalize dispatch); the change did not newly falsify it. Recorded as residue, not fixed here, to hold scope |
| 6 | sub-agent | D3 "seen red first" is documented in this report, not reproducible from the committed diff | **rejected (no change)** — inherent to a process observation; the permanent `test_orphan_detection_fires_on_an_injected_divergence` / `test_undeclared_detection_fires_on_an_injected_divergence` tests ARE the committed proof the guard fires in both directions, and the sub-agent re-ran them to confirm |

- **PR review — `cuioss-review-bot` (fixed):** flagged a real regex over-fit in the new test — `_FIELD_LINE` used `(?:\[\d*\])?`, matching a digit index (`skills[2]:`) but not a placeholder (`skills[N]:`), so `skills[N]:` silently failed to normalize to `skills`, contradicting the field-key comment. Broadened the bracket class to `[^\]]*` and added a regression test (`test_field_parser_strips_any_bracketed_skills_index`), confirmed red-first on the old pattern. Commit `ab1247d`; replied on the PR thread. No behaviour change on the real docs (they use `skills: []` / `skills[2]:`).
- **CI:** `verify / conclusion` concluded **success** on head `091135e`; re-triggered on `ab1247d` after the review fix.
- **`coderabbitai` / `sourcery-ai`:** posted only rate-limit notices, no findings (see Reviewer participation).

## Reviewer participation

Expected reviewer population derived from configuration — the `author_login` of each `marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc (cross-named by `.github/workflows/pr-agent.yml`): `cuioss-review-bot` (pr-agent.md), `coderabbitai` (coderabbit.md), `sourcery-ai` (sourcery.md). M = 3.

| Reviewer (`author_login`) | Verdict (`reviewed` / `rate-limited` / `silent`) | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Published a "PR Reviewer Guide" review body against the diff with one finding (the `_FIELD_LINE` regex over-fit), now fixed. |
| `coderabbitai` | `rate-limited` | Published only a "Review limit reached — next review available in 29 minutes" notice; no review of this diff. |
| `sourcery-ai` | `rate-limited` | Published only "you have reached your weekly rate limit of 500000 diff characters"; no review of this diff. |

Coverage: **1 of 3** reviewed. **Step 8 shortfall disclosure (fired):** "Review coverage 1 of 3 — `cuioss-review-bot` reviewed (finding fixed); `coderabbitai` rate-limited (window reopens ~29 min); `sourcery-ai` rate-limited (weekly quota)." Per Step 8 condition 4 this is a **disclosure, not a block** — rate limits are routine and outside our control, so the run proceeds to arm on partial coverage having said so.

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** active work was roughly 30–40 min (implementation + gates + PR cycle); the calendar span was ~9 h because the session idled between turns (PR opened 2026-08-12 22:13 UTC; review-fix CI re-triggered 2026-08-13 07:18 UTC). The `verify` CI run itself takes ~12–13 min. Source: PR/commit/CI timestamps.
- **Population:** this single Claude Code cloud session's usage. NOT comparable to a plan-marshall `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary — a boundary this interactive session does not share.

## Contract check (Step 9)

| Step | Verdict | Evidence |
|---|---|---|
| 1 Skills loaded | done | Named under "Skills loaded" — loaded by bundle path (plugin not installed) |
| 2 Branch | done | Harness-assigned `claude/generic-dispatch-template-field-615qbt` on `origin`; kept as-is per the contract; pushed before any edit |
| 3 Plan directory | done | `doc/plans/truthful-signals/260-…/plan.md` exists and opens with the first-instruction block (present on the handed plan — no repair needed) |
| 4 Implement | done | Commits carry the `Co-Authored-By: Claude` trailer; D0–D3 addressed |
| 4 Per-commit gate | done | Every `*.py`-touching commit (`cec4ccd`, `929ffa4`, `ab1247d`) preceded by a clean `./pw quality-gate` (`total_issues: 0`, empty `errors[]`) |
| 4 Pushed | done | No unpushed commit; each commit pushed immediately |
| 5 Build gate | done | Python changed → `./pw verify` path: quality-gate `total_issues: 0` whole-tree + `module-tests plan-marshall` 16262 passed / 1 pre-existing skip / 0 failed |
| 6 Verification sub-agent | done | Findings + dispositions in § Findings (3 fixed, 2 rejected-with-reason, 1 deferred) |
| 7 PR cycle | done | PR #1197; the one review finding (`cuioss-review-bot` regex) fixed and replied; rate-limit notices need no action |
| 8 Merge gate | conditions 1–3 met; auto-merge armed — landing delegated | Condition 1 (required `verify / conclusion` green) enforced by GitHub's auto-merge before it queues; condition 2 (comments handled); condition 3 (this report pushed as the last pre-merge commit); condition 4 shortfall disclosed (1-of-3). Session cannot self-confirm `MERGED` (self-wake tools approval-gated) → arm-and-hand-off per § Cloud session affordances |
| 8 Bridge | done | No status/bookkeeping write outside this plan's own directory; report carries PR number + per-deliverable outcome |
| 9 This check | done | This table |
| 9 What have we learned | done | Below |

**GitHub access path:** the GitHub MCP server (the cloud path). **Branch form:** harness-assigned `claude/*`. **`/sync-plugin-cache`:** not owed — a cloud run neither performs nor owes it (machine-local build step).

## What have we learned (Step 9)

**No contract change proposed.** The run exercised the contract end to end and every gate behaved as written: reading skills by bundle path (plugin absent), the conditional `./pw` build gate, the independent pre-PR sub-agent, the three comment surfaces (the `cuioss-review-bot` finding arrived in the review-body/issue-comment surface, exactly where the contract says to look), and the Step 8 shortfall disclosure on 1-of-3 coverage.

One friction was observed but is **already covered** by the contract, so it is recorded rather than proposed: the self-wake tools (`subscribe_pr_activity`, `send_later`) are approval-gated in this session, and `verify` runs ~13 min — longer than one turn — so the run could not "observe green, then arm" within a single turn. The contract already anticipates this with both **arm-and-hand-off** and **manual read-polling on re-entry** (§ Cloud session affordances / Step 8), and re-entry did occur (wall-clock advanced ~9 h between turns), so the mechanism held. A proposal would need evidence that a genuinely headless, never-re-entered run with gated self-wake *and* long CI cannot complete — which this run (operator-reachable, re-entered) did not produce. Per the "evidence, not speculation" rule, no change is proposed.

## Residue

- **Deferred (finding 5):** `extension-api/standards/ext-point-dynamic-level-executor.md:159` still states categorically that "Every dispatch site … dispatches … with the 5-field prompt body". With the extension slot now formalized, that categorical claim is imprecise (it omits both the `instructions` alternative and step-specific `requires_prompt_fields`). It is a pre-existing simplification in a doc outside this plan's declared surface, so it is left for a follow-up harmonization rather than widened into this change. A candidate for a small truthful-signals follow-up.

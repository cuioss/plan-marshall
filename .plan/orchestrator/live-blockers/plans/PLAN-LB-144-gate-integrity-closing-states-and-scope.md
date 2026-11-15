# PLAN-LB-144: A closing state must be real, a refusal must name a remedy that exists, and the freshness gate reads a Gradle submodule row

epic: live-blockers
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-144-gate-integrity-closing-states-and-scope.md` and is queued as one row file, `queue/PLAN-LB-144.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's word of 2026-11-11 ("aim at larger plans, a smaller number of plans if sensible") from the open defects and
> Watches of the PLAN-LB-130, PLAN-LB-132 and PLAN-LB-133 landing analyses: three gates that accept or refuse the wrong thing, in one
> plan. Grounded against `main` at `9771c0f9e` by a read-only leaf, with the orchestrator re-reading the `superseded_by` rule. Every
> Done-when below fails at `9771c0f9e` unless it is a stated hold. **Sequence this plan after PLAN-LB-142** (see Dependencies). No
> Sonar. No token or measurement work.

## Objective

Three gates are wrong in the same way: each takes a state at face value that it should check, or refuses with a remedy nobody can
carry out. (1) The criteria gate closes a deliverable's criteria on `superseded_by` when the cited number is one of the outline's own,
so a deliverable can supersede itself, two can supersede each other, and a successor that is itself unmet counts. (2) The merge gate
refuses a plan whose findings store holds a legacy row with no pull-request number, even a resolved one, and its remedy text names two
actions that no verb performs; the count of earlier-pull-request findings the read computes is consumed nowhere; and the review-completeness
documents still describe an edit-credit arm that no longer exists. (3) The freshness gate refuses every whole-tree change on a Gradle
ledger that holds a submodule row beside a root row, and a re-run cannot clear it. This plan makes each gate check what it accepts and
name a remedy that exists.

## Deliverables

1. **`superseded_by` names a deliverable that really supersedes this one.**
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality
   - Persona: implementer
   - The rule (`superseded_by_names_deliverable` and `_DELIVERABLE_REFERENCE` in
     `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_criteria_snapshot.py`) rejects the deliverable's OWN
     number and a cycle, and requires the cited deliverable's verdict to be a closing one (`met` or `met_with_residuals`, not
     `not_met`, not itself `superseded`). Its two callers pass what the rule needs: `open_criteria` has the row's number and the whole
     verdict map in scope; the validator's `_grade_row` (`marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/_review_support_validate.py`)
     receives only its own row today, so `validate_functional` passes the verdict rows in.
   - The reference reads the natural spellings the documents invite — `Deliverable 2`, `Deliverable #2`, `Deliverable D2`, a
     backticked or bold `D2`, `(D2)` — and the validator's error says WHY it refused (no deliverable, the deliverable itself, a cycle,
     an unmet or superseded successor, or an unreadable reference), not "names no deliverable of the outline" for all of them.
   - A deliverable retired by operator decision with no successor has a stated route: decide at outline between refusing it (the
     existing `criteria-authorize` route and the dropped-review exemption already close such criteria) and a named verdict value, and
     record the choice in the documents and the PR. This spec's default is to refuse the self-citation and point the reviewer at
     `criteria-authorize`.
   - The two existing fixtures that pin a self-citation as a closing state
     (`test/plan-marshall/phase-6-finalize/test_criteria_gate_completion_d1.py::test_superseded_deliverable_criteria_do_not_block`
     and `test/plan-marshall/phase-6-finalize/test_lb74_criterion_matching_d2.py::test_a_superseded_deliverables_rows_are_not_reported_unmatched`,
     both single-deliverable outlines with `superseded_by: 'D1'` on deliverable 1) are moved to a real successor or to the route
     above, never loosened.
   - `review-rubric.md`, `functional-review.md` (L279, L338, L352), `triage.md` (L68) and the `review_support.py` schema docstring state
     the rule once and agree with the code.

   *Done when:* each of these fails at `9771c0f9e`: deliverable 1 `{verdict: superseded, superseded_by: "D1"}` leaves its criteria open
   and the validator names the self-citation; D1 superseded by D2 and D2 by D1 leaves both open and the validator names the cycle;
   D1 superseded by a D2 graded `not_met` leaves D1's criteria open; `Deliverable 2`, a backticked `D2`, `**D2**` and `(D2)` are
   accepted when deliverable 2 is `met`; the error text for a refused spelling differs from the error text for a refused number.
   These hold at `9771c0f9e` and must keep holding: `D2 - the operator decision` and `deliverable 2` closing when deliverable 2 is
   `met`, `x` and `see d1 notes` still refused, and the validator and `open_criteria` still reading their own populations (the current
   outline's numbers and the frozen snapshot's).

2. **A refusal names a remedy that exists, and a resolved legacy row does not refuse the merge.**
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality
   - Persona: implementer
   - `_scope_findings` (`marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`) reports a legacy
     row (no pull-request number) as unscoped only when it can still decide the merge — a pending row; a resolved or rejected legacy
     row cannot hide a pending finding, so it neither counts toward the store spanning more than one pull request nor blocks.
   - `manage-findings` gains the verb the refusal text has always offered and never had: stamp a pull-request number onto an existing
     `pr-comment` finding's `detail` (name and flags decided at outline; the module is `manage-findings/scripts/_findings_core.py` and
     its CLI, with the library `update_finding_text` as the neighbouring writer). The verb writes the stamp as the first `detail` line
     in the shape the producer writes (`pr_number: N`), refuses a row that already carries a different number, and is the only
     mutation of provenance.
   - The `participation_scope_ambiguous` remedy text (`marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pre_merge_gate.py`,
     `_participation_refusal`) names that verb with its real syntax; a test asserts that a command named in a refusal's remedy parses
     against the live parser.
   - `foreign_stored_findings` (computed in `_read_pr_comment_findings`, returned by `check_completeness`, consumed nowhere) is carried
     into the gate's participation verdict as a disclosure, so an earlier pull request's pending required finding is visible at the
     merge; or the field and its computation are removed. Decide at outline; the Done-when below holds for the disclosure form.
   - `cmd_trigger_bot` (`--pr-number`) has a test that passes the flag end to end through the CLI with findings of two pull requests,
     and that fails when the wiring (`args.pr_number`) is dropped.

   *Done when:* each of these fails at `9771c0f9e`: with a resolved legacy row and findings of two pull requests in the store,
   `review_completeness check` for the current pull request reports no unscoped ids and the merge gate does not refuse with
   `participation_scope_ambiguous`; a pending legacy row is stamped by the new verb and the same `check` then reports it scoped; the
   remedy text of the refusal contains a command that the verb parser accepts; the participation verdict carries
   `foreign_stored_findings` when earlier-pull-request findings exist. These hold at `9771c0f9e` and must keep holding: a PENDING legacy
   row on a two-pull-request store still refuses the merge, not authorizable; a single-pull-request store's legacy rows still join.

3. **The review-completeness documents say what the code does.**
   - Skills: pm-documents:ref-documentation
   - Persona: documenter
   - `bot-participation-contract.md` (the sentence at about L604, "a comment recorded against an earlier commit, unedited, fails the
     test", and the sentence at about L596-597 that argues from an edit as proof) states that an edit credits nothing, as the same
     document does at about L583-584; the comment in `github_pr.py` at about L2160-2163 that describes the next fetch measuring "a fresh
     edit against this credit" is rewritten to the current behaviour (`_reviewed_at_merge_candidate` is a pure SHA comparison).
   - `automatic-review/SKILL.md` Branch 0 and its decision-log line fill and name every unproven required bot, and the
     `refusal_structural` envelope's `display_detail` template and field contract list `unproven_bots` (today the envelope declares
     `unproven_bots[N]` at about L1654 and neither Branch 0 nor the template mentions it).

   *Done when:* a doc test finds no sentence that makes an edit a credit or a precondition of one in the contract, finds Branch 0 naming
   `unproven_bots`, and finds the envelope's `display_detail` template and field contract listing it; each fails at `9771c0f9e`.

4. **The freshness gate reads a Gradle submodule row.**
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality
   - Persona: implementer
   - `parse_row_scope` (`marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py`, the
     `:`-prefixed-payload line at about L849-850) no longer returns `None` for a `:`-prefixed single-task payload token on a Maven or
     Gradle row: the row reads as the readable canonical-unknown inability it read as before PLAN-LB-130, and a multi-token
     `:`-prefixed row keeps reading as a scoped row (narrow) as before. `_unreadable_scope_blocks_whole_tree` therefore stops refusing
     on it. npm keeps its workspace scope for a `:` script name.
   - The two tests that pin the carve-out
     (`test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py::test_a_gradle_submodule_multi_task_row_is_unreadable_not_whole_tree`
     and `::test_a_single_task_gradle_submodule_row_is_also_unreadable`) are replaced by tests of the behaviour above.
   - Decide at outline, with the PLAN-LB-130 spec's text ("the goal-positional tools do not return `None`", and a Gradle submodule
     row "reads as canonical-unknown with no scope and passes a whole-tree change as an inability, predates the reorder, not changed
     here") as the evidence, and record it in the PR.

   *Done when:* each of these fails at `9771c0f9e`: `cross_check_candidates([root build row, :core:test row at one sha], whole-tree)`
   does not return `REASON_SCOPE_UNREADABLE_WHOLE_TREE` and the freshness gate over the same ledger is not stale for that reason; a
   re-run that appends another root `build` row at the same sha leaves the verdict unchanged for the same reason. These hold at
   `9771c0f9e` and must keep holding: an npm `:`-script row keeps its workspace scope; a goal-positional Maven row stays undetermined
   and not narrow; a multi-token Gradle submodule row stays a narrow scoped row.

Split guard: four deliverables, one theme (a gate takes a state at face value). D1 touches the criteria gate, D2 and D3 the
review-completeness and merge gate, D4 the freshness gate; they share no function and can ship in any order, so the lane may ship
them as separate pull requests if one is blocked, which the PR records.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- Every change fails closed: an unreadable reference, an unplaceable row and an unreadable ledger row refuse and never pass.
- A fixture answers a value the real function can give; a gate test drives the real function and not an assembled verdict.
- `functional-review.md` is under the PLAN-LB-139 contract scanners: an edit to it touches prose only, no bash block or placeholder.
- The new `manage-findings` verb adds an executor surface; the PR notes the executor regeneration it owes.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture and are shown red where the Done-when says so.
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: `superseded_by_names_deliverable` checks that the cited number is one of the outline's own and compares it with nothing else (`_criteria_snapshot.py` L1836-1867, read by the orchestrator at L1830-1871)
- OBSERVED: `test_a_superseded_deliverables_rows_are_not_reported_unmatched` carries `'superseded_by': 'D1'` on deliverable 1 (`git diff b09bf3197 4959c5530` of `test_lb74_criterion_matching_d2.py`)
- HYPOTHESIS: `_DELIVERABLE_REFERENCE` is `^\s*(?:[dD]\s?(\d+)|deliverables?\s+#?(\d+))\b` with no ignore-case flag, so `Deliverable 2`, `Deliverable #2`, `Deliverable D2`, backticked `D2`, `**D2**`, `(D2)`, `D#2`, `D-2` are rejected, and `D2`, `d2`, `D 2`, `deliverable 2`, `deliverables #2`, `D2 - …` are accepted (leaf read and ran a copy of the regex on samples, L149)
- HYPOTHESIS: `open_criteria` has the row's number (L1952), the snapshot numbers (L1947) and the whole verdict map (L1946) in scope, and `_grade_row` in `_review_support_validate.py` (L427-461, the superseded branch at L444-450) receives only its own row, `validate_functional` (L587-639) holding the `by_number` map (leaf read)
- HYPOTHESIS: two fixtures pin a self-citation as closing (`test_criteria_gate_completion_d1.py` L384-399 and `test_lb74_criterion_matching_d2.py` L173-183) and `test_superseded_by_names_deliverable_d3.py` has a two-deliverable outline whose successor is never `not_met` or superseded (leaf read)
- OBSERVED: `_scope_findings` (L1139-1208) partitions by the finding's pull-request number and the unscoped list is the legacy rows when the store spans more than one pull request (read by the orchestrator); HYPOTHESIS: it does not filter on resolution and `_read_pr_comment_findings` queries without a resolution filter (L1246), and the only test seeds a pending legacy row (`test_trigger_b_stale_set_from_participation.py` L390), none a resolved one (leaf read)
- OBSERVED: the `participation_scope_ambiguous` refusal is `authorizable: false` and its remedy offers "write the PR stamp into those rows' detail (or remove the rows)" (`pre_merge_gate.py` L1043-1060, L1228-1237, read by the orchestrator)
- HYPOTHESIS: `manage-findings` has no verb that writes `detail` or removes a `pr-comment` row: `resolve` writes `resolution`, `resolution_detail`, the fix-stamp reset and the `responded` marker; `promote` writes `promoted`; `stamp-fix-commit` writes `fix_commit_sha`; `ingest` handles only pending findings that carry `raw_input`; `update_finding_text` (`_findings_core.py` L1370) rewrites `detail` but needs fresh `raw_input`, reopens a resolved row and is not a verb (leaf read)
- OBSERVED: `foreign_stored_findings` occurs in `review_completeness.py` at L1264 and L1619 only (a search over the bundles, test and doc by the leaf and the orchestrator's own search of the bundles)
- HYPOTHESIS: no test passes `--pr-number` to `trigger-bot` end to end; `test_trigger_b_stale_set_from_participation.py` calls `_read_pr_comment_findings` directly (leaf read)
- HYPOTHESIS: the contract sentences at about L604 and L596-597 and the comment at `github_pr.py` L2160-2163 are stale, and `_reviewed_at_merge_candidate` (L1341-1438) is a pure SHA comparison (leaf read; the SHA comparison was re-read by the orchestrator at L1423-1438)
- HYPOTHESIS: `unproven_bots[N]` appears once in the skills (`automatic-review/SKILL.md` L1654) and Branch 0 (L539-563), the `display_detail` template (L1649) and the field contract (L1685-1696) do not name it (leaf read)
- HYPOTHESIS: `parse_row_scope` returns `None` for any `:`-prefixed payload token on a Maven or Gradle row (`_freshness_crosscheck.py` L849-850), `_unreadable_scope_blocks_whole_tree` refuses when any candidate row is unreadable (L1351-1392) and the Gradle discoverer prefixes every submodule task with `:` (`_gradle_cmd_discover.py` L491-498); a root `build` row is canonical-unknown (`build` is not in `CANONICAL_ANALYSES`), so the pair is stale at the head and a re-run cannot clear it (leaf read, traced by reading, not run; both lines were re-read by the orchestrator in an earlier pass)
- HYPOTHESIS: before `549e35374` a lone `:core:test` row read as canonical `:core:test` with no scope and passed as an inability, and the PLAN-LB-130 spec said the goal-positional tools must not return `None` (leaf read of the diff and the spec at L40-42 and L93)
- HYPOTHESIS: the fixture seam `_build_entry(notation=…, args=…)`, `_stub_expected` and `cross_check_candidates([...], '/nonexistent-project-dir', _required())` models Gradle and Maven rows without a Gradle project (leaf read)

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_criteria_snapshot.py` — `superseded_by_names_deliverable`, `_DELIVERABLE_REFERENCE`, `open_criteria` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/_review_support_validate.py` — `_grade_row`, `validate_functional` (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_support.py` — the schema docstring at L56 (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/review-rubric.md`, `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/functional-review.md` and `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` — `_scope_findings`, `_read_pr_comment_findings`, `check_completeness`, `cmd_trigger_bot` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pre_merge_gate.py` — `_check_participation`, `_participation_refusal` (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` and `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/manage-findings.py` — the new stamp verb (D2; verify-at-outline for the exact module split)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md` — the verb's documentation (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md` and `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — the comment at about L2160-2163 only (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` — `parse_row_scope`, `_unreadable_scope_blocks_whole_tree` (D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md` — the notation-scope paragraph PLAN-LB-130 added, only if it states the carve-out (D4)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_superseded_by_names_deliverable_d3.py`, `test/plan-marshall/phase-6-finalize/test_criteria_gate_completion_d1.py`, `test/plan-marshall/phase-6-finalize/test_lb74_criterion_matching_d2.py` and `test/plan-marshall/phase-6-finalize/test_criteria_gate_documentation_d4.py` (D1)
- OBSERVED: `test/plan-marshall/automatic-review/test_trigger_b_stale_set_from_participation.py` and `test/plan-marshall/automatic-review/test_review_completeness_cli.py` (D2)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_pre_merge_gate.py` (D2)
- HYPOTHESIS: `test/plan-marshall/manage-findings/test_manage_findings_cli.py` and `test/plan-marshall/manage-findings/test_findings_update_text.py` — the verb's tests, or a new module beside them (D2)
- HYPOTHESIS: a new doc-contract test module for D3 placed beside the existing review-completeness tests; its path is named at outline
- OBSERVED: `test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py` — the two carve-out tests are replaced (D4)
- HYPOTHESIS: `test/plan-marshall/manage-tasks/_freshness_notation_crosscheck_fixtures.py` and `test/plan-marshall/manage-tasks/_pre_commit_verify_freshness_fixtures.py` — only if the Gradle ledger needs a fixture helper (D4)

## Dependencies and Sequencing

- Depends on: PLAN-LB-142 (running, PR #1959). PLAN-LB-142 edits `review_completeness.py`, `pre_merge_gate.py`, `github_pr.py`, `automatic-review/SKILL.md`, `bot-participation-contract.md`, `branch-cleanup.md`, `test_review_completeness_cli.py` and `test_trigger_b_stale_set_from_participation.py`. It leaves `_scope_findings`, `_read_pr_comment_findings`, the `participation_scope_ambiguous` return and its remedy text, Branch 0 and the structural envelope untouched, but its hunks sit beside them and shift line numbers by about thirty, so name functions and not lines at outline, and start this plan after it ships.
- Overlaps with: PLAN-LB-139 on `functional-review.md` (one file; this plan edits prose at about L279, L338, L352 and no bash block, and PLAN-LB-139 edits it only where its stricter scanner finds a defect). PLAN-LB-137 shares nothing.
- Independent of: PLAN-LB-143 (the OpenCode surface).
- Adjacent to: the `lessons-routing` finding 085 (a quality gate that rewrites files records its success against a tree that is never committed, so the freshness gate cannot clear; the cited lines of `_cmd_pre_commit_verify_freshness.py` `_stale_reason` L261-271 read identically at the head, the recording side is unread). It is a lead, not analysed, and is NOT in this plan; if it confirms it belongs with D4.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-144-gate-integrity-closing-states-and-scope.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

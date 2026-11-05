# PLAN-LB-116: The runbook lane cannot merge past an unhandled review finding or an open Sonar issue, and its landing claims are checkable

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-116-runbook-lane-review-and-sonar-gates.md` and is queued as one row file, `queue/PLAN-LB-116.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's word from a finding pasted by the orchestrator of another epic (`ui-improvements`, project pm-mcp-clients,
> 2026-11-05). The lane text and the lane script were re-read here for the points labelled OBSERVED. The seven landings the finder
> lists were read by the finder from GitHub and are NOT re-read here; they are the motivation, labelled REPORTED, and no Done-when
> depends on them. The finder's Sonar policy is likewise REPORTED.
>
> Ruling check. This is a merge-gate integrity defect (a lane merges with findings open and reports "all handled"), so it is graded
> blocking under the epic's focus rule. It contains no token or measurement work. D3 touches Sonar behaviour of the shared lane for
> projects that have Sonar; it enables nothing in this repository, where Sonar stays off. D3 is separable and is dropped if the
> operator rules the Sonar ruling covers it.

## Objective

The runbook lane decides a merge from prose. Review handling (§ 6 step 5, § 7) has no script; the gate names outside-diff findings
but not the Follow-ups and Nitpick sections of a review body; a thread may be resolved after any reply; the landing facts carry no
thread or review-body numbers, and the Sonar facts are optional, so a landing that says "all handled" has nothing checkable behind
it; `sonar-gate` accepts a dismissal the lane recorded itself; and no step reads the lane's mailbox.

After this plan, a script answers whether a merge is allowed from the review surfaces read on GitHub, the landing carries the numbers
that script produced, a Sonar issue is dismissed only on the operator's selection, the mailbox is read at defined points, and an
evidence claim without an artifact is reported as not evidenced.

## Deliverables

1. **A `review-gate` verb decides the review half of the merge gate, and a thread is resolved only with a reason.**
   - A new `runbook_lane.py` verb `review-gate`, run before every enqueue and wired into § 7 as a gate condition beside `sonar-gate`.
     It reads, through the CI abstraction and not through `gh`, (a) the unresolved review threads with `path:line` and (b) the body of
     every reviewer's review, and parses the body sections: inline comments, Follow-ups, Nitpick comments, Outside-diff comments.
   - It answers `merge_allowed: false` with a named `reason` while any of these holds: an unresolved thread exists; a body finding has
     no disposition (a commit sha or a stated reason) in the progress file; a resolved thread's last bot comment says the concern
     remains; the read is undecidable. An undecidable read is a stop, never a pass.
   - The progress-file format gains one line per disposition (`finding: {reviewer} {section} {id} — {sha|reason}`), and the verb is
     handed the dispositions the way `sonar-gate` is handed its keys.
   - § 6 step 5 states the thread rule: a thread is resolved only after a reply that names a commit or a stated reason
     (`ci pr thread-reply`, then `ci pr resolve-thread`); never to silence it.
   - § 7 states that review-gate `merge_allowed: true` on a read taken after the last push is a gate condition, and that the
     standing review authorization never overrides a `false`.

   *Done when:* a fixture per case shows the verb answering `false` for an open thread, `false` for a body finding with no
   disposition, `false` for a body that holds only Follow-ups or Nitpicks (no thread, no outside-diff section), `false` for a
   resolved thread whose last bot reply says the concern remains, `false` for an undecidable read, and `true` for a PR with none of
   these. Each `false` case is red against a stub that checks only unresolved threads. The § 7 text names the verb as a condition.

2. **The landing carries the review and Sonar numbers, and a landing without them is rejected.**
   - `landing-facts` gains four REQUIRED fields: `unresolved_review_threads`, `review_body_findings_total`,
     `review_body_findings_handled`, `sonar_open_new_issues`. They are written from the outputs of D1 and of `sonar-gate`, never from
     memory. The Sonar field takes `n/a` for a project without Sonar, as the existing Sonar facts do, and `unknown` for a failed read.
   - The orchestrator's landing check rejects a message that lacks any of the four. How an older lane text, which does not write them,
     is treated is decided at outline (a schema-version bump, or a reject with a named remedy); the choice is recorded.
   - The orchestrator's analyze workflow states that these numbers are re-read from GitHub and that a difference is reported as a
     false claim in the landing report.
   - § 8 and the landing template list the four fields; `sonar-facts` is reconciled with the new required Sonar field so there is one
     spelling.

   *Done when:* `landing-check` fails for a message missing each of the four, one fixture per field, and passes for a message with
   all four; the lane text's facts block lists them; the analyze workflow carries the re-read step.

3. **`sonar-gate` no longer accepts a dismissal the lane recorded itself.**
   - `--dismissed-keys` and the recorded-dismissal path of § 6 step 4 and § 7 are removed. A dismissal needs an operator selection
     (question tool) that names the issue key; the gate admits a key only on that selection.
   - The question tool never offers "merge on the recorded evidence" while the open count is above 0 or `review-gate` is `false`.
     An undecidable read stays a stop.
   - The progress-file Sonar line drops the lane-recorded dismissals and records the operator's selection instead.

   *Done when:* `sonar-gate` refuses a lane dismissal (a fixture that supplies the old flag fails with a named error), still admits a
   confirmed 0, still stops on `undecidable` and `unconfigured`, and admits a key only when it is supplied as an operator selection.
   The existing Sonar tests are updated, not deleted.

4. **The lane reads its mailbox at setup, before self-review and before enqueue.**
   - `resolve` publishes the command that reads the lane's delivered mailbox, as it already publishes `inbox_write_command`.
   - The lane text adds the read at the three points, and each delivered item gets a disposition line in the progress file
     (`mailbox: {item} — {done|declined with reason|asked}`).
   - An undisposed item blocks the enqueue.

   *Done when:* `resolve` returns the command (a fixture); the lane text names the three points and the progress-file line; a test
   shows the command is the one the orchestrator's inbox surface documents for reading one plan's mailbox.

5. **An evidence claim needs an artifact.**
   - § 8 states that a browser check cites screenshot files (not only snapshots), and that a mutation run or an end-to-end run cites a
     log path that exists. A claim without an artifact is reported `not evidenced`, and it does not count toward `deliverables_done`.
   - § 1 Evidence ties the rule to the existing `order` grading so there is one place a Done-when is graded.

   *Done when:* the lane text states the rule once, in § 1, and § 8 refers to it; a text test pins that `not evidenced` appears in
   the report section and in the grading rule.

Split guard: five deliverables on one skill. D1 and D2 are the core and depend on each other (D2's numbers come from D1); D3, D4 and
D5 are independently shippable and are the first to split off if the PR grows. All five edit the same two files, so splitting them
into concurrent plans would collide; run any split in sequence.

## Standing Constraints

- **Settle each HYPOTHESIS first.** A refuted claim is dropped from its deliverable, not worked around.
- **Mechanical, like `sonar-gate`.** A gate is a script verb with tests, not added prose. Where a rule stays prose, the Done-when says
  so.
- **Fail closed.** An unreadable review surface, an unparsable body or an undecidable read is a stop, never a pass.
- **CI abstraction only.** No `gh` or `glab` call; the verb composes on the CI layer (the provider modules are not changed except as
  D1's verify-first clause requires).
- **Operator policy is not weakened.** The standing review authorization, the required-reviewer rule and the quota policy keep their
  text; D1 only adds a condition they cannot override.
- **No Sonar in this repository.** `resolve` reports `not_configured` here and stays so. D2 and D3 tests use `configured` fixtures and
  collect no Sonar figure from this repository.
- **No token or measurement work.** `total_tokens` stays as it is.
- **Documentation states the current behaviour.** No comment or doc describes a change.
- **Tests state their purpose**, use the `PLAN_MARSHALL_HOME` fixture, and are shown red where a Done-when says so.
- **Executor regeneration is owed after merge**, because the lane adds a verb; the landing lists it as owed.

## Claim Labels

- OBSERVED: review handling is prose — `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` § 6 step 5 (L664-671) and
  § 7 (L726-739); the only gate script for a review-adjacent condition is `sonar-gate` (L120-136).
- OBSERVED: the gate names only outside-diff findings — § 7 (L726-729).
- OBSERVED: a lane may resolve a thread after a reply and nothing checks the reply — § 6 step 5 (L670-671).
- OBSERVED: the facts block carries no thread or review-body facts and the Sonar facts are optional — § 8 (L788-819).
- OBSERVED: `sonar-gate` admits a count whose every key carries a recorded dismissal — L131-136, § 6 step 4 (L647-656), § 7
  (L716-720).
- OBSERVED: the lane text holds no step that reads a mailbox, and `runbook_lane.py` does not mention one (a content search of the
  source inventory finds the word only in `_cmd_lifecycle.py`, `_orchestrator_inbox.py` and `orchestrator.py`).
- REPORTED (finder, not re-read): seven landings of epic `ui-improvements` merged with CodeRabbit findings or Sonar issues open while
  their landing messages said "all handled" (PLAN-89 PR 305 and 314, PLAN-92 PR 309, PLAN-94 PR 321, PLAN-96 PR 320, PLAN-93 PR 319,
  PLAN-99 PR 325).
- REPORTED (finder): operator policy of that project, 2026-11-05 — zero open new-code Sonar issues at the merge head, fixed in the
  merging PR, no dismissal without the operator's word.
- HYPOTHESIS: the CI layer already exposes the unresolved threads (with path and line) and each review's body, so the verb composes on
  it — confirm/refute at `tools-integration-ci` (`ci pr comments`, `ci pr reviews`) and
  `workflow-integration-github/scripts/_github_pr.py` (verify-at-outline). If a read is missing, adding it to the provider belongs to
  D1 and the GitLab parity is stated.
- HYPOTHESIS: a review body's sections (Follow-ups, Nitpick comments, Outside-diff) are parseable from the body text the CI layer
  returns, for the required reviewers' current format — confirm/refute against the format documented in
  `automatic-review/standards/{bot}.md` (verify-at-outline). A format the parser cannot read is an undecidable read, not a pass.
- HYPOTHESIS: the orchestrator's landing check (`inbox landing-check`) holds the required-field set in
  `plan-orchestrator/scripts/_orchestrator_inbox.py` and versions it by the `schema=landing-facts/1` line — confirm/refute
  (verify-at-outline). It decides how D2 treats an older message.
- HYPOTHESIS: the orchestrator's inbox surface already has a verb that reads one plan's delivered mailbox, which D4's resolve field
  names — confirm/refute at `orchestrator.py inbox --help` (verify-at-outline).
- Verify-first clause (D1): reproduce each failure shape from the finder's list as a fixture before writing the verb. A shape that
  cannot be reproduced from review data is reported, and its Done-when is narrowed in the PR.
- Verify-first clause (D2): read how the landing check treats an unknown key and a missing key today, before choosing the
  compatibility path.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` — § 1, § 6, § 7, § 8, the canonical invocations (D1-D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` — `review-gate`, `sonar-gate`, `sonar-facts`, `resolve` (D1-D4)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane.py` — resolve and new verb fixtures (D1, D4)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane_sonar.py` — the gate tests that change (D3)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane_sonar_landing.py` — the facts tests that change (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py` — the required-field set and the landing check (D2; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md` — the re-read step (D2; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/landing-analysis.md` — the facts list (D2; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` — only if a thread or body read is missing (D1; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/api-contract.md` — only if the CI contract gains a read (D1; verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/plan-orchestrator/` — the landing-check fixtures (D2; verify-at-outline)

## Dependencies and Sequencing

- **Depends on:** none.
- **Overlaps with PLAN-LB-106 (running) and PLAN-LB-108 (staged)** on `runbook-lane/SKILL.md` and `test_runbook_lane.py`, per the
  staging record of the corpus (LB-106 and LB-108 share those two files). **Run this plan after both**, in sequence, and re-read this
  spec's section references at its outline, because those plans edit the same lane text. The disjointness gate decides the pairing
  at emit; it was not run in this draft.
- PLAN-LB-105 (review-gate grading truth) is about the finalize review gate, not the lane; re-read its surface at emit.
- **Adjacent to** (left untouched): the `automatic-review` bot standards, the quota policy text, the finalize review gate.
- **Owed outside this plan, operator-run:** regenerate the executor in every project that runs the lane (a new verb), and a harness
  sync.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-116-runbook-lane-review-and-sonar-gates.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

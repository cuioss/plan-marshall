# PLAN-LB-08: Triage survives a re-run of the check that produced it

epic: live-blockers
workstream: WS-01

> ⛔ **SUPERSEDED — do not launch.** Regrouped on 2026-10-08: PLAN-LB-26 (all deliverables).
> This file is kept as the audit record of the original cut. The successor carries its
> deliverables, claim labels and surface entries unchanged.

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-08-triage-survives-recheck.md` and is queued as one row file,
> `queue/PLAN-LB-08.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

When a checker files a Q-Gate finding that is already in the store with a resolution, the store sets
it back to `pending` and erases the resolution text and timestamp. The match that triggers this is
title plus a hash of the finding's content, so it fires exactly when nothing about the finding has
changed. Re-running a deterministic check — the normal way to confirm a fix — therefore undoes every
triage decision on the findings it re-observes, re-arms the pending-findings gate, and reports
`findings_emitted: 0` while doing so. Six findings an operator had accepted were reverted this way by
one verification re-run, and a later plan was told not to re-run the check at all. This plan makes an
unchanged re-emission leave a recorded resolution alone, keeps reopening as an explicit request for
the one consumer that depends on it, and makes the re-observation visible instead of destructive.
No earlier spec covers this; the evidence is two lessons, `2026-09-02-19-001` and `2026-09-05-17-001`.

## Deliverables

1. **An unchanged re-emission keeps the recorded resolution.** In `add_qgate_finding`, a record matched
   on (title, content discriminator) whose resolution is any non-pending value — `fixed`, `suppressed`,
   `accepted`, `taken_into_account`, `rejected` — keeps `resolution`, `resolution_detail` and
   `resolution_timestamp` exactly as they are. The identity rule does not change: content is already
   part of the key, so a finding whose detail, file or rule changed fails the match and is filed as a
   new pending record, which is the correct handling of "the content changed". The call returns a
   distinct in-store status that names the kept resolution (for example `status: resolved_kept`,
   `resolution: accepted`), and that status joins `QGATE_PERSIST_OK`. The re-observation is recorded
   on the record without touching the resolution (a last-observed timestamp and an observation
   count). Done when: a test parametrized over every member of `VALID_RESOLUTIONS` except `pending`
   (derived from the constant, not listed by hand) resolves a finding, re-adds it with identical
   arguments, and reads back the same resolution, detail and timestamp with the pending count
   unchanged; the test fails at HEAD for all five values.
2. **Reopening is an explicit request, limited to `fixed`, and keeps the history.** The self-review
   loop depends on reopening: it marks a finding `fixed` because a landed change touched the file, and
   relies on the next round's re-detection to return it to `pending` if the defect survived. Keep that
   path as an opt-in on the add call (an API parameter and a `qgate add` flag) that reopens a matched
   record only when its resolution is `fixed` — `fixed` is the one resolution that claims the defect
   is gone, so an identical re-detection contradicts it; the other four record a decision to live
   with the finding and are never reopened by a re-emission. A reopen moves the previous resolution,
   detail and timestamp into a history field instead of setting them to null. The self-review
   re-surface call passes the opt-in; no other producer does. Done when: tests show (a) `fixed` plus
   the opt-in returns `reopened` and the prior resolution is readable from the record, (b) `fixed`
   without the opt-in is kept, (c) `accepted` with the opt-in is kept; and the existing
   self-correction test passes with the opt-in supplied.
3. **A checker says what it re-observed.** `qgate-mechanical-checks` counts a persist as emitted only
   when the status is `success`, so a run that reopened six findings reported zero. After deliverable
   1 it must not go silent in the other direction either: its result reports, alongside
   `findings_emitted`, how many findings it re-observed that already carry a resolution, and how many
   of those are recorded `fixed` — a finding recorded as fixed that the check still detects is worth
   a line in the output even though the store is left alone. Apply the same reporting to every
   caller that folds the persist status into a count. Done when: a test runs the mechanical checks,
   accepts one finding and resolves another `fixed`, re-runs the checks on the unchanged plan, and
   reads `findings_emitted: 0`, a re-observed count of 2 and a still-detected-but-fixed count of 1,
   with both resolutions intact in the store.
4. **The documents describe the behaviour the store has.** `manage-findings/SKILL.md` says `qgate
   add` "deduplicates by title" and that a resolved match is "reactivated to `pending`";
   `q-gate-validation.md` repeats the title-only rule; `jsonl-format.md` has the outcome table;
   `phase-lifecycle.md` lists `reopened` among resolution values; `pre-submission-self-review.md` and
   the `resolve_qgate_findings_by_evidence` docstring say a re-detection reopens. Bring each in line
   with deliverables 1 and 2: the key is (title, content discriminator), a resolved match is kept,
   reopening needs the opt-in and applies to `fixed` only. Done when: a doc test asserts that no
   document under `marketplace/bundles/plan-marshall/skills/` states that `qgate add` reopens a
   resolved finding without naming the opt-in, and that the status values listed in
   `manage-findings/SKILL.md` equal the members of `QGATE_PERSIST_OK`.
5. **The tests that pin reopen-by-default are rewritten.** The tests listed under Claim Labels assert
   `status == 'reopened'` after a plain re-add of a resolved finding. Each becomes either a
   kept-resolution assertion or an opt-in reopen assertion, according to what it was protecting, and
   the status-partition fixture gains the new value. Done when: the manage-findings, manage-tasks and
   phase-5-execute test directories pass, and no test asserts a reopen from a call that does not pass
   the opt-in.

## Claim Labels

- OBSERVED: the Q-Gate dedup key is the pair (title, `content_discriminator`), where the discriminator is a hash over `detail`, `file_path` and `rule`; the match is scoped to one phase's store file — `_content_discriminator` and `_find_by_title_and_discriminator` at `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py:150-164`, `:989-1004`, `:1061-1064`
- OBSERVED: on a match whose resolution is `pending` the call returns `deduplicated` and changes nothing; on a match with ANY other resolution it writes `resolution: 'pending'`, `resolution_detail: None`, `resolution_timestamp: None`, overwrites `iteration` when one is supplied, and returns `reopened` — `_findings_core.py:1065-1090`. The branch tests only `== 'pending'`, so all five other members of `VALID_RESOLUTIONS` (`fixed`, `suppressed`, `accepted`, `taken_into_account`, `rejected`, `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py:145-159`) are reset alike, and nothing of the previous resolution is retained
- OBSERVED: a re-emission whose detail, file or rule differs does not reach that branch; it is appended as a new pending record and the resolved one is untouched — `_findings_core.py:1064`, `:1092-1124`, and the test `test_qgate_same_class_different_subject_not_reopened` at `test/plan-marshall/manage-findings/test_manage_findings.py:224`
- OBSERVED: the plan-scoped store has no such path — `add_finding` always appends a new pending record with a fresh `hash_id` and never reads existing records — `_findings_core.py:479-572`. A re-run of a plan-scoped producer therefore cannot reset a resolution; it can add a duplicate pending record beside the triaged one
- OBSERVED: `qgate-mechanical-checks` returns `1 if status == 'success' else 0` per finding, so a `reopened` persist is counted as nothing emitted — `_emit_finding` at `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_qgate_mechanical.py:104-141`; it supplies no `rule` and `iteration=None`, so its identity is title, detail and file path
- OBSERVED: the reported incident — six `declared_scope_reconciliation` findings resolved `accepted` at the review gate in phase `4-plan` were reverted to `pending` by a verification re-run of `qgate-mechanical-checks`, and a later plan was instructed not to re-run the check after resolving — lessons `2026-09-02-19-001` and `2026-09-05-17-001`, read at `.plan/orchestrator/truthful-signals/lessons/` in the orchestrator ledger (both ids are absent from the global lessons store)
- OBSERVED: the self-review loop relies on reopening a `fixed` record — "the re-surface below re-detects the defect and `add_qgate_finding` REOPENS the record to `pending`" at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:155`, the same statement in the docstring of `resolve_qgate_findings_by_evidence` at `_findings_core.py:1262-1266`, and the re-surface `qgate add` call at `pre-submission-self-review.md:608-613`
- OBSERVED: no script branches on the literal `reopened` or `deduplicated`; the only occurrences in `marketplace/bundles/**/*.py` are the two return sites and the `QGATE_PERSIST_OK` definition — `_findings_core.py:91`, `:1068`, `:1086`. Callers test set membership
- OBSERVED: thirteen script files reference `add_qgate_finding`, `add_qgate_finding_checked` or `qgate add` — `manage-status/scripts/_cmd_classification_validate.py`, `plan-doctor/scripts/plan_doctor.py`, `workflow-integration-sonar/scripts/sonar.py`, `plan-marshall/scripts/_invariants.py`, `phase-5-execute/scripts/scope_creep_check.py`, `workflow-integration-gitlab/scripts/gitlab_pr.py`, `script-shared/scripts/build/_build_shared.py`, `manage-findings/scripts/_findings_store_state.py`, `_findings_core.py`, `manage-findings.py`, `manage-tasks/scripts/_cmd_qgate_mechanical.py`, `workflow-integration-github/scripts/github_pr.py`, `workflow-integration-git/scripts/_cmd_baseline_reconcile.py` (one file-name search at HEAD; some are mentions rather than calls)
- OBSERVED: documents that state the old or a stale rule — "deduplicates by title … returns `status: reopened` (reactivated to `pending`)" at `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md:223-226`; "Same title + resolved → `status: reopened`" at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md:815-817`; the outcome table at `marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md:262-270`; `reopened` listed as a resolution value at `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/phase-lifecycle.md:68`
- OBSERVED: tests that assert reopen from a plain re-add — `test/plan-marshall/manage-findings/test_findings_store_resolve.py:133-160` (resolved `fixed`), `:311-339` (evidence-resolved, the self-correction test); `test/plan-marshall/manage-findings/test_manage_findings_qgate.py:180-221`; `test/plan-marshall/manage-findings/test_findings_store_add.py:323`; the status-partition fixture at `test/plan-marshall/manage-findings/_findings_store_fixtures.py:80-95` with its consumer at `test_findings_store_resolve.py:438-460`; the `benign_status` parametrization at `test/plan-marshall/phase-5-execute/test_scope_creep_check.py:315`
- HYPOTHESIS: a non-zero pending Q-Gate count blocks phase boundaries, so a reopen re-arms a gate an operator had cleared — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` § `_capture_pending_findings_blocking_count` and the boundary table near line 1851 (verify-at-outline)
- HYPOTHESIS: the mechanical checks produce byte-identical title and detail for an unchanged plan, so a re-run matches the existing records instead of minting new ones — confirm/refute by running `qgate-mechanical-checks` twice on a fixture plan and comparing record counts; the incident (records reverted, not duplicated) points this way (verify-at-outline)
- HYPOTHESIS: some producers put volatile text into the title or detail (a line number, a count, a cohort size, a command string), so their re-emissions never match and each re-run adds a fresh pending record beside the resolved one — confirm/refute per producer in the thirteen files above; the self-review test title `defect at src/c.py:5` suggests at least one does (verify-at-outline)
- Verify-first clause: derive the caller population before changing the status set. For every call site of `add_qgate_finding` and `add_qgate_finding_checked`, and every workflow document that reads the `status` of `qgate add`, record whether it only tests in-store membership or also turns the status into a count or a branch. Deliverable 3 applies to the second group; a caller missed here will read the new status as "nothing happened".
- Verify-first clause: confirm that the self-review re-surface is the only consumer that needs a reopen. Search the workflow documents for instructions that depend on a resolved Q-Gate finding returning to `pending` on re-detection. If another consumer exists, it gets the opt-in explicitly; the default does not change back.
- Verify-first clause: decide with the operator whether `fixed` is kept by default (this spec's choice, matching the lessons' directive) or always reopened non-destructively. The case for keeping it: triage records `fixed` when it allocates the fix task, before the fix lands, so a check re-run in between would reopen the finding and a second triage would allocate a second task. The cost: outside self-review, a fix that did not work is reported by deliverable 3's count rather than by a pending finding.

## Expected Surface

- DERIVED — this spec is superseded and claims no surface of its own. The entries it declared are
  recorded in the next section and are now declared by the successor named in the banner above.

## Superseded Surface (record only)

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` — `add_qgate_finding` match branch, `QGATE_PERSIST_OK`, `add_qgate_finding_checked`, the `resolve_qgate_findings_by_evidence` docstring (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/manage-findings.py` — `qgate add` opt-in flag and result fields (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_qgate_mechanical.py` — re-observed counts in the result (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md` — deduplication paragraph and `qgate add` reference (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md` — outcome table and record fields (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md` — Step 6 note (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/phase-lifecycle.md` — resolution-value line (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — the evidence-resolution paragraph and the re-surface `qgate add` call only (D2, D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md` — `qgate-mechanical-checks` result fields (D3) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py` — only if the caller census puts it in the counting group (D3) (verify-at-outline)
- OBSERVED: `test/plan-marshall/manage-findings/test_findings_store_resolve.py` — reopen, self-correction and partition tests (D1, D2, D5)
- OBSERVED: `test/plan-marshall/manage-findings/test_manage_findings_qgate.py` — CLI reopen test (D2, D5)
- OBSERVED: `test/plan-marshall/manage-findings/test_findings_store_add.py` — checked-add reopen test (D5)
- OBSERVED: `test/plan-marshall/manage-findings/_findings_store_fixtures.py` — status-partition fixture (D5)
- OBSERVED: `test/plan-marshall/manage-tasks/test_manage_tasks_qgate_mechanical.py` — re-run regression (D3)
- OBSERVED: `test/plan-marshall/phase-5-execute/test_scope_creep_check.py` — `benign_status` parametrization (D5)
- HYPOTHESIS: `test/plan-marshall/manage-findings/test_qgate_resolution_survives_reemission.py` — new parametrized test for D1 (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-LB-02 (`pre-submission-self-review.md` — that plan reworks the round loop; this one edits the evidence-resolution paragraph and one call. Sequence the two, and whichever lands second re-reads the reopen wording), PLAN-LB-07 (`scope_creep_check.py` and its test — the guard re-emits an unchanged finding on every task, so after this plan an accepted scope-creep finding stays accepted; PLAN-LB-07 rewrites the same test file, so do not run them together), PLAN-LB-06 (`_findings_core.py`, only if that plan adds a task reference to the resolve call), PLAN-LB-09 (reads the pending count this plan stops re-arming; no shared file expected).
- Adjacent to: the self-review step marking a finding `fixed` because a change from the base branch touched its file. That is the evidence rule in `resolve_qgate_findings_by_evidence`, which this plan leaves as it is apart from its docstring.
- Left out on purpose: de-duplication in the plan-scoped store (`add_finding` appends a new pending record on every re-emission, so a build re-run duplicates a triaged failure) — a different function with a different remedy, partly addressed from the workflow side by PLAN-LB-06 deliverable 3; and re-keying producers whose titles or details are volatile — the third hypothesis above measures the problem, and a fix belongs to each producer.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-08-triage-survives-recheck.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

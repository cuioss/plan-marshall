# PLAN-LB-09: The pending-findings gate holds at archive and at merge

epic: live-blockers
workstream: WS-01

> ⛔ **SUPERSEDED — do not launch.** Regrouped on 2026-10-08: PLAN-LB-25 (all deliverables).
> This file is kept as the audit record of the original cut. The successor carries its
> deliverables, claim labels and surface entries unchanged.

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-09-pending-findings-gate.md` and is queued as one row file, `queue/PLAN-LB-09.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

A plan must not merge or be archived while an actionable finding is still `pending`. The check exists, but it leaks in three places. (1) `manage-status archive` refuses with `error: blocking_findings_present` and exits 0, and its one production caller, the `archive-plan` finalize step, has already recorded itself `done` and then logs "Plan archived" without reading the result — so the plan stays in place while the step record and the work log both say it was archived. (2) The archive gate fires only when `--reason` is absent, and the command's own help offers `normal_completion` as an example reason, so following the help disarms the gate on exactly the completion it exists for. (3) Before the merge, the findings check is a `phase_handshake findings-check` call that the `branch-cleanup` step document tells an agent to issue and parse; neither merge verb requires it, so a skipped or misread call still merges, and the later archive refusal then strands a plan whose change is already on the base branch. This plan closes all three. Carries forward code-intelligence-substrate PLAN-CIS-052 D3 (D3(a) as written, D3(b) turned from a proposal into a built deliverable) and PLAN-CIS-054 D5 item 3.

## Deliverables

1. **The archive step reads the refusal.** Amend `phase-6-finalize/standards/archive-plan.md` so the step parses the TOON `status` of `manage-status archive` before anything is logged, with an explicit `error: blocking_findings_present` branch modelled on the foreign-PR gate earlier in the same document: stop, do not emit the "Plan archived" log, do not run the session-store sweep, return the refusal payload (`blocking_count`, `blocking_types`, `per_type`) to the dispatcher, and leave the step without a `done` record. The `mark-step-done` call must still land before the directory move (the move invalidates the live plan path), so the fix is "a refused archive does not leave `done` behind" — either evaluate the gate before the mark (for example through `archive --dry-run` extended to run the findings assertion, or a `findings-check` call), or overwrite the record with `failed` on refusal. Treat `error: phases_unexaminable` and any other `status: error` the same way. Do NOT make the CLI exit non-zero: exit 0 for an operation failure is mandated by `pm-plugin-development:plugin-script-architecture/standards/output-contract.md`. *Done when:* a test drives `manage-status archive` through the script's `main()` with a pending actionable finding and asserts the emitted TOON carries `status: error` / `error: blocking_findings_present` and exit code 0; a doc-contract test asserts that `archive-plan.md` § Archive contains a `blocking_findings_present` branch positioned before the "Plan archived" log line; and a cold reader given only the amended section answers "stop, do not log, do not mark done" to "what do you do when the archive call returns `blocking_findings_present`?".

2. **`--reason normal_completion` no longer skips the gate, and the help stops suggesting it.** Remove `normal_completion` from the `archive --reason` help text in `manage-status.py`. In `cmd_archive`, a reason that asserts completion must not exempt the plan: `--reason normal_completion` takes the same gated path as an absent `--reason` (findings assertion and the `phases_unexaminable` refusal included). Every other reason keeps today's exemption, because an abandonment or cleanup archive must not be stranded by pending findings. When a reason-exempted archive proceeds while actionable findings are pending, the result carries the fact (for example `findings_gate: exempted_by_reason` plus the pending count) and one WARNING decision-log line, so an exemption is visible instead of silent; if the count cannot be evaluated the result says so rather than reporting zero. *Done when:* a test archiving a plan that is open in `6-finalize` with a pending actionable finding and `reason='normal_completion'` gets `blocking_findings_present` and the plan directory is not moved (red before the change); the existing `reason='low_confidence'` test still archives and now asserts the exemption field; `manage-status archive --help` no longer contains `normal_completion`.

3. **The merge cannot be dispatched without the findings predicate having been evaluated.** Replace the instruction-only gate in `branch-cleanup.md` § "Pre-merge blocking-findings store gate" with a mechanical one: one script entry point evaluates the blocking-findings invariant for the plan at `6-finalize` and only on a clean result issues the routed merge (`ci pr safe-merge` when `use_merge_queue == false`, `ci pr merge-queue` when `true`); `branch-cleanup.md` issues that entry point instead of the bare merge verbs. `blocking_findings_present` returns the refusal payload and dispatches nothing; `query_failed` (the count could not be evaluated) also dispatches nothing and routes to the existing § "UNKNOWN disposition — blocked, and never authorizable" path, never to a hard halt that strands the plan and never to a merge. The choice between this wrapper shape and the attestation shape is settled by the verify-first clause below; whichever is built, the two CI merge verbs stay provider-generic unless that clause's reading shows the coupling is already there. *Done when:* a test with a pending actionable finding calls the new entry point and asserts the refusal payload and that the merge runner (injected test seam) was never invoked; a second test does the same for an unevaluable query; a third shows a clean store reaches the merge runner with the routed verb and arguments unchanged; and the closed-dispatch-set test for the step body passes against the amended document.

4. **The documents that describe the two firing sites say what the code does.** Update `plan-marshall/references/phase-handshake.md` (the firing-site table and § `findings-check`), `ref-workflow-architecture/standards/findings-pipeline.md` (the same table and its "armed by a state, not a call" paragraph), `plan-marshall/SKILL.md` (the `pending_findings_blocking_count` rows), `manage-status/SKILL.md` § archive (the reason vocabulary, the gated `normal_completion`, the exemption field) and the docstrings in `_cmd_lifecycle.py` / `_invariants.py` that name the pre-merge gate as the owner of the fail-closed path. *Done when:* no document under `marketplace/bundles/plan-marshall/skills/` describes the pre-merge findings gate as a call the agent "issues and parses" without naming the enforcing entry point, and the canonical-invocation / argparse parity checks for `manage-status` and for the script D3 touches pass.

## Claim Labels

- OBSERVED: `manage-status archive` returns `{status: error, error: blocking_findings_present, blocking_count, blocking_types, per_type}` and moves nothing when an actionable finding is pending — read at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` § `_finalize_findings_refusal` (lines 570-627) and § `cmd_archive` (lines 995-998), at HEAD `6edefac32`
- OBSERVED: the archive step records `--outcome done` in § "Mark Step Complete" (lines 50-60), then issues `manage-status archive` and the `"[STATUS] … Plan archived: {plan_id}"` log with no `status` parse between them (lines 62-72); the same document's foreign-PR gate does parse `status` and has a "STOP. Do NOT mark the step done and do NOT archive" branch (lines 44-48) — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md`
- OBSERVED: the archive gate is entered only when `getattr(args, 'reason', None) is None`; any non-empty reason skips both the `phases_unexaminable` refusal and the findings assertion — read at `_cmd_lifecycle.py` § `cmd_archive` line 975
- OBSERVED: the `--reason` help lists `normal_completion` among its examples — read at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` lines 367-379; a search of `marketplace/bundles/`, `.claude/skills/` and `test/` finds the token nowhere else, so no caller or test depends on it as an exempting reason
- OBSERVED: the pre-merge findings gate is a bash block plus three parse instructions in a step document; it writes no row and leaves no record that it ran — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` § "Pre-merge blocking-findings store gate" (lines 733-750) and `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_handshake_commands.py` § `cmd_findings_check` ("Writes NO handshake row")
- OBSERVED: `findings-check` already fails closed on an unevaluable count (`error: query_failed`), while the archive boundary fails open on the same condition and logs that "the pre-merge findings-check gate owns the fail-closed path" — read at `_handshake_commands.py` § `cmd_findings_check` and `_cmd_lifecycle.py` lines 618-626. The fail-open archive branch is deliberately left as it is by this plan; D3 is what makes its stated owner real
- OBSERVED: the merge is issued in `branch-cleanup` (frontmatter `order: 70`) and the archive in `archive-plan` (`order: 1100`), so today a plan that skipped or misread the pre-merge call merges first and is refused only at archive — read at the two step documents' frontmatter
- OBSERVED: the step body's merge-shaped dispatch set is declared closed with exactly two members, `ci pr safe-merge` and `ci pr merge-queue` — read at `branch-cleanup.md` § "The dispatch set is CLOSED" (lines 1425-1436); a test derives and asserts that set — read at `test/plan-marshall/phase-6-finalize/test_branch_cleanup_merge_queue_routing_routing.py` (module docstring, lines 16-21 and 212)
- OBSERVED: a HEAD-bound authorization record with `grant` / `check` verbs already exists on `manage-status` (`merge-authorization`, stored at `status.metadata.merge_authorizations`) and `branch-cleanup.md` already uses it for consent and review-barrier gaps — read at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_merge_authorization.py` and `branch-cleanup.md` § "Merge-Authorization Roster"
- OBSERVED: the existing archive-refusal test calls `cmd_archive` in-process with a `Namespace`, not the CLI `main()` — read at `test/plan-marshall/manage-status/test_manage_status_transition_archive_archive_refuses.py`
- HYPOTHESIS: no existing test drives `manage-status archive` through `main()` with a pending finding and asserts the emitted TOON and exit code — confirm/refute across `test/plan-marshall/manage-status/test_manage_status_transition_archive*.py` and `test_archive_*.py` (verify-at-outline)
- HYPOTHESIS: the dispatcher's post-dispatch completion guard in `phase-6-finalize/SKILL.md` treats an `archive-plan` return without a terminal record as a halt that a resumed finalize retries, so "no `done` on refusal" needs no dispatcher change — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` § Step 3 (post-dispatch guard, "returned without recording a terminal outcome") (verify-at-outline)
- Verify-first clause: before scoping D3, settle the enforcement shape against the code. Shape A — a single entry point under `phase-6-finalize/scripts/` that runs the findings assertion and then dispatches the routed merge verb; it leaves `ci.py` plan-agnostic but changes the closed dispatch set and the test that pins it. Shape B — `findings-check` persists a HEAD-bound clean attestation (the existing `merge-authorization` record is the candidate store) and the two merge verbs refuse without it; it keeps the dispatch set but couples the provider-generic CI verbs to plan state. Read `tools-integration-ci/scripts/ci.py` and `ci_base.py` (how `--plan-id` reaches `pr safe-merge` / `pr merge-queue`, if at all) and the dispatch-set test, then choose; Shape A is the default when the reading does not decide it. Either shape must send an unevaluable store to the "UNKNOWN disposition" path
- Verify-first clause: before scoping D2, enumerate every caller of `manage-status archive` that passes `--reason` (plan-doctor's `orphan-init-incomplete`, the `low_confidence` remediation, `planning.md` § cleanup) and confirm none relies on `normal_completion`; if one does, it moves to the no-reason form in the same change

## Expected Surface

- DERIVED — this spec is superseded and claims no surface of its own. The entries it declared are
  recorded in the next section and are now declared by the successor named in the banner above.

## Superseded Surface (record only)

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md` — § Mark Step Complete and § Archive: parse the refusal, suppress the log and the `done` record (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` — `cmd_archive` reason handling and exemption reporting (D2); docstrings naming the pre-merge owner (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` — `archive --reason` help text (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` — § archive: reason vocabulary, gated `normal_completion`, exemption field (D2, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — § "Pre-merge blocking-findings store gate", § "Merge PR" and the closed dispatch set (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pre_merge_gate.py` — new entry point under Shape A; not created under Shape B (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — script table row for the new entry point; archive-plan refusal handling at the dispatcher if the second hypothesis is refuted (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_handshake_commands.py` — `cmd_findings_check`, reused by the entry point or extended to persist the attestation (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/phase_handshake.py` — parser change only if the gate is added as a `phase_handshake` verb (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py` — touched only under Shape B (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_merge_authorization.py` — touched only under Shape B, as the attestation store (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` — docstring that names the pre-merge gate (D4); no predicate change
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/references/phase-handshake.md` — firing-site table and § `findings-check` (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/findings-pipeline.md` — firing-site table (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/SKILL.md` — `pending_findings_blocking_count` firing-site rows (D4)
- OBSERVED: `test/plan-marshall/manage-status/test_manage_status_transition_archive_archive_refuses.py` — CLI-surface refusal test (D1)
- OBSERVED: `test/plan-marshall/manage-status/test_manage_status_transition_archive_archive_reason.py` — `normal_completion` gated, exemption field asserted (D2)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_branch_cleanup_merge_queue_routing_routing.py` — closed dispatch set follows the amended step body (D3)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/test_pre_merge_gate.py` — new tests for the entry point: pending finding, unevaluable query, clean store (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/test_archive_plan_refusal_contract.py` — new doc-contract test for the archive step's refusal branch (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-LB-05 (`phase-6-finalize/standards/branch-cleanup.md` — wait procedures in the same step document; different sections, sequence rather than run concurrently); PLAN-LB-10 (`manage-status/scripts/` and `phase-6-finalize/SKILL.md`; LB-10 changes which outcome transitions `mark-step-done` accepts — if it lands first, D1's "overwrite with `failed` on refusal" option needs no `--force`); PLAN-LB-11 and PLAN-LB-02 (`phase-6-finalize/SKILL.md`, different sections); PLAN-LB-04 (`plan-marshall/scripts/_invariants.py` and `_handshake_commands.py` — LB-04 changes invariant logic, this plan changes a docstring and reuses `cmd_findings_check`; sequence).
- Adjacent to: the archive boundary's fail-open branch for an unevaluable query (`blocking is None` in `_finalize_findings_refusal`) stays untouched in either direction; the review-completeness barrier and its two predicates in `branch-cleanup.md` stay untouched; PLAN-LB-08 (`manage-findings/scripts/_findings_core.py`) decides which findings are pending and is not edited here.
- Left out on purpose: closing the `--reason` vocabulary to a fixed set (only `normal_completion` changes behaviour here); a non-zero exit code for a refused archive.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-09-pending-findings-gate.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

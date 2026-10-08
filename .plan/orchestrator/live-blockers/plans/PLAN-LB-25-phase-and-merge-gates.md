# PLAN-LB-25: Phase boundaries and merge gates: the findings gate holds at archive and at merge, merge waits run without sleep, and light-lane plans pass the refine boundary

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-25-phase-and-merge-gates.md` and is queued as one row file, `queue/PLAN-LB-25.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Assembled on 2026-10-08 from PLAN-LB-09, PLAN-LB-05, PLAN-LB-04, which this spec supersedes in whole or in part.
> Deliverables, claim labels, surface entries and the carried sequencing notes are copied from those
> specs unchanged. Each deliverable is tagged with the spec and number it came from; inside carried
> text, "deliverable 2" or "D2" means that number of the SAME source spec, and a plan id below
> PLAN-LB-22 resolves through the id map at the end of § Dependencies and Sequencing.

## Objective

The gates at the two ends of a plan are wrong in opposite directions. At the end, the pending-findings gate leaks: the archive step ignores a refusal, `--reason normal_completion` disarms it, and before the merge it is an instruction an agent may skip; the merge-lock admission wait and the merge-queue landing wait in the same step are paced with a `sleep` the harness refuses. At the start, every light-lane plan is stopped at the `2-refine` capture because nothing on that lane writes `pr_title`. This plan makes the findings gate mechanical at both firing sites, gives both merge waits a bounded script-side form, and gives the light lane its own producer for what the refine boundary demands. The sources are one plan because they share `phase-6-finalize/standards/branch-cleanup.md` and the handshake scripts `plan-marshall/scripts/_handshake_commands.py` and `_invariants.py`.

### Carried from PLAN-LB-09: The pending-findings gate holds at archive and at merge

A plan must not merge or be archived while an actionable finding is still `pending`. The check exists, but it leaks in three places. (1) `manage-status archive` refuses with `error: blocking_findings_present` and exits 0, and its one production caller, the `archive-plan` finalize step, has already recorded itself `done` and then logs "Plan archived" without reading the result — so the plan stays in place while the step record and the work log both say it was archived. (2) The archive gate fires only when `--reason` is absent, and the command's own help offers `normal_completion` as an example reason, so following the help disarms the gate on exactly the completion it exists for. (3) Before the merge, the findings check is a `phase_handshake findings-check` call that the `branch-cleanup` step document tells an agent to issue and parse; neither merge verb requires it, so a skipped or misread call still merges, and the later archive refusal then strands a plan whose change is already on the base branch. This plan closes all three. Carries forward code-intelligence-substrate PLAN-CIS-052 D3 (D3(a) as written, D3(b) turned from a proposal into a built deliverable) and PLAN-CIS-054 D5 item 3.

### Carried from PLAN-LB-05: Wait procedures the harness cannot run

Three finalize waits tell the agent to pace a poll with a standalone foreground `sleep`, which the
harness refuses, so the wait's budget is unreachable: the review-bot completion poll ended after a few
unpaced reads and the step was marked done while the bot was still reviewing; the merge-lock admission
wait and the merge-queue landing wait have the same shape. Two further waits mislead rather than block:
documents disagree on whether an orchestrator-tier build may run in the background, and a CI wait that
lapses while every check is still running is filed as a `ci_timeout` finding and costs a triage round.
This plan moves each short pacing wait into the script that owns the query (a bounded, script-side wait
the caller re-issues), states one runnable rule for long builds, and classifies a lapsed wait on a live
run as "still pending". Carries forward process-compliance PLAN-23 deliverable D4 (D4a, D4b) and the
remedy direction of truthful-signals PLAN-TRUTH-169 (folded recurrences) and PLAN-TRUTH-162 (D3, second
member).

### Carried from PLAN-LB-04: Light-lane plans pass the refine boundary without an override

A plan routed to the light planning lane never runs `phase-2-refine`; the orchestrator closes `2-refine`
itself and then dispatches one collapsed refine+outline envelope. `phase-2-refine` Step 13 is the only place
that writes `status.metadata.pr_title`, and the `pr_title_present` handshake invariant demands that field
from the `2-refine` capture onward. The orchestrator's own `phase_handshake capture --phase 2-refine` on the
light lane therefore refuses with `pr_title_missing` on every light-lane plan, before the envelope is even
dispatched, and the plan stops until someone sets a title by hand or passes `--override --reason`. Give the
light lane its own producer for what the `2-refine` boundary demands, so small plans start without an
operator in the loop. Carries forward truthful-signals PLAN-TRUTH-172 deliverable D2 and process-compliance
PLAN-10 deliverable D1.

## Deliverables

1. **[PLAN-LB-09 D1]** **The archive step reads the refusal.** Amend `phase-6-finalize/standards/archive-plan.md` so the step parses the TOON `status` of `manage-status archive` before anything is logged, with an explicit `error: blocking_findings_present` branch modelled on the foreign-PR gate earlier in the same document: stop, do not emit the "Plan archived" log, do not run the session-store sweep, return the refusal payload (`blocking_count`, `blocking_types`, `per_type`) to the dispatcher, and leave the step without a `done` record. The `mark-step-done` call must still land before the directory move (the move invalidates the live plan path), so the fix is "a refused archive does not leave `done` behind" — either evaluate the gate before the mark (for example through `archive --dry-run` extended to run the findings assertion, or a `findings-check` call), or overwrite the record with `failed` on refusal. Treat `error: phases_unexaminable` and any other `status: error` the same way. Do NOT make the CLI exit non-zero: exit 0 for an operation failure is mandated by `pm-plugin-development:plugin-script-architecture/standards/output-contract.md`. *Done when:* a test drives `manage-status archive` through the script's `main()` with a pending actionable finding and asserts the emitted TOON carries `status: error` / `error: blocking_findings_present` and exit code 0; a doc-contract test asserts that `archive-plan.md` § Archive contains a `blocking_findings_present` branch positioned before the "Plan archived" log line; and a cold reader given only the amended section answers "stop, do not log, do not mark done" to "what do you do when the archive call returns `blocking_findings_present`?".

2. **[PLAN-LB-09 D2]** **`--reason normal_completion` no longer skips the gate, and the help stops suggesting it.** Remove `normal_completion` from the `archive --reason` help text in `manage-status.py`. In `cmd_archive`, a reason that asserts completion must not exempt the plan: `--reason normal_completion` takes the same gated path as an absent `--reason` (findings assertion and the `phases_unexaminable` refusal included). Every other reason keeps today's exemption, because an abandonment or cleanup archive must not be stranded by pending findings. When a reason-exempted archive proceeds while actionable findings are pending, the result carries the fact (for example `findings_gate: exempted_by_reason` plus the pending count) and one WARNING decision-log line, so an exemption is visible instead of silent; if the count cannot be evaluated the result says so rather than reporting zero. *Done when:* a test archiving a plan that is open in `6-finalize` with a pending actionable finding and `reason='normal_completion'` gets `blocking_findings_present` and the plan directory is not moved (red before the change); the existing `reason='low_confidence'` test still archives and now asserts the exemption field; `manage-status archive --help` no longer contains `normal_completion`.

3. **[PLAN-LB-09 D3]** **The merge cannot be dispatched without the findings predicate having been evaluated.** Replace the instruction-only gate in `branch-cleanup.md` § "Pre-merge blocking-findings store gate" with a mechanical one: one script entry point evaluates the blocking-findings invariant for the plan at `6-finalize` and only on a clean result issues the routed merge (`ci pr safe-merge` when `use_merge_queue == false`, `ci pr merge-queue` when `true`); `branch-cleanup.md` issues that entry point instead of the bare merge verbs. `blocking_findings_present` returns the refusal payload and dispatches nothing; `query_failed` (the count could not be evaluated) also dispatches nothing and routes to the existing § "UNKNOWN disposition — blocked, and never authorizable" path, never to a hard halt that strands the plan and never to a merge. The choice between this wrapper shape and the attestation shape is settled by the verify-first clause below; whichever is built, the two CI merge verbs stay provider-generic unless that clause's reading shows the coupling is already there. *Done when:* a test with a pending actionable finding calls the new entry point and asserts the refusal payload and that the merge runner (injected test seam) was never invoked; a second test does the same for an unevaluable query; a third shows a clean store reaches the merge runner with the routed verb and arguments unchanged; and the closed-dispatch-set test for the step body passes against the amended document.

4. **[PLAN-LB-09 D4]** **The documents that describe the two firing sites say what the code does.** Update `plan-marshall/references/phase-handshake.md` (the firing-site table and § `findings-check`), `ref-workflow-architecture/standards/findings-pipeline.md` (the same table and its "armed by a state, not a call" paragraph), `plan-marshall/SKILL.md` (the `pending_findings_blocking_count` rows), `manage-status/SKILL.md` § archive (the reason vocabulary, the gated `normal_completion`, the exemption field) and the docstrings in `_cmd_lifecycle.py` / `_invariants.py` that name the pre-merge gate as the owner of the fail-closed path. *Done when:* no document under `marketplace/bundles/plan-marshall/skills/` describes the pre-merge findings gate as a call the agent "issues and parses" without naming the enforcing entry point, and the canonical-invocation / argparse parity checks for `manage-status` and for the script D3 touches pass.

5. **[PLAN-LB-05 D1]** **The merge-lock admission wait runs without `sleep`.** `branch-cleanup.md` prescribes "a SINGLE
   standalone `sleep {interval}` Bash call" between `merge_lock acquire` polls in both admission loops
   (the early-hold reference and the Pre-Merge Gate loop). Give the wait a script-side form: one call
   that keeps trying for admission for up to a caller-supplied number of seconds (for example
   `--wait-seconds`), returns the same `admission` discriminator as today plus the seconds it waited,
   and is bounded below the harness per-call ceiling so the caller re-issues it until
   `merge_queue_wait_budget_seconds` is spent. The wait must sit between non-waiting acquire attempts,
   never inside the store's read-modify-write section (see the verify-first clause on
   `merge_lock.py`). Rewrite both loops onto it. Done when: a test shows the call returning
   `admitted` as soon as the front holder releases, and returning the blocked discriminator with the
   waited time when the bound lapses; and no `sleep` instruction remains in the two admission loops.

6. **[PLAN-LB-05 D2]** **The merge-queue landing wait runs without `sleep`.** `branch-cleanup.md` § "Landing poll loop"
   paces `ci pr view` reads with a standalone `sleep`. A bounded wait for exactly this condition
   already exists and is unused here: `ci pr wait-for-queue-settle --pr-number N --timeout S
   --interval I`, returning `settle` of `merged` / `closed` / `dequeued` / `timeout`. Rewrite the
   landing loop to re-issue that verb with a `--timeout` below the per-call ceiling until
   `{wait_budget}` is spent, mapping `merged` to the landed branch, `closed` and `dequeued` to the
   Landing-gate failure path, `timeout` with budget left to another call, and an `error` to the
   failure path as today. Keep the `--pr-number` selector and the `merge_hold_budget_seconds` bound.
   Done when: a doc test asserts the landing loop names the wait verb and contains no `sleep`
   instruction, and the four `settle` values each have exactly one documented branch.

7. **[PLAN-LB-04 D1]** **The light lane writes `pr_title` before its `2-refine` capture.** `planning.md`'s light-lane branch
   authors a commit-style PR title from the request (the same shape rules as `phase-2-refine` Step 13:
   at most 72 characters, imperative, `type(scope): summary`) and persists it with `manage-status metadata
   --set --field pr_title` BEFORE the orchestrator-side `phase_handshake capture --phase 2-refine`. The
   capture precedes the envelope dispatch for reasons the document states, so the producer sits on the
   orchestrator side of that boundary; the light-lane envelope may refine the title after it has read the
   code, and `create-pr.md`'s staleness check already re-derives it against the executed scope. The
   invariant itself is not weakened: no lane-conditional skip is added to `_capture_pr_title_present`.
   Done when: an end-to-end handshake test walks the light-lane sequence as `planning.md` documents it
   (transition `2-refine`, boundary stamp, capture) and the capture returns `status: success` with no
   `--override`; the same test with the producer step omitted still returns `error: pr_title_missing`; a
   document-contract test asserts that in the light-lane section the `pr_title` persist appears before the
   `2-refine` capture.

8. **[PLAN-LB-04 D2]** **A capture-source matrix for the `2-refine` boundary, and every row has a light-lane producer.** The
   plan enumerates every value the `2-refine` capture or a later phase requires that `phase-2-refine` Step
   13 produces on the deep lane (`pr_title`, `track`, `scope_estimate`, the module mapping, and whatever
   else the enumeration finds), and records for each which step produces it on the light lane. The matrix
   is published once, in `planning.md` beside the light-lane branch or in the phase-lifecycle standard it
   links, and a test derives the deep-lane producer set from `phase-2-refine/SKILL.md` Step 13 and fails
   when a member has no named light-lane producer. Any member found without one is given a producer in the
   same plan — expected for `track`, which `light-lane.md` says it persists but for which it shows only
   the `scope_estimate` command.
   Done when: the matrix exists, the derived test passes, and a light-lane fixture plan reaches
   `phase-4-plan`'s `manage-references get --field track` read with `track=simple` present.

9. **[PLAN-LB-04 D3]** **The refusal names the producer for the lane the plan is on.** `PrTitleMissing`'s message says
   "phase-2-refine Step 13 must author and persist a commit-style PR title", which sends an operator on a
   light-lane plan to a phase that plan never runs. The `pr_title_missing` payload from both `capture` and
   `verify` names the light-lane producer when `planning_lane` is `light` and the deep-lane one otherwise,
   and gives the exact `manage-status metadata --set --field pr_title` command either way.
   Done when: two tests, one per lane, read the refusal payload and find the lane-correct producer named;
   the `verify` and `capture` payloads stay identical in shape.

10. **[folded in from inbox message `lb-22-finalize-loop-control-014.md`]** **The merge lock stays held across `integrate_into_main`.** `branch-cleanup` acquires the cross-plan merge lock and then calls `integrate_into_main`, which acquires the same lock under the same plan id and releases it on every exit path. Release is not counted, so the lock file is removed at that point and the worktree removal and the pull that follow run without the lock. Make the inner call leave a lock it did not take: either `integrate_into_main` skips its release when its own acquire answered `already_held`, or holds are counted per plan id so that only the outermost release removes the file. *Done when:* a test holds the lock, runs `integrate_into_main`, and asserts the lock is still held afterwards (it fails at HEAD); and the existing reentrant-acquire test stays green.

## Claim Labels

Carried in source order: bullets 1 to 14 from PLAN-LB-09; bullets 15 to 23 from PLAN-LB-05; bullets 24 to 39 from PLAN-LB-04; bullets 40 to 40 added at the regrouping.

- OBSERVED: `manage-status archive` returns `{status: error, error: blocking_findings_present, blocking_count, blocking_types, per_type}` and moves nothing when an actionable finding is pending — read at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` § `_finalize_findings_refusal` (lines 570-627) and § `cmd_archive` (lines 995-998), at HEAD `6edefac32`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _cmd_lifecycle.py _finalize_findings_refusal (570-627) returns the blocking_findings_present dict; cmd_archive (995-998) returns it before the phase-close write and shutil.move
- OBSERVED: the archive step records `--outcome done` in § "Mark Step Complete" (lines 50-60), then issues `manage-status archive` and the `"[STATUS] … Plan archived: {plan_id}"` log with no `status` parse between them (lines 62-72); the same document's foreign-PR gate does parse `status` and has a "STOP. Do NOT mark the step done and do NOT archive" branch (lines 44-48) — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: archive-plan.md: Mark Step Complete (50-60) records --outcome done, Archive (62-72) issues archive then the Plan archived log with no status parse; foreign-PR gate (44-48) parses status and has the STOP branch
- OBSERVED: the archive gate is entered only when `getattr(args, 'reason', None) is None`; any non-empty reason skips both the `phases_unexaminable` refusal and the findings assertion — read at `_cmd_lifecycle.py` § `cmd_archive` line 975
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _cmd_lifecycle.py cmd_archive line 975: `if getattr(args, 'reason', None) is None:` wraps both the phases_unexaminable refusal and the _finalize_findings_refusal call
- OBSERVED: the `--reason` help lists `normal_completion` among its examples — read at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` lines 367-379; a search of `marketplace/bundles/`, `.claude/skills/` and `test/` finds the token nowhere else, so no caller or test depends on it as an exempting reason
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: manage-status.py 367-379 --reason help lists normal_completion; inventory content search (bundles+test, 3496 files) hits only that file. .claude/skills is outside the inventory and was NOT searched
- OBSERVED: the pre-merge findings gate is a bash block plus three parse instructions in a step document; it writes no row and leaves no record that it ran — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` § "Pre-merge blocking-findings store gate" (lines 733-750) and `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_handshake_commands.py` § `cmd_findings_check` ("Writes NO handshake row")
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: branch-cleanup.md 733-750: one findings-check bash block plus three status bullets, 'writes NO handshake row'; _handshake_commands.py cmd_findings_check docstring 'Writes NO handshake row'
- OBSERVED: `findings-check` already fails closed on an unevaluable count (`error: query_failed`), while the archive boundary fails open on the same condition and logs that "the pre-merge findings-check gate owns the fail-closed path" — read at `_handshake_commands.py` § `cmd_findings_check` and `_cmd_lifecycle.py` lines 618-626. The fail-open archive branch is deliberately left as it is by this plan; D3 is what makes its stated owner real
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _handshake_commands.py cmd_findings_check returns error: query_failed on None; _cmd_lifecycle.py 618-626 logs WARNING 'proceeding; the pre-merge findings-check gate owns the fail-closed path' and returns None
- OBSERVED: the merge is issued in `branch-cleanup` (frontmatter `order: 70`) and the archive in `archive-plan` (`order: 1100`), so today a plan that skipped or misread the pre-merge call merges first and is refused only at archive — read at the two step documents' frontmatter
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: Frontmatter read: branch-cleanup.md `order: 70`, archive-plan.md `order: 1100`; merge dispatch lives in branch-cleanup, archive call in archive-plan
- OBSERVED: the step body's merge-shaped dispatch set is declared closed with exactly two members, `ci pr safe-merge` and `ci pr merge-queue` — read at `branch-cleanup.md` § "The dispatch set is CLOSED" (lines 1425-1436); a test derives and asserts that set — read at `test/plan-marshall/phase-6-finalize/test_branch_cleanup_merge_queue_routing_routing.py` (module docstring, lines 16-21 and 212)
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: branch-cleanup.md 1425-1436 'The dispatch set is CLOSED' names exactly safe-merge and merge-queue; test_branch_cleanup_merge_queue_routing_routing.py docstring 16-24 and _EXPECTED_DISPATCH_SET at 212-214
- OBSERVED: a HEAD-bound authorization record with `grant` / `check` verbs already exists on `manage-status` (`merge-authorization`, stored at `status.metadata.merge_authorizations`) and `branch-cleanup.md` already uses it for consent and review-barrier gaps — read at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_merge_authorization.py` and `branch-cleanup.md` § "Merge-Authorization Roster"
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _cmd_merge_authorization.py docstring: grant/check, record in status.metadata.merge_authorizations, HEAD-bound; branch-cleanup.md has a Merge-Authorization Roster heading and grant calls (e.g. line 500 red-ci-override)
- OBSERVED: the existing archive-refusal test calls `cmd_archive` in-process with a `Namespace`, not the CLI `main()` — read at `test/plan-marshall/manage-status/test_manage_status_transition_archive_archive_refuses.py`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: test_manage_status_transition_archive_archive_refuses.py line 38 calls cmd_archive(Namespace(plan_id=..., dry_run=False, reason=None)) in-process; no main() call in the file
- HYPOTHESIS: no existing test drives `manage-status archive` through `main()` with a pending finding and asserts the emitted TOON and exit code — confirm/refute across `test/plan-marshall/manage-status/test_manage_status_transition_archive*.py` and `test_archive_*.py` (verify-at-outline)
- HYPOTHESIS: the dispatcher's post-dispatch completion guard in `phase-6-finalize/SKILL.md` treats an `archive-plan` return without a terminal record as a halt that a resumed finalize retries, so "no `done` on refusal" needs no dispatcher change — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` § Step 3 (post-dispatch guard, "returned without recording a terminal outcome") (verify-at-outline)
- Verify-first clause: before scoping D3, settle the enforcement shape against the code. Shape A — a single entry point under `phase-6-finalize/scripts/` that runs the findings assertion and then dispatches the routed merge verb; it leaves `ci.py` plan-agnostic but changes the closed dispatch set and the test that pins it. Shape B — `findings-check` persists a HEAD-bound clean attestation (the existing `merge-authorization` record is the candidate store) and the two merge verbs refuse without it; it keeps the dispatch set but couples the provider-generic CI verbs to plan state. Read `tools-integration-ci/scripts/ci.py` and `ci_base.py` (how `--plan-id` reaches `pr safe-merge` / `pr merge-queue`, if at all) and the dispatch-set test, then choose; Shape A is the default when the reading does not decide it. Either shape must send an unevaluable store to the "UNKNOWN disposition" path
- Verify-first clause: before scoping D2, enumerate every caller of `manage-status archive` that passes `--reason` (plan-doctor's `orphan-init-incomplete`, the `low_confidence` remediation, `planning.md` § cleanup) and confirm none relies on `normal_completion`; if one does, it moves to the no-reason form in the same change
- OBSERVED: the harness refuses a standalone foreground `sleep`; the documented `sleep 30` in the completion poll was refused on PR #1704 and the step was marked done with the bot still in progress — lesson `2026-10-07-07-007` (read through `manage-lessons get`), and the corpus's own rule at `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/tool-usage-patterns.md` § "No sleep for external waits", which forbids `sleep N` for external waits and says to extend the CI abstraction with a `wait-for-*` verb instead
  - verdict: unverifiable | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: tool-usage-patterns.md 276-324 'No sleep for external waits' holds as cited (forbids sleep N, says extend CI wait-for-*); manage-lessons get 2026-10-07-07-007 returns not_found and PR #1704 is not reachable here
- OBSERVED: the merge-lock admission loops prescribe a standalone `sleep {interval}` between `acquire` polls — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:373`, `:579`, `:594`, `:601`, `:608`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: branch-cleanup.md lines 373, 579, 594, 601 and 608 each prescribe a single standalone `sleep {interval}` Bash call between merge_lock acquire polls; line numbers unchanged at HEAD
- OBSERVED: `merge_lock acquire` takes `--plan-id`, a no-op `--timeout` and `--no-title-token`, and has no waiting form — `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py:2295-2317`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: merge_lock.py main() acquire subcommand (2295-2317) declares --plan-id, --timeout ('Legacy compatibility flag; acquire no longer waits internally') and --no-title-token, nothing else
- OBSERVED: `merge_lock.py` declares "This module has no `time.sleep` and must keep none", reasoning that a wait inside a primitive every finalizing plan contends on would hold a process open — `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py:114-123`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: merge_lock.py module docstring 114-123: 'This module has no time.sleep and must keep none ... a wait embedded here would hold a process open inside a primitive every concurrently-finalizing plan contends on'
- OBSERVED: the landing loop paces `ci pr view` with a standalone `sleep {interval}` — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:1572`, `:1590`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: branch-cleanup.md Landing poll loop: line 1572 paces `ci pr view` polls with a single standalone `sleep {interval}` Bash call, and line 1590 (state == open) repeats it; line numbers unchanged
- OBSERVED: a bounded landing wait exists and `branch-cleanup.md` does not use it — `cmd_pr_wait_for_queue_settle` at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py:2857`, documented at `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/leaf-command-reference.md:46`; its only workflow caller is `plan-orchestrator/workflow/land.md:187`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _github_pr.py:2857 cmd_pr_wait_for_queue_settle; leaf-command-reference.md:46 documents it; land.md:187 calls it; content search finds no wait-for-queue-settle in branch-cleanup.md and no other workflow doc
- OBSERVED: `pr wait-for-queue-settle` does not report `dequeued` for a PR ejected before the wait began; it runs to `timeout`, and `pr queue-state` is the single-read verb for that case — docstring of `cmd_pr_wait_for_queue_settle`, `_github_pr.py:2871-2891`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _github_pr.py cmd_pr_wait_for_queue_settle docstring 2871-2891: an already-ejected PR 'is not reported dequeued by this verb - the wait runs to timeout'; pr queue-state reports it from a single read
- HYPOTHESIS: no other finalize or execute document prescribes a standalone `sleep` outside the rate-window recovery owned by PLAN-LB-18 — confirm/refute with a content search for `sleep` across `marketplace/bundles/plan-marshall/skills/**/*.md` and `.claude/skills/**`, classifying each hit (verify-at-outline)
- Verify-first clause: settle where the merge-lock wait lives before scoping deliverable 1. The module's no-sleep rule is stated for the rate-window claim and the read-modify-write section; the plan must either place the pacing between whole non-waiting `acquire` attempts and amend that paragraph to say so, or put the wait in a separate verb or script. A wait that holds the store lock while sleeping is not acceptable.
- OBSERVED: the invariant applies from `2-refine` onward on every plan and has no lane branch — `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` § `_capture_pr_title_present` (:1683-1713: returns `None` only for `1-init`, otherwise raises `PrTitleMissing` when `metadata.pr_title` is absent or blank), registered with `_always` (:1734) and scoped `blocking_at_every_boundary` (:1852).
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _invariants.py _capture_pr_title_present 1683-1713 returns None only for 1-init, else raises PrTitleMissing, no lane branch; registered with _always at 1734; scope blocking_at_every_boundary at 1852
- OBSERVED: `capture` and `verify` both turn the exception into a boundary refusal — `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_handshake_commands.py:467-474` (`cmd_capture`, `error: pr_title_missing`) and `:597-614` (the same payload on the verify path).
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _handshake_commands.py cmd_capture 467-474 and cmd_verify 598-614 both catch PrTitleMissing and return status error / error pr_title_missing with the same payload shape
- OBSERVED: the only producer of `metadata.pr_title` is `phase-2-refine` Step 13 item 4 — `marketplace/bundles/plan-marshall/skills/phase-2-refine/SKILL.md:268`; a search for `pr_title` in `plan-marshall/workflow/planning.md`, `phase-3-outline/workflow/light-lane.md`, `phase-3-outline/SKILL.md` and `phase-1-init/SKILL.md` returns no hit.
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: phase-2-refine/SKILL.md:268 Step 13 item 4 persists pr_title; inventory content search for pr_title has no hit in planning.md, light-lane.md, phase-3-outline/SKILL.md or phase-1-init/SKILL.md
- OBSERVED: the light lane never dispatches `phase-2-refine`, and the orchestrator runs the `2-refine` transition, boundary stamp and capture itself before dispatching the envelope — `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` light-lane branch step 2 (:243-271; "The light lane never dispatches `phase-2-refine`" at :248; the capture call at :266-269).
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: planning.md light-lane branch step 2 (243-273): 'The light lane never dispatches phase-2-refine' at 248; transition (a), phase-boundary (b) and capture (c, 266-271) are orchestrator-side and pre-dispatch
- OBSERVED: the placement of that capture before the dispatch is deliberate and load-bearing (metrics attribution by spawn timestamp, and the envelope's entry protocol verifies the captured `2-refine` row) — `planning.md:243-246`. A producer inside the envelope would run after the capture it has to satisfy.
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: planning.md 243-246 gives both reasons: manage-metrics enrich attributes by spawn timestamp, and the envelope's Phase Entry Protocol runs phase_handshake verify --phase 2-refine against the captured row
- OBSERVED: the refusal message names only the deep-lane producer — `_invariants.py` § `PrTitleMissing` (:313-332, "phase-2-refine Step 13 must ...").
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _invariants.py PrTitleMissing 313-333: message says 'phase-2-refine Step 13 must author and persist a commit-style PR title via manage-status metadata --set --field pr_title'; no light-lane producer named
- OBSERVED: the capture accepts an override that needs a reason — `_handshake_commands.py:427-431` ("`--override requires --reason`"); `planning.md` does not mention using it on the light lane.
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _handshake_commands.py cmd_capture 427-432 returns missing_reason '--override requires --reason'; planning.md light-lane branch (233-312) names no --override use on its capture call
- OBSERVED: `create-pr` reads `metadata.pr_title` as its only title source and re-derives a stale one against the executed scope — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md:256-292`.
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: create-pr.md Step 3.5 (254-297): reads metadata.pr_title as the deterministic title, forbids improvising, STOPs when empty, and re-derives plus re-persists a stale title against the executed deliverables
- OBSERVED: `phase-2-refine` Step 13 also persists `scope_estimate` and `track` (items 2 and 3, `SKILL.md:266-267`), and `phase-4-plan` reads `track` from references — `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md:687` and `:706-708`.
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: phase-2-refine/SKILL.md 266-267 Step 13 items 2 and 3 persist scope_estimate and track; phase-4-plan/SKILL.md 687 lists track from manage-references get --field track, with the bash read at 706-709
- HYPOTHESIS: the light lane does not persist `track` — `light-lane.md:122` says "Persist the (possibly refined) scope/track to references.json" and the command block that follows sets only `scope_estimate` (:125-126); a search for `--field track` across `phase-1-init/`, `phase-3-outline/` and `plan-marshall/workflow/` returns nothing. Confirm/refute by reading `marketplace/bundles/plan-marshall/skills/phase-3-outline/workflow/light-lane.md` end to end and `manage-status planning-lane route` for a side effect that writes it (verify-at-outline).
- HYPOTHESIS: `planning_lane` is readable from plan status at capture time, so the refusal in Deliverable 3 can pick the lane-correct producer without a new input — confirm at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` § the `planning-lane` verbs (:765-830) and the `metadata` dict `_capture_pr_title_present` receives (verify-at-outline).
- HYPOTHESIS: every light-lane plan hits this refusal — recorded independently by two retired lessons (`2026-09-04-12-001`, which also names `track`, and `2026-09-08-15-001`) and by several plan runs that continued under `--override`; not reproduced here. Reproduce by walking the light-lane sequence against a fixture plan (verify-at-outline).
- Verify-first clause: reproduce `pr_title_missing` on the documented light-lane sequence at HEAD before changing anything. If a producer has appeared since, close Deliverable 1 with that finding and keep Deliverables 2 and 3.
- Verify-first clause: settle at outline whether the orchestrator can author a good-enough title before any code is read. The default is yes, from the request narrative, with the envelope free to overwrite it; if the outline rejects that, the alternative is to move the `2-refine` capture's `pr_title` requirement to the `3-outline` boundary for light-lane plans only — a change to the invariant that needs the operator's agreement, because it is the one option that relaxes a gate.
- Verify-first clause: build the Deliverable 2 matrix from Step 13 and the invariant registry before scoping; whatever it finds beyond `pr_title` and `track` is in scope only if it stops a light-lane plan at a boundary. Anything else is reported, not fixed here.
- OBSERVED: both halves of this defect recurred on 2026-10-07 in the plan run for issue #1697 and stopped it twice: the light-lane pre-dispatch `phase_handshake capture` failed `pr_title_missing`, and the pre-dispatch `2-refine` closure was refused by the `refine_bare_transition` guard; the run stopped both times instead of inventing a title or passing an override — read at `.plan/archived-orchestrators/process-compliance/inbox/archive/issue-1697/issue-1697-002.md` and `issue-1697-003.md`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: issue-1697-002.md (refine_bare_transition refusal, run stopped) and issue-1697-003.md (capture pr_title_missing, no override, no invented title) hold as cited; created stamps are 2026-10-05 and 2026-10-06, not 10-07
- Verify-first clause: `plan-marshall/workflow/planning.md` and `phase-3-outline/workflow/light-lane.md` both changed between `6edefac32`, the HEAD the PLAN-LB-04 claims were read at, and `64b573110`. Re-read both files and re-derive every line reference before scoping the PLAN-LB-04 deliverables; if a `pr_title` producer has appeared on the light lane, the first of them closes with that finding.
- HYPOTHESIS: folded in on 2026-10-08 from inbox message `lb-22-finalize-loop-control-014.md`: a second `merge_lock acquire` by the same plan id returns `already_held`, release is idempotent and not counted, and `integrate_into_main` releases on every exit path including success, so the first release to run is the inner one. Recorded call order in that plan: acquire 20:05:12, worktree removal 20:43:52, switch-and-pull 20:43:57, documented release 20:44:02. Reported from two source readings and a script log; the inner call itself was not in the log window read — confirm/refute at `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/integrate_into_main.py` § `_release_and` and `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py` § the module docstring bullet on reentrant acquire (verify-at-outline)
- Verify-first clause: the folded-in lock deliverable and PLAN-LB-05 D1 both change how the merge lock is held during branch cleanup. Design them together at outline: the waiting form of `acquire` must not change what a reentrant acquire returns, and the release rule must hold whether the outer acquire waited or not.

## Expected Surface

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
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — admission loops and landing loop (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py` — bounded admission wait and the no-sleep paragraph (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/SKILL.md` — `merge_lock acquire` canonical invocation (D1)
- OBSERVED: `test/plan-marshall/manage-locks/test_manage_locks_merge_lock_cli.py` — admission-wait tests (D1)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/test_no_standalone_sleep_in_wait_docs.py` — new doc test for D1–D4 wording (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` — light-lane branch: `pr_title` producer before the capture, capture-source matrix
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-3-outline/workflow/light-lane.md` — `track` persist, optional title refinement after the bounded read
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` — `PrTitleMissing` message; `_capture_pr_title_present` only if the alternative in the verify-first clause is chosen
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_handshake_commands.py` — lane-correct `pr_title_missing` payload on `capture` and `verify`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-2-refine/SKILL.md` — Step 13, read as the deep-lane producer list; edited only to point at the matrix
- OBSERVED: `test/plan-marshall/plan-marshall/test_lifecycle_handshake_e2e.py` — light-lane walk through the `2-refine` capture
- OBSERVED: `test/plan-marshall/plan-marshall/test_phase_handshake_capture_verify.py` — per-lane refusal payload beside the existing `pr_title_present` cases
- OBSERVED: `test/plan-marshall/plan-marshall/test_invariants.py` — `PrTitleMissing` message cases
- HYPOTHESIS: `test/plan-marshall/plan-marshall/test_light_lane_capture_sources.py` — new derived test for the capture-source matrix (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/integrate_into_main.py` — release only a lock this call took (folded-in lock deliverable) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-locks/test_manage_locks_merge_lock_reentrant_acquire.py` — release-side case beside the existing acquire test (folded-in lock deliverable) (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none. If PLAN-LB-22 has landed, the "overwrite the record with `failed` on refusal" option of PLAN-LB-09 D1 needs no `--force`; if it has not, evaluate the gate before the mark instead.
- The PLAN-LB-04 deliverables are the separable part of this plan: they share only the two handshake scripts with the rest. If the outline finds the plan too wide, split them back out as their own plan.
- Overlaps with: PLAN-LB-22, PLAN-LB-24 and PLAN-LB-27 on `phase-6-finalize/SKILL.md`; PLAN-LB-22 on `manage-status/scripts/manage-status.py`, `_cmd_lifecycle.py` and `manage-status/SKILL.md`; PLAN-LB-24 on `manage-locks/scripts/merge_lock.py` and `manage-locks/SKILL.md`. Sequence against those three.
- May run together with: PLAN-LB-23, PLAN-LB-26 and PLAN-LB-28, and with PLAN-LB-14, PLAN-LB-29, PLAN-LB-30 and PLAN-LB-31.

### Carried sequencing notes

Copied from the source specs. They use the plan ids from before the regrouping; resolve each through
the id map below. Where a carried "Depends on" or "Overlaps with" line disagrees with the bullets above,
the bullets above are current.

From PLAN-LB-09:

- Depends on: none.
- Overlaps with: PLAN-LB-05 (`phase-6-finalize/standards/branch-cleanup.md` — wait procedures in the same step document; different sections, sequence rather than run concurrently); PLAN-LB-10 (`manage-status/scripts/` and `phase-6-finalize/SKILL.md`; LB-10 changes which outcome transitions `mark-step-done` accepts — if it lands first, D1's "overwrite with `failed` on refusal" option needs no `--force`); PLAN-LB-11 and PLAN-LB-02 (`phase-6-finalize/SKILL.md`, different sections); PLAN-LB-04 (`plan-marshall/scripts/_invariants.py` and `_handshake_commands.py` — LB-04 changes invariant logic, this plan changes a docstring and reuses `cmd_findings_check`; sequence).
- Adjacent to: the archive boundary's fail-open branch for an unevaluable query (`blocking is None` in `_finalize_findings_refusal`) stays untouched in either direction; the review-completeness barrier and its two predicates in `branch-cleanup.md` stay untouched; PLAN-LB-08 (`manage-findings/scripts/_findings_core.py`) decides which findings are pending and is not edited here.
- Left out on purpose: closing the `--reason` vocabulary to a fixed set (only `normal_completion` changes behaviour here); a non-zero exit code for a refused archive.

From PLAN-LB-05:

- Overlaps with: PLAN-LB-18 (`automatic-review/SKILL.md`, `manage-locks/SKILL.md`, `merge_lock.py`). Scope boundary: the CodeRabbit rate-window wait — the up-to-an-hour quota wait in `automatic-review/SKILL.md` § "Rate-limit refusal recovery", its Branch 3 poll, the `poll-delay` jitter sleep and the `rate-window` verbs — belongs to PLAN-LB-18. This plan owns the short pacing sleeps (admission, landing, completion poll) and the timeout classification, and must not edit the recovery section. Sequence the two; do not run them together.
- Overlaps with: PLAN-LB-09 (`branch-cleanup.md`, pre-merge check), PLAN-LB-10 (`ci_verify.py`), PLAN-LB-06 (`execution.md`), PLAN-LB-12 (`script-shared/scripts/build/*`), PLAN-LB-19 (`github_pr.py`), PLAN-LB-02 and PLAN-LB-11 (`phase-6-finalize/SKILL.md`). Each touches a different section; sequence rather than pair.
- Adjacent to: the landing gate's inability to tell an ejected PR from a queued one. `pr wait-for-queue-settle` runs to `timeout` for a PR ejected before the wait began; this plan keeps the existing budget-exhaustion path for that case and does not add the `pr queue-state` pre-read.

From PLAN-LB-04:

- Depends on: none.
- Overlaps with: none. No other `live-blockers` plan edits `planning.md`, `light-lane.md`, `_invariants.py` or `_handshake_commands.py`.
- Adjacent to: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` and `triage.md` in the same `workflow/` directory, edited by PLAN-LB-05 and PLAN-LB-06; and `manage-status/scripts/`, edited by PLAN-LB-09 and PLAN-LB-10. This plan reads `planning_lane` from status and adds no `manage-status` verb.
- Left out on purpose: truthful-signals PLAN-TRUTH-172 D0, D1 and D3 (the finalize branch table's missing arrival path for an empty-population verdict, and the transition-time phase-array invariant). They are unrelated to the light-lane stop.
- Left out on purpose: process-compliance PLAN-10 D2–D5. D2 (the mailbox probe mis-reading `source_id`) is already fixed by PR #1685. D3 (file input for `recipe-match` / `aspect-classify`), D4 (`phase_steps_complete` reading non-step bullets) and D5 (handshake-capture backfill) do not stop a light-lane plan at the refine boundary.
- Left out on purpose: whether a large scope should be routed to the light lane at all (the lane router's sizing). This plan fixes the documented lane; it does not change who enters it.

### Id map

| Id before the regrouping | Now |
|---|---|
| PLAN-LB-01 | PLAN-LB-23 (all deliverables) |
| PLAN-LB-02 | PLAN-LB-22 (all deliverables) |
| PLAN-LB-03 | PLAN-LB-28 (all deliverables) |
| PLAN-LB-04 | PLAN-LB-25 (all deliverables) |
| PLAN-LB-05 | D1 and D2 to PLAN-LB-25; D3 to PLAN-LB-24; D4 to PLAN-LB-26; D5 to PLAN-LB-22 |
| PLAN-LB-06 | PLAN-LB-26 (all deliverables) |
| PLAN-LB-07 | PLAN-LB-27 (all deliverables) |
| PLAN-LB-08 | PLAN-LB-26 (all deliverables) |
| PLAN-LB-09 | PLAN-LB-25 (all deliverables) |
| PLAN-LB-10 | PLAN-LB-22 (all deliverables) |
| PLAN-LB-11 | PLAN-LB-27 (all deliverables) |
| PLAN-LB-12 | PLAN-LB-23 (all deliverables) |
| PLAN-LB-13 | PLAN-LB-28 (all deliverables) |
| PLAN-LB-14 | unchanged, still PLAN-LB-14 |
| PLAN-LB-15 | PLAN-LB-29 (all deliverables) |
| PLAN-LB-16 | PLAN-LB-30 (all deliverables) |
| PLAN-LB-17 | PLAN-LB-29 (all deliverables) |
| PLAN-LB-18 | PLAN-LB-24 (all deliverables) |
| PLAN-LB-19 | PLAN-LB-24 (all deliverables) |
| PLAN-LB-20 | D1 to D3 to PLAN-LB-30; D4 and D5 to PLAN-LB-31 |
| PLAN-LB-21 | PLAN-LB-31 (all deliverables) |

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-25-phase-and-merge-gates.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

<!-- GENERATED FILE — never hand-edit. Rendered from this epic's ledger (status.json, resume_anchor.md, queue/*.json) by `orchestrator regenerate-view --slug live-blockers`. On a merge conflict in this file, do not merge it by hand: merge the source files, run `orchestrator regenerate-view --slug live-blockers`, and `git add` the result. -->

# Queue view: Live Blockers

## START HERE

**Resume anchor**: RESUME HERE (rewritten 2026-11-11 after PLAN-LB-133, 134 and 138 were analysed): after a restart run /plan-orchestrator resume slug=live-blockers, read START HERE, then epic.md Decisions (top entries 2026-11-11, 2026-11-10 and 2026-11-09), Queue annotations and Open Defects. FIRST in a new session: the registry pins plan-marshall 0.1.2090 but the executor is 0.1.2076 (restart-check registry_parity indeterminate), so the operator regenerates the executor via /marshall-steward before the first script call (PLAN-LB-132 added --pr-number to two review_completeness verbs and PLAN-LB-138 added corpus verbs, so the regeneration is owed again), then run land status. LEDGER LAND STATE: this analysis was followed by a land on the operator word of 2026-11-11; read land status first and finish the cycle if it is not closed; PR 1958 (merge commit eacede16c1f) was the previous land. FOCUS RULE (operator, 2026-10-23): high and blocking only; token usage and measurement out of scope (a landing that is incomplete on total_tokens alone is no defect); CodeRabbit quota refusal = wait; Sourcery optional; the Claude PreToolUse hook is deliberately unset (never remind). SONAR (operator, 2026-10-28, REFINED 2026-11-07): not enabled for THIS project and ignored here; where Sonar is configured for a project and for the plan the runbook lane must not miss any Sonar finding. SETTLED 2026-10-25: with at least one valid CodeRabbit review and the quota blocking the re-review the standing authorization applies; never ask. OPERATOR RULE 2026-11-10 (PLAN-LB-142): after one successful CodeRabbit review and ALL handling of its result there is no further review, the review is done and the plan or lane merges; per pull request, per bot behind a registry flag, CodeRabbit only. STATE: queue 142 rows. Analysed and reconciled: PLAN-LB-105 to PLAN-LB-134, PLAN-LB-138 and PLAN-LB-141 (detail in landings/PLAN-LB-NN.md; pull requests 1946 to 1949, 1951 to 1954 and 1957; no blocker). OPEN DEFECTS, ALL REPORTED TO THE OPERATOR AND NONE STAGED: the PLAN-LB-130 Gradle carve-out (outside this repository), and four majors from this pass: the OpenCode emitter expresses no tool restriction for any agent and its effect rests on the unread OpenCode 2 base policy (the cheap check is opencode api GET /api/agent for the execution-context-reader agent), the shadow refusal that aborts permission fix protect-path and breaks ensure idempotence, a scalar bash or permission value replaced by an empty map in six writers (pre-existing, OpenCode 1 shape), and superseded_by accepting a deliverable own number and a cycle. IN FLIGHT one: PLAN-LB-142 (a handled CodeRabbit review is the review; spec plans/PLAN-LB-142-coderabbit-review-done-after-handling.md; four deliverables implemented, self-review clear; PR 1959 OPEN on head 88b6d2695, NO CodeRabbit review because it refused on quota twice, the lane is parked on that wait; its branch predates the merges of PLAN-LB-133, 134 and 138 so the base must be merged in; its row stays running with pr and plan id stamped; its first message is LEFT LIVE on purpose so the lane can amend it at the merge, do not archive it until its merged landing arrives). Three of four slots are free. HELD BACK, ALL ADMISSIBLE NOW (all lane runbook, declarative surfaces): PLAN-LB-135 (opencode bridge and sweep; its spec should be re-read against the shadow refusal and the emitter change first; PLAN-LB-136 then 140 follow it one at a time on opencode_runtime.py), PLAN-LB-137 (shares orchestrator.py and test_runbook_lane.py with the now shipped PLAN-LB-138), PLAN-LB-139 (shares functional-review.md with the now shipped PLAN-LB-133). Nothing is emitted: the operator said not to emit yet. Rows 41, 46, 51, 69, 75, 83, 84 and 89 are superseded and row 87 is retired (specs stay as the record). INBOX, NOT DRAINED: three lessons-routing finding messages, all graded high by the sender and none a landing: 084 (the merge gate never proves the calling plan holds the merge mutex and a not-live holder blocks admission; the sender asks to check PLAN-LB-100 and PLAN-LB-120 first), 085 (a rewriting quality gate records success against a tree that is never committed so the freshness gate cannot clear; manage-tasks _cmd_pre_commit_verify_freshness.py), 086 (a build-server submit with no plan selector builds the main checkout and reports success; build-server-client build_server.py), and the PLAN-LB-142 mid-flight message, which stays live. OPERATOR DECISIONS OPEN: stage fix plans for the four majors above and the PLAN-LB-130 Gradle carve-out (my recommendation: one small plan for the OpenCode 1 map-shape class and the shadow refusal, one for superseded_by, and a read of the base policy before anything on the emitter); which of PLAN-LB-135, 137 and 139 to emit; drain the three lessons-routing findings. OPERATOR-RUN, OWED: a FULL SESSION RESTART is done only if the operator did it; executor regeneration in every project via /marshall-steward (PLAN-LB-124 D2 changed the executor template; PLAN-LB-108 build_queue.py arguments; PLAN-LB-116 added the review-gate verb; PLAN-LB-132 added --pr-number; PLAN-LB-138 added corpus verbs; read the executor version first); the harness sync for the PLAN-LB-128 to PLAN-LB-134 and PLAN-LB-138 bundle edits; a live routed check in the move-back window; the second machine install and executor regeneration; the Dependabot ecosystem switch from pip to uv (chore PR by the operator); a systemd-tmpfiles janitor that reaps guard-node and executor-mappings directories in the system temp directory, and optionally a larger tmpfs nr_inodes limit (PLAN-LB-141 scopes both out because they live outside the repository; a live count of guard-node directories after the next suite run is the cheap confirmation of its fix). uv.lock: whether the earlier stale types-pyyaml line is still stale was not re-checked. BRANCH STATE: five remote branches with no PR stay for a diff check (chore/config-manifest-test-reduction-02, chore/lessons-routing-inbox-drain-2026-09-24, claude/cleanup-af76zf, claude/derived-set-closure-integrity-g7n8x2, claude/dispatch-audit-surfaces-rc5j18). NEXT ACTION: wait for the operator's word on emission and on the fix plans; run /plan-orchestrator analyze when PLAN-LB-142 files its merged landing (fetch origin first, read the parent of a squash commit with git and name it in the leaf prompt, read the changed path list with git rather than guessing a path, carry each narrative claim into the leaf prompt one by one, re-read every point marked checked at file:line, stamp status, pr, landing and plan id in one pass after the analysis); when a slot is wanted run /plan-orchestrator next. For the PLAN-LB-142 landing carry the PLAN-LB-132 Watch items (the scope-ambiguous refusal with no verb to clear it, foreign_stored_findings consumed nowhere, stale contract prose about an edit arm), check that the flag is read through one accessor, and check how it behaves for a PR whose only review is on a head the base has since moved past. When writing a spec, one persona per Persona line and no annotation on a Skills line. WORKING RULES LEARNED: before I say a fix is possible, run the existing check that might already answer it; a reproduction must say WHICH copy of the script ran; a pre-fix statement in a spec must be checked by running the full verb; read the lane own self-review state first on a landing; a lane statement of no surface drift is checked against the diff, never accepted; a lane statement of an evidence boundary is a layer-1 lead: check whether the shipped test uses the live shape or an assembled one; a test fixture that answers a value the real verb cannot give hides the defect: read the verb the fixture stands in for; a migration that reports a change must be checked for whether the command saves it; a leaf report is a lead: re-read every point it marks checked at its file:line before it is written into a landing and say which were not re-read, and a leaf can name the wrong test or miscount: check it; a merge commit that came through the merge queue is a squash with one parent: read the parent with git and name it in the leaf prompt; a leaf prompt carries a landing narrative claims one by one; a leaf can grade a finding above what the Done-when supports, so re-grade it; a lane claim that a capture is verbatim in a fixtures file is checked by a content search for the comment id; a report key that no document or consumer names is not reported to the operator; stamp status, pr, landing and plan id in one pass after the analysis; a leaf finding is checked against the lane own table before it is recorded (a point the lane already marks green at base is no overclaim); a message filed after the drain enumerated is the next pass, not part of this one; a landing message whose merge_state is open is a mid-flight report, not a ship: confirm the PR and the head, keep the row running, write no landing report, stamp pr and plan id, and DO NOT ARCHIVE the message (an archived message cannot be amended, so the lane files a second one); a lane that declines a review finding because of a remedy is checked for whether the remedy exists (PLAN-LB-132 inline-2); the land ejection gate stops on found indeterminate whatever requeue says, and a stale open land PR is closed (on the operator word) so the workflow treats it as unbound; a plan slug must be unique in the queue (queue add-row refuses a duplicate of a superseded row, so rename the spec file first); grounding leaves return data and the orchestrator writes every spec; spec claims ground against HEAD before staging, and a directory or glob claim in a spec widens the overlap against running plans, so name files where they are known; one command per Bash call, no env assignment or semicolon prefix; never redirect command output anywhere, not even to dev null, and verify an update-field write by reading the view; verify a manage-logging write with manage-logging read; before replacing the anchor read the current value; a spec with no queue row makes every staged comparison indeterminate; a combined plan above the six-deliverable guard needs the operator word and a recorded split order; corpus verdicts, corpus cross-check and corpus surfaces can exceed 1MB: read the persisted file with a read-only grep for the rows; Grep and Glob may be unavailable, then use a read-only grep or ls through Bash and say so; fetch origin before reading the log because a lane can merge while the orchestrator works; the Decisions section of epic.md is newest first with one heading; the manage-status read verb takes no --field; a measured acceptance on a shared system temp directory must use a run-private TMPDIR because concurrent plans hold live directories there; do not guess a path in a leaf prompt, read the changed path list with git first. EXECUTOR: the main executor carries GENERATED_FOR any; if executor_target_mismatch shows here, report it as a LB-94 defect. COUNT-CLAIM SCAN: the epic count-claim scan reads a bare number placed directly before a status word such as shipped, landed or retired as a count, so in anchor prose write the row or the plan by name and never put a bare number straight before such a word (the queue holds 142 rows).
**Phase**: orchestrating
**Running**:
- PLAN-LB-142 (WS-05) — plan=rb-lb-142-coderabbit-review-done-after-handling — PR 1959
**Queue** (staged, in order):
1. PLAN-LB-135 (WS-04)
2. PLAN-LB-136 (WS-04)
3. PLAN-LB-139 (WS-05)
4. PLAN-LB-140 (WS-04)
5. PLAN-LB-137 (WS-04)
- PLAN-LB-14 (WS-03) — plan=lb-14-launch-gate-scope — PR 1715 — landing=landings/PLAN-LB-14.md — status: shipped
- PLAN-LB-01 (WS-01) — status: superseded
- PLAN-LB-04 (WS-01) — status: superseded
- PLAN-LB-07 (WS-01) — status: superseded
- PLAN-LB-03 (WS-01) — status: superseded
- PLAN-LB-02 (WS-01) — status: superseded
- PLAN-LB-08 (WS-01) — status: superseded
- PLAN-LB-06 (WS-01) — status: superseded
- PLAN-LB-05 (WS-01) — status: superseded
- PLAN-LB-09 (WS-01) — status: superseded
- PLAN-LB-10 (WS-01) — status: superseded
- PLAN-LB-11 (WS-01) — status: superseded
- PLAN-LB-12 (WS-02) — status: superseded
- PLAN-LB-13 (WS-02) — status: superseded
- PLAN-LB-15 (WS-04) — status: superseded
- PLAN-LB-17 (WS-04) — status: superseded
- PLAN-LB-16 (WS-04) — status: superseded
- PLAN-LB-18 (WS-05) — status: superseded
- PLAN-LB-19 (WS-05) — status: superseded
- PLAN-LB-21 (WS-05) — status: superseded
- PLAN-LB-20 (WS-05) — status: superseded
- PLAN-LB-22 (WS-01) — plan=lb-22-finalize-loop-control — PR 1718 — landing=landings/PLAN-LB-22.md — status: shipped
- PLAN-LB-23 (WS-02) — plan=lb-23-verify-builds — PR 1729 — landing=landings/PLAN-LB-23.md — status: shipped
- PLAN-LB-24 (WS-05) — plan=lb-24-review-step — PR 1742 — landing=landings/PLAN-LB-24.md — status: shipped
- PLAN-LB-25 (WS-01) — plan=lb-25-phase-and-merge-gates — PR 1751 — landing=landings/PLAN-LB-25.md — status: shipped
- PLAN-LB-26 (WS-01) — plan=lb-26-execute-loop-triage — PR 1769 — landing=landings/PLAN-LB-26.md — status: shipped
- PLAN-LB-27 (WS-01) — status: retired
- PLAN-LB-28 (WS-02) — plan=lb-28-java-consumer-repos — PR 1750 — landing=landings/PLAN-LB-28.md — status: shipped
- PLAN-LB-29 (WS-04) — plan=plan-lb-29-harness-sync — PR 1724 — landing=landings/PLAN-LB-29.md — status: shipped
- PLAN-LB-30 (WS-04) — plan=plan-lb-30-org-ci-release — PR 1722 — landing=landings/PLAN-LB-30.md — status: shipped
- PLAN-LB-31 (WS-05) — plan=plan-lb-31-in-house-reviewer — PR 1771 — landing=landings/PLAN-LB-31.md — status: shipped
- PLAN-LB-32 (WS-01) — plan=lb-32-head-dependent-step-refire — PR 1741 — landing=landings/PLAN-LB-32.md — status: shipped
- PLAN-LB-33 (WS-02) — plan=lb-33-leaf-test-scope-and-executor — PR 1745 — landing=landings/PLAN-LB-33.md — status: shipped
- PLAN-LB-34 (WS-01) — status: superseded
- PLAN-LB-35 (WS-01) — status: superseded
- PLAN-LB-36 (WS-01) — status: superseded
- PLAN-LB-37 (WS-01) — plan=lb-37-functional-review — PR 1759 — landing=landings/PLAN-LB-37.md — status: shipped
- PLAN-LB-38 (WS-05) — plan=plan-lb-38-review-gate-and-empty-scope — PR 1752 — landing=landings/PLAN-LB-38.md — status: shipped
- PLAN-LB-39 (WS-04) — plan=antigravity-execution-fidelity — PR 1768 — landing=landings/PLAN-LB-39.md — status: shipped
- PLAN-LB-40 (WS-04) — plan=steward-upgrade-integrity — PR 1774 — landing=landings/PLAN-LB-40.md — status: shipped
- PLAN-LB-41 (WS-05) — status: superseded
- PLAN-LB-42 (WS-01) — plan=plan-lb-42-outline-qgate-integrity — PR 1773 — landing=landings/PLAN-LB-42.md — status: shipped
- PLAN-LB-43 (WS-04) — plan=lb-43-consumer-leaf-workflow-resolution — PR 1851 — landing=landings/PLAN-LB-43.md — status: shipped
- PLAN-LB-44 (WS-01) — plan=lb-44-red-ci-triage-route — PR 1848 — landing=landings/PLAN-LB-44.md — status: shipped
- PLAN-LB-45 (WS-04) — plan=oc-lb-45-runtime-stamp — PR 1802 — landing=landings/PLAN-LB-45.md — status: shipped
- PLAN-LB-46 (WS-05) — status: superseded
- PLAN-LB-47 (WS-01) — plan=lb-26-regression-fixes — PR 1778 — landing=landings/PLAN-LB-47.md — status: shipped
- PLAN-LB-48 (WS-04) — plan=lb-48-opencode-2-compat — PR 1830 — landing=landings/PLAN-LB-48.md — status: shipped
- PLAN-LB-49 (WS-04) — plan=lb-49-opencode-measurement — PR 1833 — landing=landings/PLAN-LB-49.md — status: shipped
- PLAN-LB-50 (WS-04) — plan=implement-plan-lb-50-lb-39-regression-fixes — PR 1777 — landing=landings/PLAN-LB-50.md — status: shipped
- PLAN-LB-51 (WS-04) — status: superseded
- PLAN-LB-52 (WS-01) — plan=oc-lb-52-criteria-and-gate-integrity — PR 1806 — landing=landings/PLAN-LB-52.md — status: shipped
- PLAN-LB-53 (WS-01) — plan=lb-53-halt-conflict-and-phase-time — PR 1857 — landing=landings/PLAN-LB-53.md — status: shipped
- PLAN-LB-54 (WS-01) — plan=oc-lb-54-lb-42-completion — PR 1788 — landing=landings/PLAN-LB-54.md — status: shipped
- PLAN-LB-55 (WS-01) — plan=lb-55-gate-head-truth — PR 1856 — landing=landings/PLAN-LB-55.md — status: shipped
- PLAN-LB-56 (WS-04) — plan=implement-plan-lb-56-session-boundary-enforcement — PR 1781 — landing=landings/PLAN-LB-56.md — status: shipped
- PLAN-LB-57 (WS-05) — status: retired
- PLAN-LB-58 (WS-01) — plan=rb-lb-58-verification-truth — PR 1866 — landing=landings/PLAN-LB-58.md — status: shipped
- PLAN-LB-59 (WS-01) — plan=lb-59-skill-and-adr-resolution — PR 1821 — landing=landings/PLAN-LB-59.md — status: shipped
- PLAN-LB-60 (WS-04) — plan=implement-plan-lb-60-lb-40-regression-fixes — PR 1782 — landing=landings/PLAN-LB-60.md — status: shipped
- PLAN-LB-61 (WS-01) — plan=oc-lb-61-lb-47-hotfix — PR 1787 — landing=landings/PLAN-LB-61.md — status: shipped
- PLAN-LB-62 (WS-04) — plan=oc-lb-62-lb-56-completion — PR 1790 — landing=landings/PLAN-LB-62.md — status: shipped
- PLAN-LB-63 (WS-04) — plan=oc-lb-63-lb-60-completion — PR 1795 — landing=landings/PLAN-LB-63.md — status: shipped
- PLAN-LB-64 (WS-04) — plan=oc-lb-64-lb-50-completion — PR 1794 — landing=landings/PLAN-LB-64.md — status: shipped
- PLAN-LB-65 (WS-04) — plan=oc-lb-65-lb-62-completion — PR 1800 — landing=landings/PLAN-LB-65.md — status: shipped
- PLAN-LB-66 (WS-04) — plan=oc-lb-66-runbook-lane-skill — PR 1808 — landing=landings/PLAN-LB-66.md — status: shipped
- PLAN-LB-67 (WS-04) — plan=lb-67-standing-review-authorization — PR 1813 — landing=landings/PLAN-LB-67.md — status: shipped
- PLAN-LB-68 (WS-04) — plan=lb-68-lb-65-completion — PR 1814 — landing=landings/PLAN-LB-68.md — status: shipped
- PLAN-LB-69 (WS-04) — status: superseded
- PLAN-LB-70 (WS-03) — plan=lb-70-lb-52-completion — PR 1815 — landing=landings/PLAN-LB-70.md — status: shipped
- PLAN-LB-71 (WS-04) — plan=lb-71-lb-67-completion — PR 1817 — landing=landings/PLAN-LB-71.md — status: shipped
- PLAN-LB-72 (WS-04) — plan=lb-72-lb-71-completion — PR 1819 — landing=landings/PLAN-LB-72.md — status: shipped
- PLAN-LB-73 (WS-04) — plan=lb-73-lb-72-completion — PR 1843 — landing=landings/PLAN-LB-73.md — status: shipped
- PLAN-LB-74 (WS-03) — plan=lb-74-lb-70-integrity-fixes — PR 1822 — landing=landings/PLAN-LB-74.md — status: shipped
- PLAN-LB-75 (WS-03) — status: superseded
- PLAN-LB-76 (WS-01) — plan=lb-76-lb-59-completion — PR 1824 — landing=landings/PLAN-LB-76.md — status: shipped
- PLAN-LB-77 (WS-03) — plan=lb-77-lb-74-completion — PR 1826 — landing=landings/PLAN-LB-77.md — status: shipped
- PLAN-LB-78 (WS-04) — plan=lb-78-runbook-lane-build-resolution — PR 1834 — landing=landings/PLAN-LB-78.md — status: shipped
- PLAN-LB-79 (WS-04) — plan=lb-79-lb-68-completion — PR 1835 — landing=landings/PLAN-LB-79.md — status: shipped
- PLAN-LB-80 (WS-01) — plan=lb-80-lb-76-completion — PR 1854 — landing=landings/PLAN-LB-80.md — status: shipped
- PLAN-LB-81 (WS-04) — plan=lb-81-lb-45-completion — PR 1832 — landing=landings/PLAN-LB-81.md — status: shipped
- PLAN-LB-82 (WS-03) — plan=rb-lb-82-lb-77-completion — PR 1864 — landing=landings/PLAN-LB-82.md — status: shipped
- PLAN-LB-83 (WS-04) — status: superseded
- PLAN-LB-84 (WS-04) — status: superseded
- PLAN-LB-85 (WS-04) — plan=lb-85-lane-sonar-issues — PR 1839 — landing=landings/PLAN-LB-85.md — status: shipped
- PLAN-LB-86 (WS-04) — plan=lb-86-lb-49-completion — PR 1841 — landing=landings/PLAN-LB-86.md — status: shipped
- PLAN-LB-87 (WS-04) — status: retired
- PLAN-LB-88 (WS-04) — plan=lb-88-lb-79-completion — PR 1840 — landing=landings/PLAN-LB-88.md — status: shipped
- PLAN-LB-89 (WS-04) — status: superseded
- PLAN-LB-90 (WS-04) — plan=lb-90-lane-reads-ledger-spec — PR 1859 — landing=landings/PLAN-LB-90.md — status: shipped
- PLAN-LB-91 (WS-01) — plan=lb-91-change-ledger-rewrite — PR 1847 — landing=landings/PLAN-LB-91.md — status: shipped
- PLAN-LB-92 (WS-04) — plan=lb-92-lane-worktree-executor — PR 1850 — landing=landings/PLAN-LB-92.md — status: shipped
- PLAN-LB-93 (WS-04) — plan=rb-lb-93-flat-install-generator-bootstrap — PR 1874 — landing=landings/PLAN-LB-93.md — status: shipped
- PLAN-LB-94 (WS-04) — plan=rb-lb-94-one-executor-all-harnesses — PR 1861 — landing=landings/PLAN-LB-94.md — status: shipped
- PLAN-LB-95 (WS-04) — plan=rb-lb-95-executor-pythonpath-own-version — PR 1865 — landing=landings/PLAN-LB-95.md — status: shipped
- PLAN-LB-96 (WS-04) — plan=rb-lb-96-flat-install-bundles-root — PR 1868 — landing=landings/PLAN-LB-96.md — status: shipped
- PLAN-LB-97 (WS-04) — plan=rb-lb-97-flat-install-skill-resolution — PR 1872 — landing=landings/PLAN-LB-97.md — status: shipped
- PLAN-LB-98 (WS-04) — plan=rb-lb-98-flat-install-executor-skew — PR 1876 — landing=landings/PLAN-LB-98.md — status: shipped
- PLAN-LB-99 (WS-04) — plan=rb-lb-99-source-checkout-executor-skew — PR 1878 — landing=landings/PLAN-LB-99.md — status: shipped
- PLAN-LB-100 (WS-01) — plan=rb-lb-100-merge-path-truth — PR 1883 — landing=landings/PLAN-LB-100.md — status: shipped
- PLAN-LB-101 (WS-01) — plan=rb-lb-101-review-policy-barrier — PR 1890 — landing=landings/PLAN-LB-101.md — status: shipped
- PLAN-LB-102 (WS-04) — plan=rb-lb-102-ledger-first-spec-read — PR 1882 — landing=landings/PLAN-LB-102.md — status: shipped
- PLAN-LB-103 (WS-04) — plan=rb-lb-103-tests-use-fixtures-not-live-config — PR 1894 — landing=landings/PLAN-LB-103.md — status: shipped
- PLAN-LB-104 (WS-04) — plan=rb-lb-104-routed-build-project-dir — PR 1893 — landing=landings/PLAN-LB-104.md — status: shipped
- PLAN-LB-106 (WS-05) — plan=lb-106-review-bot-evidence-truth — PR 1912 — landing=landings/PLAN-LB-106.md — status: shipped
- PLAN-LB-105 (WS-03) — plan=lb-105-review-gate-grading-truth — PR 1913 — landing=landings/PLAN-LB-105.md — status: shipped
- PLAN-LB-107 (WS-01) — plan=lb-107-finalize-gate-waiver-and-step-truth — PR 1920 — landing=landings/PLAN-LB-107.md — status: shipped
- PLAN-LB-108 (WS-04) — plan=lb-108-build-daemon-worktree-serialisation — PR 1922 — landing=landings/PLAN-LB-108.md — status: shipped
- PLAN-LB-109 (WS-01) — plan=lb-109-execute-prescribed-yield-not-error — PR 1911 — landing=landings/PLAN-LB-109.md — status: shipped
- PLAN-LB-110 (WS-02) — plan=lb-110-maven-consumer-test-truth — PR 1921 — landing=landings/PLAN-LB-110.md — status: shipped
- PLAN-LB-111 (WS-03) — plan=lb-111-three-layer-landing-analysis — PR 1908 — landing=landings/PLAN-LB-111.md — status: shipped
- PLAN-LB-112 (WS-04) — plan=lb-112-routed-build-worktree-fault-truth — PR 1910 — landing=landings/PLAN-LB-112.md — status: shipped
- PLAN-LB-113 (WS-02) — plan=lb-113-domain-content-gaps — PR 1909 — landing=landings/PLAN-LB-113.md — status: shipped
- PLAN-LB-114 (WS-03) — plan=lb-114-landing-and-link-checker-corrections — PR 1915 — landing=landings/PLAN-LB-114.md — status: shipped
- PLAN-LB-115 (WS-04) — plan=rb-lb-115-routed-build-carry-and-fault-corrections — PR 1932 — landing=landings/PLAN-LB-115.md — status: shipped
- PLAN-LB-116 (WS-04) — plan=rb-lb-116-runbook-lane-review-and-sonar-gates — PR 1940 — landing=landings/PLAN-LB-116.md — status: shipped
- PLAN-LB-117 (WS-01) — plan=lb-117-execute-handback-fix — PR 1918 — landing=landings/PLAN-LB-117.md — status: shipped
- PLAN-LB-118 (WS-03) — plan=lb-118-review-gate-grading-fix — PR 1919 — landing=landings/PLAN-LB-118.md — status: shipped
- PLAN-LB-119 (WS-03) — plan=lb-119-review-gate-truth-fixes — PR 1925 — landing=landings/PLAN-LB-119.md — status: shipped
- PLAN-LB-120 (WS-01) — plan=lb-120-merge-and-push-gate-truth-fixes — PR 1923 — landing=landings/PLAN-LB-120.md — status: shipped
- PLAN-LB-121 (WS-02) — plan=lb-121-maven-consumer-gate-truth-fixes — PR 1929 — landing=landings/PLAN-LB-121.md — status: shipped
- PLAN-LB-122 (WS-03) — plan=lb-122-landing-analysis-and-link-checker-gaps — PR 1931 — landing=landings/PLAN-LB-122.md — status: shipped
- PLAN-LB-123 (WS-01) — plan=lb-123-execute-handback-and-manifest-gaps — PR 1933 — landing=landings/PLAN-LB-123.md — status: shipped
- PLAN-LB-127 (WS-03) — plan=rb-lb-127-coderabbit-registry-summary-concerns-and-file-limit — PR 1941 — landing=landings/PLAN-LB-127.md — status: shipped
- PLAN-LB-125 (WS-03) — plan=rb-lb-125-review-gate-jvm-acceptance-and-triage-exemption — PR 1939 — landing=landings/PLAN-LB-125.md — status: shipped
- PLAN-LB-126 (WS-01) — plan=rb-lb-126-finalize-commit-rows-and-foreign-branch — PR 1942 — landing=landings/PLAN-LB-126.md — status: shipped
- PLAN-LB-124 (WS-01) — plan=rb-lb-124-push-gate-and-maven-guard-truth-fixes — PR 1938 — landing=landings/PLAN-LB-124.md — status: shipped
- PLAN-LB-128 (WS-03) — plan=rb-lb-128-coderabbit-roster-save-and-summary-concern — PR 1946 — landing=landings/PLAN-LB-128.md — status: shipped
- PLAN-LB-129 (WS-04) — plan=rb-lb-129-review-gate-thread-and-count-truth — PR 1947 — landing=landings/PLAN-LB-129.md — status: shipped
- PLAN-LB-130 (WS-01) — plan=rb-lb-130-freshness-gate-scope-by-notation — PR 1949 — landing=landings/PLAN-LB-130.md — status: shipped
- PLAN-LB-131 (WS-01) — plan=rb-lb-131-foreign-gate-default-branch — PR 1948 — landing=landings/PLAN-LB-131.md — status: shipped
- PLAN-LB-133 (WS-03) — plan=rb-lb-133-criteria-gate-reach — PR 1953 — landing=landings/PLAN-LB-133.md — status: shipped
- PLAN-LB-134 (WS-04) — plan=rb-lb-134-opencode-permission-writer — PR 1954 — landing=landings/PLAN-LB-134.md — status: shipped
- PLAN-LB-138 (WS-04) — plan=rb-lb-138-orchestrator-staging-and-landing-read-hygiene — PR 1957 — landing=landings/PLAN-LB-138.md — status: shipped
- PLAN-LB-132 (WS-05) — plan=rb-lb-132-refusal-escalation-and-pr-scoped-staleness — PR 1952 — landing=landings/PLAN-LB-132.md — status: shipped
- PLAN-LB-141 (WS-04) — plan=rb-lb-141-tempdir-teardown-in-test-harnesses — PR 1951 — landing=landings/PLAN-LB-141.md — status: shipped

## Ordered Queue

| # | Plan | Workstream | Status | Surface (expected) | Lane |
|---|------|------------|--------|--------------------|------|
| 1 | PLAN-LB-135 | WS-04 | staged | doc/developer/opencode.adoc; marketplace/bundles/plan-marshall-opencode/skills/target-rules/SKILL.md; marketplace/bundles/plan-marshall-opencode/skills/target-rules/standards/opencode-rules.md; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py; marketplace/bundles/plan-marshall/skills/script-shared/scripts/target_context.py; test/marketplace/targets/opencode/test_opencode2_dispatch_shape.py; test/plan-marshall/platform-runtime/test_opencode_runtime.py; test/plan-marshall/script-shared/test_target_context.py | runbook |
| 2 | PLAN-LB-136 | WS-04 | staged | marketplace/bundles/plan-marshall-antigravity/skills/target-rules/standards/antigravity-rules.md; marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_rules.py; marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/antigravity_runtime.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py; test/plan-marshall/manage-execution-manifest/_manage_execution_manifest_manage_execution_manifest_compose_fixtures.py; test/plan-marshall/manage-execution-manifest/test_manage_execution_manifest_compose_request_project_gates.py; test/plan-marshall/platform-runtime/test_antigravity_runtime.py; test/plan-marshall/platform-runtime/test_opencode_runtime.py | runbook |
| 3 | PLAN-LB-139 | WS-05 | staged | marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/code-review.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/functional-review.md; test/plan-marshall/phase-6-finalize/_review_contract_scanners.py; test/plan-marshall/phase-6-finalize/test_code_review_contract.py; test/plan-marshall/phase-6-finalize/test_functional_review_contract.py; test/plan-marshall/phase-6-finalize/test_review_contract_scanners.py | runbook |
| 4 | PLAN-LB-140 | WS-04 | staged | marketplace/bundles/plan-marshall/skills/execute-task/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/operations.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/antigravity_runtime.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py; marketplace/targets/antigravity/emitter.py; marketplace/targets/antigravity/mapping.json; marketplace/targets/body_transform_engine.py; test/marketplace/targets/antigravity/test_body_transforms.py; test/marketplace/targets/antigravity/test_emitter.py; test/marketplace/targets/antigravity/test_emitter_skill_dir.py; test/marketplace/targets/test_body_transform_engine.py; test/plan-marshall/platform-runtime/test_antigravity_runtime.py; test/plan-marshall/platform-runtime/test_platform_runtime_router.py | runbook |
| 5 | PLAN-LB-137 | WS-04 | staged | marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md; marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py; marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py; test/conftest.py; test/plan-marshall/plan-orchestrator/test_orchestrator_restart_check_registry_parity.py; test/plan-marshall/runbook-lane/test_runbook_lane.py; test/plan-marshall/tools-integration-ci/test_ci_base_primitives.py; test/plan-marshall/tools-script-executor/test_generate_executor_behavior.py; test/plan-marshall/tools-script-executor/test_generate_executor_bootstrap.py; test/plan-marshall/workflow-integration-github/test_github_ops_errors.py; test/plan-marshall/workflow-integration-gitlab/test_gitlab_ops_errors.py | runbook |
| 6 | PLAN-LB-142 | WS-05 | running | doc/concepts/planning-workflow.adoc; doc/user/configuration.adoc; doc/user/getting-started.adoc; doc/user/parallelism-and-locking.adoc; marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md; marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pre_merge_gate.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup-rereview.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md; marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py; marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/pr-review-operations.md; marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py; marketplace/bundles/plan-marshall/skills/workflow-pr-doctor/standards/automated-review-lifecycle.md; test/plan-marshall/automatic-review/; test/plan-marshall/automatic-review/test_review_completeness_state.py; test/plan-marshall/automatic-review/test_review_policy_defaults.py; test/plan-marshall/automatic-review/test_trigger_b_stale_set_from_participation.py; test/plan-marshall/manage-config/test_config_defaults.py; test/plan-marshall/phase-6-finalize/; test/plan-marshall/phase-6-finalize/test_pre_merge_gate.py; test/plan-marshall/runbook-lane/test_runbook_lane.py; test/plan-marshall/runbook-lane/test_runbook_lane_review_gate.py; test/plan-marshall/test_bot_participation_contract_*; test/plan-marshall/test_branch_cleanup_merge_queue_routing_*.py; test/plan-marshall/test_review_merge_invocation_contract_*.py; test/plan-marshall/workflow-integration-github/; test/plan-marshall/workflow-integration-github/test_re_review_strategy_fresh_review.py | runbook |

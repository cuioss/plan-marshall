# History: Post-Run Quality Analysis

slug: post-run-quality
closed: 2026-10-07

> Frozen record of the epic at close. `epic.md`, the queue rows, the specs, the landings, the
> inbox and the logs stay in this tree untouched; this file is the summary a later reader
> starts from. Close freezes and never deletes.

## Closing rationale

Closed by operator instruction on 2026-10-07. plan-marshall's workflow machinery is being
rewritten as plan-marshall-mcp, which supersedes most of this epic's staged and parked work.
The work that still matters for plan-marshall itself — defects that block or mislead a normal
run today, and high-priority work on things the rewrite does not replace — was cut into the
successor epic `live-blockers` (`.plan/orchestrator/live-blockers/`). Everything else was
left where it stood.

## Vision as pursued

**Everything this project does to judge a run AFTER it has finished — and whether any of it is
trustworthy.** Fourteen distinct aspects exist today across four surfaces: the 16-aspect
`plan-retrospective`, the 24-check archived-plan corpus auditor, the metrics/findings measurement
substrate, and the lessons corpus that is supposed to close the loop. They were built one at a time, and
the evidence says the seams between them leak: a producer publishes a confident figure over a population
it never read; an auditor's own census cannot census itself; a process lesson reaches the governing
contract **1 time in 5**; and an obligation a finished plan left behind has no owner once that plan is
archived.

Too large for one plan because the aspects share no owner and no vocabulary: each is a separate producer,
several were built by different plans in different epics, and the fixes span `plan-retrospective`,
`.claude/skills/audit-archived-plan-retrospectives`, `manage-metrics`, `manage-findings` and
`manage-lessons`. **Done at the epic level** means: every post-run producer states the population it read,
every post-run verdict is derivable rather than self-reported, the loop from finding → lesson → governing
contract is measured rather than assumed, and an obligation that outlives its plan has a tracker.

⭐ **The epic's own instrument is the honest zero.** Every deliverable here is judged by one question:
after it lands, can a reader tell *"checked and clean"* from *"never looked"*? That is ADR-019 applied to
the machinery that grades us.

## Final state

The two blocks below are the generated view at close, verbatim.

### Queue view: Post-Run Quality Analysis

#### START HERE

**Resume anchor**: === | 2026-10-05 (b) -- INBOX DRAINED, 1 of 1, and the epic is RESTART-READY. QUEUE: 1 staged (PRQ-14), 9 parked, 5 merged. Inbox 0 queued / 51 archived. The one message was the stream-end marker from the landed cross-repo-telemetry-archive-and-analyze plan: dispositioned stream_end_noted and archived per the contract's lifecycle rule, with its kind branch deliberately NOT run (it carries kind=finding by design, and routing it as an observation would manufacture a Watch out of 'this sender is done'). restart-check now returns verdict READY -- all five scored signals green: phase orchestrating, no running plan, corpus 15/15 both ways, inbox 0 queued, worktree clean. ⛔ TWO FINDINGS FROM THE DRAIN, both this epic's own subject matter, both recorded as Open Defects and NEITHER owned here (plan-orchestrator inbox mechanics): (1) CONSUMING A STREAM-END MARKER DESTROYS THE CLOSURE IT DECLARES. Before the drain the queue read FINISHED (live_count 0 with the sender in closed_senders -- it will send no more); archiving the marker, which is exactly what the contract prescribes, moved it to EMPTY, which asserts the opposite -- a later message is still possible. A closure is either queued-and-undrained or archived-and-no-longer-declaring; there is NO state where it is both recorded and consumed, so the three-zero vocabulary's middle value is UNREACHABLE after any complete drain. Harmless for this sender (a landed archived plan that can never write) but inbox write would no longer refuse it with stream_closed. (2) ⚠ THE RESTART-CHECK DEFECT IS NOT FIXED BY THE GREEN VERDICT. restart-check still reads the inbox's count rather than live_count; the drain cleared the INSTANCE, not the defect. Any filed-and-undrained stream-end marker will hold its epic at not_ready again -- and a FINISHED queue is BY DEFINITION one that still holds its marker. Do not read ready as resolution. | ON RESUME: (a) PRQ-14 is the only live candidate -- an ordinary in-repo /plan-marshall plan carrying PRQ-13's D4a hand-back, now with BOTH its hypotheses settled by the 2026-10-05 cleanup (simplify is the non-filing case whose findings are already produced and counted before being dropped; security-audit is filed-but-untagged under a CLOSED type taxonomy, so D2 adds a provenance field and never a type). Run next when a slot is wanted. (b) Settled-narrative relocation is still DEFERRED pending operator confirmation and is the natural first act of the next cleanup pass -- epic.md is past 950 lines. (c) The PM-MCP carry-over re-grounding Watch remains the last blocker to close. (d) Landing: use 'orchestrator land' (status / snapshot / bind / resync), not a hand-rolled merge-and-PR; the shared branch was landed by a sibling as #1695 and the remote branch is gone, so a fresh land cycle starts from main. ===

=== | 2026-10-05 -- WS-05 CLOSED OUT and the ledger LANDED. All three telemetry Watches retired: the reports have run in anger on two projects (70 plans and 16 orchestrator records transferred, first fully-adjudicated reports committed, reports/ holds plan-marshall AND cui-http), the .adoc has been read (operator-confirmed, not verified -- no renderer is recorded in that repo), and the tokens zero-floor is fixed. ⛔⛔ THE VINDICATION, not the closure, is the headline: the first real run found FALSE MEASURED ZEROS -- a recorder placeholder total_tokens: 0 treated as a figure on 11 plans, and main_context_tokens measured-0 on 45 -- the precise defect class this epic exists to eliminate, shipped INSIDE the instrument built to detect it, invisible to 924 green tests, surfaced ONLY by real data. A fixture corpus cannot contain the shapes a real corpus has. Cleanup pass ran A-D: corpus 15/15, compaction invariants ok, relocation DEFERRED pending operator confirmation. PRQ-14's two hypotheses settled and both deliverables sharpened. The ledger branch was 23 BEHIND main with main having changed post-run-quality via #1693 -- the #1641 shape -- so main was merged in and nine conflicts resolved by establishing which side was NEWER, every main-only line checked individually; a sibling then landed it as #1695. ===

=== | 2026-10-04 (i) -- PLAN-PRQ-15 SHIPPED (telemetry 0965060..0adc341, 8 commits, no PR). All seven deliverables. D6 verified in the tree: skills are exactly analysis-engine, analyze, transfer; test dirs mirror them and test/analyze/ is NEW, carrying the control that fails if a slash-command usage example returns; 126 rename-detected paths, so git mv moved both trees in one commit. ⛔ THE FINDING THAT MATTERED: plan_rollup reported complete: true over FLOOR summands -- a PRQ-13 defect found by reusing PRQ-13's own pattern, and the floor-propagation form of this epic's founding class: NOT a false zero but a FALSE CERTAINTY. ⭐ aborted proved REACHABLE BUT NEVER OCCURRED (0 of 70 plans carry an abandonment record), and the rule held: zero deliverables done is never aborted. ===

=== | 2026-10-04 (f) -- PLAN-PRQ-13 SHIPPED (telemetry 5546bde) and PLAN-PRQ-14 STAGED from its D4a hand-back. The out-of-lifecycle lane WORKED. ⭐ D0 corrected my partition in three places, two against me. SELF-REVIEW found SEVEN defects, six of this epic's founding class in the instrument built to detect it. ⛔ The seventh was PRE-EXISTING: all 820 assessments.jsonl records counted as findings, making 255 of PLAN-PRQ-07's 255 actionable-pending items assessments -- every quality-chain reading before 5546bde overstated actionable chain debt. Standing caveat: re-derive, never cite. ===

=== | 2026-10-04 -- PLAN-PRQ-07 LANDED (PR #1694 after split #1692) AND ITS INBOX DRAINED (9 of 9). First landing ever to arrive through the inbox, first to pass landing-check complete, and the orchestration-detection control predicted it and held. PLAN-PRQ-13 was then re-cut out of the /plan-marshall lane entirely, on the first-party evidence that PRQ-07's resolver could not see the sibling repo -- 111 declared paths invisible, recall 27.3% graded an error. ===

=== | 2026-09-26 -- QUEUE PARKED: SUPERSEDED BY PM-MCP. Every then-staged row moved to parked with a SUPERSEDED banner; content filed as plan-marshall-mcp/doc/known-defects/post-run-quality-carry-over.md (148 rows). The 2026-10-02 restore recovered this state after PR #1641 reverted it. ===
**Phase**: orchestrating
**Parked**:
- PLAN-PRQ-03 (WS-02)
- PLAN-PRQ-04 (WS-04)
- PLAN-PRQ-01 (WS-01)
- PLAN-PRQ-05 (WS-03)
- PLAN-PRQ-08 (WS-01)
- PLAN-PRQ-09 (WS-01)
- PLAN-PRQ-10 (WS-01)
- PLAN-PRQ-11 (WS-01)
- PLAN-PRQ-12 (WS-01)
**Queue** (staged, in order):
1. PLAN-PRQ-14 (WS-01)
- PLAN-PRQ-02 (WS-01) — plan=retrospective-aspects-publish-verdict — PR 1550 — landing=landings/PLAN-PRQ-02.md — status: shipped
- PLAN-PRQ-06 (WS-04) — plan=prq-06-a-lane-override-that-cannot-take-effect-is — PR 1541 — landing=landings/PLAN-PRQ-06.md — status: shipped
- PLAN-PRQ-07 (WS-05) — plan=cross-repo-telemetry-archive-and-analyze — PR 1694 — landing=landings/PLAN-PRQ-07.md — status: shipped
- PLAN-PRQ-13 (WS-05) — PR 5546bde — landing=landings/PLAN-PRQ-13.md — status: shipped
- PLAN-PRQ-15 (WS-05) — PR 0adc341 — landing=landings/PLAN-PRQ-15.md — status: shipped

#### Ordered Queue

| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-PRQ-03 | WS-02 | parked | .claude/skills/audit-archived-plan-retrospectives/SKILL.md; .claude/skills/audit-archived-plan-retrospectives/checks/; .claude/skills/audit-archived-plan-retrospectives/scripts/audit.py; .claude/skills/recipe-plan-review/SKILL.md; test/plan-marshall/audit-archived-plan-retrospectives/ |
| 2 | PLAN-PRQ-04 | WS-04 | parked | marketplace/bundles/plan-marshall/skills/manage-status/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/**; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md; test/plan-marshall/phase-6-finalize/** |
| 3 | PLAN-PRQ-01 | WS-01 | parked | .claude/skills/audit-archived-plan-retrospectives/SKILL.md; .claude/skills/audit-archived-plan-retrospectives/checks/; .claude/skills/audit-archived-plan-retrospectives/scripts/audit.py; doc/analyzis-cloud-plan/; marketplace/bundles/plan-marshall/skills/manage-findings/**; marketplace/bundles/plan-marshall/skills/manage-references/**; marketplace/bundles/plan-marshall/skills/phase-3-outline/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py; marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/**; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/retro_sections.py; marketplace/bundles/plan-marshall/skills/script-shared/scripts/; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py; marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; test/plan-marshall/audit-archived-plan-retrospectives/; test/plan-marshall/manage-findings/**; test/plan-marshall/plan-retrospective/; test/plan-marshall/plan-retrospective/** |
| 4 | PLAN-PRQ-05 | WS-03 | parked | .claude/skills/finalize-step-lessons-housekeeping/; marketplace/bundles/plan-marshall/skills/manage-lessons/; test/plan-marshall/manage-lessons/ |
| 5 | PLAN-PRQ-08 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py; marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/; marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md; marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/references/; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/retro_sections.py; test/plan-marshall/manage-metrics/; test/plan-marshall/plan-retrospective/ |
| 6 | PLAN-PRQ-09 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/manage-references/scripts/; marketplace/bundles/plan-marshall/skills/manage-tasks/**; marketplace/bundles/plan-marshall/skills/plan-retrospective/references/; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/retro_sections.py; test/plan-marshall/plan-retrospective/ |
| 7 | PLAN-PRQ-10 | WS-01 | parked | doc/user/configuration.adoc; marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md; marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md; marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/verdict-currency.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_patterns.py; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/self_review.py; test/plan-marshall/phase-6-finalize/; test/pm-plugin-development/ext-self-review-plan-marshall/ |
| 8 | PLAN-PRQ-11 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/plan-retrospective/references/; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/; test/plan-marshall/plan-retrospective/ |
| 9 | PLAN-PRQ-12 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/plan-retrospective/references/chat-history-analysis.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/extract-chat-signal.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_chat_signal_reducer.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_claude_runtime_impl.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/antigravity_runtime.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py; marketplace/bundles/plan-marshall/skills/ref-toon-format/scripts/toon_parser.py; test/plan-marshall/plan-retrospective/test_extract_chat_signal.py; test/plan-marshall/platform-runtime/ |
| 10 | PLAN-PRQ-14 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-findings/; marketplace/bundles/plan-marshall/skills/manage-tasks/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/; marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py; marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py; test/plan-marshall/manage-findings/; test/plan-marshall/phase-6-finalize/ |

## Queue outcome

15 plans: 5 shipped, 0 closed unshipped, 9 parked, 1 at another status.

### Shipped

| Plan | Slug | Status | PR |
|---|---|---|---|
| PLAN-PRQ-02 | retrospective-aspects-publish-a-verdict-over-a-population-they-never-read | shipped | 1550 |
| PLAN-PRQ-06 | a-lane-override-that-cannot-take-effect-is-accepted-and-reported-set | shipped | 1541 |
| PLAN-PRQ-07 | cross-repo-telemetry-archive-and-analyze | shipped | 1694 |
| PLAN-PRQ-13 | telemetry-analyze-outcome-and-quality-reports | shipped | 5546bde |
| PLAN-PRQ-15 | project-level-adoc-aggregate-and-outcome-identity-fields | shipped | 0adc341 |

### Closed unshipped

_none_

### Parked at close

| Plan | Slug | Status |
|---|---|---|
| PLAN-PRQ-03 | the-census-does-not-census-itself-and-a-re-check-persists-nothing | parked |
| PLAN-PRQ-04 | an-obligation-that-outlives-its-plan-has-no-owner | parked |
| PLAN-PRQ-01 | retrospective-quality-chain-and-assessments-graded-at-report-time | parked |
| PLAN-PRQ-05 | lessons-corpus-provenance-and-quality | parked |
| PLAN-PRQ-08 | two-dispatch-ledgers-disagree-and-terminal-spend-is-classified-as-waste | parked |
| PLAN-PRQ-09 | retrospective-instruments-that-cannot-fire-and-recall-denominators-that-count-the-wrong-population | parked |
| PLAN-PRQ-10 | finalize-refire-convergence-and-self-review-coverage-honesty | parked |
| PLAN-PRQ-11 | spend-and-diagnostic-aspects-count-the-wrong-population-too | parked |
| PLAN-PRQ-12 | the-reducer-never-marks-its-own-output-for-block-scalar-emission | parked |

### Other status at close

| Plan | Slug | Status |
|---|---|---|
| PLAN-PRQ-14 | findings-producers-tag-their-mechanism-and-keep-upstream-severity | staged |

A row still `staged` or `parked` here was live work that did not finish before the close. It
is a lead, not a queue entry: nothing emits it any more.

## Carried into `live-blockers`

- Scope-creep guard reports (forwarded here from API-Sheriff and the telemetry plan) → `PLAN-LB-07`.
- CodeRabbit rate-window wait inside a sub-agent → `PLAN-LB-18`.
- Self-review non-convergence and `verdict_inputs` (`PLAN-PRQ-10` D1) → `PLAN-LB-02`.

## Leads carried forward, not staged

- The medium- and low-priority items found in this epic are listed with evidence in
  `.plan/orchestrator/live-blockers/backlog.md`. They are unstaged.
- `epic.md` § Open Defects (23 entries) and § Watches (18 entries) are frozen as they
  stood. Entries not named above or in that backlog were judged to be design input for the
  rewrite, refactors or measurements of machinery the rewrite replaces, or already fixed.
- Design input for plan-marshall-mcp lives in that repository's requirements, specification
  and `doc/implementation-watch/` documents. Ledger pointers to
  `plan-marshall-mcp/doc/known-defects/…-carry-over.md` name a path that no longer exists.
- `PLAN-PRQ-12` is `parked` but its main deliverable shipped via #1646.
- `PLAN-PRQ-14`, the one staged row, rests on an overstated premise: Sonar severity is written into every finding's detail text (`sonar.py:594`), so it is recoverable.
- `PLAN-PRQ-03` and parts of `PLAN-PRQ-01` point at code that moved to the `plan-marshall-telemetry` repository.
- Review-bot size caps discovered only after PR creation, the lesson duplicate check that cannot see worktree plans, and finalize step ordering are in `backlog.md` §§ 4.4, 2.6 and 1.24.

### Inbox messages undrained at close

- none

## Landed in parallel with the close

One ledger landing from this epic's own session reached `main` while the close was being
prepared (#1706). It was integrated into this tree before it was archived; the "Final state"
block above predates it.

- **Issue #1697 resolved and closed**: both inbox defects (a "sender finished" marker counted
  as unread mail; closure lost after the drain) were fixed by PR #1700 and verified on this
  epic's own queue.
- **Settled-narrative relocation applied** (operator-confirmed): ten items moved verbatim from
  `epic.md` to `settled.md` under "Resolved defects" and "Retired watches". The Open Defects
  and Watches counts quoted above were taken before that move.

## Decision record

`epic.md` § Decisions is the curated view; `logs/decision.log` is the append-only record. Both
are frozen in this tree.
